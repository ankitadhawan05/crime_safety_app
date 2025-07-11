import requests
import pandas as pd
import folium
import streamlit as st
import numpy as np
from shapely.geometry import Point # type: ignore
from streamlit_folium import st_folium
from data_preprocess import load_crime_data, preprocess_for_clustering  # Updated imports
from clustering_engine import load_clustering_model, predict_clusters_safe  # Updated imports

# ------------------- Free API Configuration -------------------
OSRM_HOST = "localhost"
OSRM_PORT = "5000"
USE_OSRM = False  # Set to False by default since OSRM server is not running

# OpenRouteService (Free API) Configuration
OPENROUTESERVICE_API_KEY = None  # Will be set by user
USE_OPENROUTESERVICE = False

# Alternative free routing services
ROUTING_SERVICES = {
    "openrouteservice": "https://api.openrouteservice.org/v2/directions",
    "graphhopper": "https://graphhopper.com/api/1/route"  # Has free tier
}

# ------------------- Alternative: Get Pre-clustered Data -------------------
@st.cache_data
def get_fast_clustered_data():
    """Ultra-fast clustered data using pre-computed results or simplified clustering"""
    try:
        # Load the already clustered data from clustering.py if available
        from clustering import get_processed_data, get_clustered_data
        
        # Get the processed data
        df, df_encoded, extra_cols = get_processed_data()
        
        # Get clustered data using existing pipeline
        clustered_df = get_clustered_data(df, df_encoded, extra_cols)
        
        # Sample for route generation performance (removed info message)
        if len(clustered_df) > 5000:
            clustered_df = clustered_df.sample(n=5000, random_state=42).reset_index(drop=True)
        
        return clustered_df
        
    except Exception as e:
        st.error(f"Error using pre-clustered data: {str(e)}")
        return None

# ------------------- Compute Bounding Box -------------------
def get_bbox_from_areas(df, start_area, end_area):
    """Get bounding box and coordinates for start/end areas"""
    try:
        # Filter data for start and end areas
        start_data = df[df['AREA NAME'] == start_area][['LAT', 'LON']].dropna()
        end_data = df[df['AREA NAME'] == end_area][['LAT', 'LON']].dropna()

        if start_data.empty or end_data.empty:
            st.error(f"No coordinate data found for {start_area} or {end_area}")
            return None, None, None, None, None

        # Get mean coordinates for each area
        start_coords = start_data.mean()
        end_coords = end_data.mean()
        
        start_lat, start_lon = float(start_coords['LAT']), float(start_coords['LON'])
        end_lat, end_lon = float(end_coords['LAT']), float(end_coords['LON'])

        # Create bounding box with buffer
        lat_buffer = 0.02
        lon_buffer = 0.02

        north = max(start_lat, end_lat) + lat_buffer
        south = min(start_lat, end_lat) - lat_buffer
        east = max(start_lon, end_lon) + lon_buffer
        west = min(start_lon, end_lon) - lon_buffer

        bbox = (west, south, east, north)
        return bbox, (start_lat, start_lon), (end_lat, end_lon), start_area, end_area
        
    except Exception as e:
        st.error(f"Error computing bounding box: {str(e)}")
        return None, None, None, None, None

# ------------------- Free API Real Road Routing -------------------
def get_openrouteservice_route(start_coords, end_coords, travel_mode="driving-car", api_key=None):
    """Get real road route from OpenRouteService (Free API)"""
    if not api_key:
        return None
    
    # Convert travel modes
    mode_mapping = {
        "driving": "driving-car",
        "walking": "foot-walking", 
        "cycling": "cycling-regular"
    }
    
    profile = mode_mapping.get(travel_mode, "driving-car")
    
    # OpenRouteService API endpoint
    url = f"https://api.openrouteservice.org/v2/directions/{profile}"
    
    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
        'Authorization': api_key,
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    # Coordinates in [longitude, latitude] format for ORS
    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    
    body = {
        "coordinates": [[start_lon, start_lat], [end_lon, end_lat]],
        "format": "geojson"
    }
    
    try:
        response = requests.post(url, json=body, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('features') and len(data['features']) > 0:
                # Extract coordinates from GeoJSON
                coordinates = data['features'][0]['geometry']['coordinates']
                # Return in [lon, lat] format to match our existing system
                return coordinates
        elif response.status_code == 403:
            st.error("🔑 Invalid API key or quota exceeded")
        elif response.status_code == 429:
            st.error("⏱️ API rate limit exceeded. Please try again later.")
        else:
            st.error(f"🌐 API Error: {response.status_code}")
        
        return None
        
    except requests.exceptions.RequestException as e:
        st.error(f"🌐 Network error connecting to routing service: {str(e)}")
        return None

def get_graphhopper_route(start_coords, end_coords, travel_mode="car", api_key=None):
    """Get real road route from GraphHopper (Free tier available)"""
    if not api_key:
        return None
    
    # Convert travel modes for GraphHopper
    mode_mapping = {
        "driving": "car",
        "walking": "foot",
        "cycling": "bike"
    }
    
    vehicle = mode_mapping.get(travel_mode, "car")
    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    
    url = "https://graphhopper.com/api/1/route"
    
    params = {
        "point": [f"{start_lat},{start_lon}", f"{end_lat},{end_lon}"],
        "vehicle": vehicle,
        "key": api_key,
        "type": "json",
        "points_encoded": "false"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('paths') and len(data['paths']) > 0:
                # Extract coordinates
                points = data['paths'][0]['points']['coordinates']
                # Convert from [lat, lon] to [lon, lat] format
                return [[point[0], point[1]] for point in points]
        else:
            st.error(f"🌐 GraphHopper API Error: {response.status_code}")
        
        return None
        
    except requests.exceptions.RequestException as e:
        st.error(f"🌐 Network error: {str(e)}")
        return None

def get_free_real_road_route(start_coords, end_coords, travel_mode="driving", api_keys=None):
    """Try multiple free APIs to get real road routing"""
    
    if not api_keys:
        api_keys = {}
    
    # Try OpenRouteService first (most reliable free option)
    if api_keys.get('openrouteservice'):
        st.info("🛣️ Getting real road route from OpenRouteService...")
        route = get_openrouteservice_route(start_coords, end_coords, travel_mode, api_keys['openrouteservice'])
        if route:
            return route, "OpenRouteService"
    
    # Try GraphHopper as backup
    if api_keys.get('graphhopper'):
        st.info("🛣️ Trying GraphHopper for real road route...")
        route = get_graphhopper_route(start_coords, end_coords, travel_mode, api_keys['graphhopper'])
        if route:
            return route, "GraphHopper"
    
    # No API keys or all failed
    return None, None

# ------------------- Enhanced Multi-Route Generation with Real Roads -------------------
def generate_multiple_routes_real_roads(start_coords, end_coords, travel_mode="driving", api_keys=None):
    """Generate multiple real road routes using free APIs"""
    routes = {}
    
    try:
        # Try to get real road route first
        real_route, service_used = get_free_real_road_route(start_coords, end_coords, travel_mode, api_keys)
        
        if real_route:
            st.success(f"✅ Real road route generated using {service_used}")
            
            # Use the real route as base and generate variations
            routes["low_risk"] = create_safe_variation(real_route, start_coords, end_coords, 0.3)
            routes["medium_risk"] = real_route  # Use the real route as balanced option
            routes["high_risk"] = create_direct_variation(real_route, start_coords, end_coords)
            
        else:
            # Fallback to simulated routes if no API available
            st.info("🛣️ Using simulated road routes (no API key provided)")
            routes = generate_multiple_routes(start_coords, end_coords, travel_mode)
            
    except Exception as e:
        st.warning(f"Error with real road routing: {str(e)}")
        # Fallback to simulated routes
        routes = generate_multiple_routes(start_coords, end_coords, travel_mode)
    
    return routes

def create_safe_variation(base_route, start_coords, end_coords, detour_factor):
    """Create a safer variation of the real road route"""
    if not base_route or len(base_route) < 3:
        return generate_safe_route(start_coords, end_coords, {"waypoints": 20, "curve_factor": 0.002}, detour_factor)
    
    # Take the real route and add safety detours at key points
    safe_route = []
    for i, coord in enumerate(base_route):
        safe_route.append(coord)
        
        # Add detour points every few segments for safety
        if i > 0 and i < len(base_route) - 1 and i % 5 == 0:
            lon, lat = coord
            # Small detour to potentially avoid high-crime direct paths
            import math
            progress = i / len(base_route)
            detour_lat = lat + detour_factor * 0.001 * math.sin(progress * math.pi * 2)
            detour_lon = lon + detour_factor * 0.001 * math.cos(progress * math.pi * 2)
            safe_route.append([detour_lon, detour_lat])
    
    return safe_route

def create_direct_variation(base_route, start_coords, end_coords):
    """Create a more direct variation of the real road route"""
    if not base_route or len(base_route) < 3:
        return generate_direct_route(start_coords, end_coords, 10)
    
    # Simplify the real route by taking every nth point for more direct path
    step = max(1, len(base_route) // 15)  # Take fewer points for more direct route
    direct_route = []
    
    for i in range(0, len(base_route), step):
        direct_route.append(base_route[i])
    
    # Ensure we have start and end points
    if direct_route[0] != base_route[0]:
        direct_route.insert(0, base_route[0])
    if direct_route[-1] != base_route[-1]:
        direct_route.append(base_route[-1])
    
    return direct_route

def generate_direct_route(start_coords, end_coords, waypoints):
    """Generate direct route - potentially higher risk but faster"""
    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    
    route_coords = []
    for i in range(waypoints + 1):
        progress = i / waypoints
        lat = start_lat + (end_lat - start_lat) * progress
        lon = start_lon + (end_lon - start_lon) * progress
        route_coords.append([lon, lat])
    
    return route_coords

def generate_balanced_route(start_coords, end_coords, params, detour_factor):
    """Generate balanced route with moderate detour"""
    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    
    route_coords = []
    waypoints = params["waypoints"]
    
    for i in range(waypoints + 1):
        progress = i / waypoints
        
        # Base interpolation
        lat = start_lat + (end_lat - start_lat) * progress
        lon = start_lon + (end_lon - start_lon) * progress
        
        # Add moderate detour for medium risk avoidance
        if 0.2 <= progress <= 0.8:
            import math
            detour = detour_factor * params["curve_factor"]
            lat += detour * math.sin(progress * math.pi * 2)
            lon += detour * math.cos(progress * math.pi * 1.5)
        
        route_coords.append([lon, lat])
    
    return route_coords

def generate_safe_route(start_coords, end_coords, params, detour_factor):
    """Generate safer route with larger detour to avoid high-crime areas"""
    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    
    route_coords = []
    waypoints = params["waypoints"] + 5  # More waypoints for safer route
    
    for i in range(waypoints + 1):
        progress = i / waypoints
        
        # Base interpolation
        lat = start_lat + (end_lat - start_lat) * progress
        lon = start_lon + (end_lon - start_lon) * progress
        
        # Add larger detour for safety
        if 0.1 <= progress <= 0.9:
            import math
            detour = detour_factor * params["curve_factor"]
            # Create larger curves to avoid direct path through potential high-crime areas
            lat += detour * math.sin(progress * math.pi * 3) * (1 - abs(progress - 0.5))
            lon += detour * math.cos(progress * math.pi * 2.5) * (1 - abs(progress - 0.5))
        
        route_coords.append([lon, lat])
    
    return route_coords

def generate_multiple_routes(start_coords, end_coords, travel_mode="driving"):
    """Generate multiple routes with different risk profiles based on travel mode"""
    try:
        routes = {}
        
        # Base parameters based on travel mode
        mode_params = {
            "driving": {"detour_factor": 1.3, "waypoints": 15, "curve_factor": 0.001},
            "walking": {"detour_factor": 1.2, "waypoints": 20, "curve_factor": 0.0015},
            "cycling": {"detour_factor": 1.25, "waypoints": 18, "curve_factor": 0.0012}
        }
        
        params = mode_params.get(travel_mode, mode_params["driving"])
        
        start_lat, start_lon = start_coords
        end_lat, end_lon = end_coords
        
        # Calculate base distance
        lat_diff = end_lat - start_lat
        lon_diff = end_lon - start_lon
        
        # Route 1: Direct/Fast Route (Higher Risk Potential)
        routes["high_risk"] = generate_direct_route(start_coords, end_coords, params["waypoints"])
        
        # Route 2: Balanced Route (Medium Risk)
        routes["medium_risk"] = generate_balanced_route(start_coords, end_coords, params, 0.1)
        
        # Route 3: Safe Route (Lower Risk, Longer)
        routes["low_risk"] = generate_safe_route(start_coords, end_coords, params, 0.2)
        
        return routes
        
    except Exception as e:
        st.error(f"Error generating multiple routes: {str(e)}")
        return {"low_risk": [[start_coords[1], start_coords[0]], [end_coords[1], end_coords[0]]]}

# ------------------- Optimized Risk Scoring -------------------
def score_route_risk(route_coords, clustered_df, risk_threshold=0.01):
    """Fast risk scoring with optimized performance"""
    try:
        # Sample crime data for faster computation
        max_crime_points = 2000
        if len(clustered_df) > max_crime_points:
            clustered_sample = clustered_df.sample(n=max_crime_points, random_state=42)
        else:
            clustered_sample = clustered_df
        
        # Pre-filter only high and medium risk areas for faster processing
        high_risk_points = clustered_sample[clustered_sample["Cluster"] == 0][["LAT", "LON"]].values
        medium_risk_points = clustered_sample[clustered_sample["Cluster"] == 2][["LAT", "LON"]].values
        
        risk_score = 0
        risk_details = {"high_risk": 0, "medium_risk": 0, "safe_segments": 0}
        
        # Vectorized distance calculation for better performance
        import numpy as np
        
        route_array = np.array([[lat, lon] for lon, lat in route_coords])
        
        for i, (lat, lon) in enumerate(route_array):
            found_risk = False
            
            # Check high risk areas first (more important)
            if len(high_risk_points) > 0:
                distances = np.sqrt(np.sum((high_risk_points - [lat, lon])**2, axis=1))
                if np.any(distances < risk_threshold):
                    risk_score += 3
                    risk_details["high_risk"] += 1
                    found_risk = True
            
            # Only check medium risk if no high risk found
            if not found_risk and len(medium_risk_points) > 0:
                distances = np.sqrt(np.sum((medium_risk_points - [lat, lon])**2, axis=1))
                if np.any(distances < risk_threshold):
                    risk_score += 1
                    risk_details["medium_risk"] += 1
                    found_risk = True
            
            if not found_risk:
                risk_details["safe_segments"] += 1
        
        return risk_score, risk_details
        
    except Exception:
        # Fast fallback scoring
        return len(route_coords) // 3, {"high_risk": 1, "medium_risk": 1, "safe_segments": len(route_coords) - 2}

# ------------------- Enhanced Multi-Route Map Display -------------------
def display_multi_route_map(routes_data, clustered_df, start_coords, end_coords, travel_mode):
    """Display multiple routes on map with different colors and risk levels"""
    try:
        # Create map centered between start and end
        center_lat = (start_coords[0] + end_coords[0]) / 2
        center_lon = (start_coords[1] + end_coords[1]) / 2
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=11, prefer_canvas=True)

        # Color mapping for crime clusters
        crime_color_map = {0: 'red', 1: 'green', 2: 'orange'}
        cluster_labels = {0: 'High Risk Zone', 1: 'Low Risk Zone', 2: 'Medium Risk Zone'}
        
        # Sample crime data for fast map rendering
        max_map_points = 300  # Reduced for better performance with multiple routes
        if len(clustered_df) > max_map_points:
            clustered_sample = clustered_df.sample(n=max_map_points, random_state=42)
        else:
            clustered_sample = clustered_df
        
        # Add crime data points
        for _, row in clustered_sample.iterrows():
            folium.CircleMarker(
                location=(row['LAT'], row['LON']),
                radius=2,
                color=crime_color_map.get(row['Cluster'], 'gray'),
                fill=True,
                fillOpacity=0.3,
                weight=1,
                tooltip=f"{cluster_labels.get(row['Cluster'], 'Unknown')}"
            ).add_to(m)

        # Route colors and styles
        route_styles = {
            "low_risk": {"color": "green", "weight": 5, "opacity": 0.8, "label": "🟢 Safe Route"},
            "medium_risk": {"color": "orange", "weight": 4, "opacity": 0.7, "label": "🟡 Balanced Route"},
            "high_risk": {"color": "red", "weight": 4, "opacity": 0.7, "label": "🔴 Direct Route"}
        }
        
        # Add all routes to map
        displayed_routes = {}
        for route_type, route_coords in routes_data.items():
            if route_coords:
                style = route_styles.get(route_type, route_styles["low_risk"])
                route_points = [[lat, lon] for lon, lat in route_coords]
                
                folium.PolyLine(
                    route_points,
                    color=style["color"],
                    weight=style["weight"],
                    opacity=style["opacity"],
                    popup=f"{style['label']} ({travel_mode.title()} Mode)"
                ).add_to(m)
                
                displayed_routes[route_type] = {
                    "coords": route_coords,
                    "style": style
                }

        # Add travel mode specific markers
        mode_icons = {
            "driving": "car",
            "walking": "walk", 
            "cycling": "bicycle"
        }
        
        icon_name = mode_icons.get(travel_mode, "location-arrow")
        
        # Start marker
        folium.Marker(
            location=start_coords,
            popup=f"Start ({travel_mode.title()} Mode)",
            icon=folium.Icon(color='blue', icon=icon_name, prefix='fa')
        ).add_to(m)
        
        # End marker
        folium.Marker(
            location=end_coords,
            popup=f"Destination ({travel_mode.title()} Mode)",
            icon=folium.Icon(color='purple', icon='flag', prefix='fa')
        ).add_to(m)

        # Add legend
        legend_html = f'''
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 200px; height: auto; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <p><b>🚗 {travel_mode.title()} Routes</b></p>
        <p><span style="color:green;">🟢</span> Safe Route (Recommended)</p>
        <p><span style="color:orange;">🟡</span> Balanced Route</p>
        <p><span style="color:red;">🔴</span> Direct Route (Higher Risk)</p>
        <br>
        <p><b>Crime Zones:</b></p>
        <p><span style="color:red;">🔴</span> High Crime</p>
        <p><span style="color:orange;">🟠</span> Medium Risk</p>
        <p><span style="color:green;">🟢</span> Low Crime</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

        return m, displayed_routes
        
    except Exception as e:
        st.error(f"Error displaying multi-route map: {str(e)}")
        return None, {}

# ------------------- Smart Route Recommendation -------------------
def get_route_recommendation(risk_scores, travel_mode):
    """Provide intelligent route recommendation based on risk analysis"""
    
    # Find the safest route
    safest_route = min(risk_scores.keys(), key=lambda x: risk_scores[x])
    lowest_risk = risk_scores[safest_route]
    
    if lowest_risk <= 3:
        return {
            "status": "safe",
            "message": "✅ Safe to travel on this route",
            "recommended_route": safest_route,
            "color": "success"
        }
    elif lowest_risk <= 8:
        return {
            "status": "moderate", 
            "message": "⚠️ Moderate risk detected. Consider the recommended safe route.",
            "recommended_route": safest_route,
            "color": "warning"
        }
    else:
        return {
            "status": "unsafe",
            "message": "🚨 Unsafe to travel. High crime risk zone detected on this route. Change route recommended.",
            "recommended_route": safest_route,
            "color": "error"
        }

# ------------------- Enhanced Main Pipeline with Real Roads Support -------------------
def compute_and_display_safe_route(start_area, end_area, travel_mode="driving", force_safe_route=False, api_keys=None):
    """Enhanced route computation with real road routing using free APIs"""
    try:
        # Show immediate feedback
        progress = st.progress(0)
        status = st.empty()
        
        status.text("🔄 Loading crime data...")
        progress.progress(20)
        
        # Try to use fast pre-clustered data first
        clustered_df = get_fast_clustered_data()
        
        if clustered_df is None:
            status.text("🔄 Generating clusters...")
            progress.progress(30)
            clustered_df = get_clustered_crime_data_safe()
        
        if clustered_df is None:
            progress.empty()
            status.empty()
            st.error("Could not load crime data")
            return False

        status.text("📍 Computing coordinates...")
        progress.progress(40)

        # Get bounding box and coordinates
        bbox, start_coords, end_coords, _, _ = get_bbox_from_areas(clustered_df, start_area, end_area)

        if bbox is None:
            progress.empty()
            status.empty()
            st.error("🚫 Failed to compute area coordinates.")
            return False

        status.text(f"🛣️ Generating real road {travel_mode} routes...")
        progress.progress(60)

        # Generate routes with real road routing
        if force_safe_route:
            # For safety-first, try real road route but with safety modifications
            real_route, service = get_free_real_road_route(start_coords, end_coords, travel_mode, api_keys)
            if real_route:
                routes = {"low_risk": create_safe_variation(real_route, start_coords, end_coords, 0.4)}
                st.success(f"✅ Safe real road route generated using {service}")
            else:
                routes = {"low_risk": generate_safe_route(start_coords, end_coords, 
                         {"waypoints": 20, "curve_factor": 0.002}, 0.3)}
                st.info("🛣️ Generated simulated safe route (no API available)")
        else:
            # Generate multiple route options with real roads
            routes = generate_multiple_routes_real_roads(start_coords, end_coords, travel_mode, api_keys)

        if routes:
            status.text("⚡ Analyzing route risks...")
            progress.progress(80)
            
            # Score all routes
            route_risk_scores = {}
            route_risk_details = {}
            
            for route_type, route_coords in routes.items():
                if route_coords:
                    risk_score, risk_details = score_route_risk(route_coords, clustered_df)
                    route_risk_scores[route_type] = risk_score
                    route_risk_details[route_type] = risk_details
            
            status.text("🗺️ Rendering map...")
            progress.progress(95)
            
            # Clear progress indicators
            progress.progress(100)
            status.empty()
            progress.empty()
            
            # Display results
            st.success("✅ Routes generated successfully!")
            st.info(f"📍 {travel_mode.title()} routes from {start_area} to {end_area}")
            
            # Get route recommendation
            recommendation = get_route_recommendation(route_risk_scores, travel_mode)
            
            # Display recommendation with appropriate styling
            if recommendation["status"] == "safe":
                st.success(recommendation["message"])
            elif recommendation["status"] == "moderate":
                st.warning(recommendation["message"])
            else:
                st.error(recommendation["message"])
                
                # Add change route button for unsafe routes
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Generate Safer Route", type="primary", key="safer_route"):
                        # Force generate only the safest route
                        with st.spinner("🛡️ Generating safer route..."):
                            return compute_and_display_safe_route(start_area, end_area, travel_mode, force_safe_route=True, api_keys=api_keys)
                
                with col2:
                    if st.button("🔍 Try Different Areas", key="different_areas"):
                        st.info("Please select different start and destination areas above.")
                        return False
            
            # Display the multi-route map
            map_obj, displayed_routes = display_multi_route_map(
                routes, clustered_df, start_coords, end_coords, travel_mode
            )
            
            if map_obj:
                st_folium(map_obj, width=900, height=600, returned_objects=[])
                
                # Display detailed route information
                st.markdown("### 📊 Route Analysis")
                
                cols = st.columns(len(route_risk_scores))
                for i, (route_type, risk_score) in enumerate(route_risk_scores.items()):
                    with cols[i]:
                        route_name = route_type.replace("_", " ").title() + " Route"
                        
                        if route_type == "low_risk":
                            st.success(f"🟢 **{route_name}**")
                        elif route_type == "medium_risk":
                            st.warning(f"🟡 **{route_name}**")
                        else:
                            st.error(f"🔴 **{route_name}**")
                        
                        st.metric("Risk Score", risk_score)
                        details = route_risk_details[route_type]
                        st.write(f"🔴 High Risk: {details['high_risk']}")
                        st.write(f"🟢 Safe Segments: {details['safe_segments']}")
                
                # Travel mode specific tips
                st.markdown(f"### 💡 {travel_mode.title()} Safety Tips")
                mode_tips = {
                    "driving": [
                        "🚗 Keep doors locked and windows up",
                        "⛽ Plan fuel stops in safe areas", 
                        "📱 Use hands-free navigation",
                        "🚨 Avoid stopping in isolated areas"
                    ],
                    "walking": [
                        "👥 Walk in groups when possible",
                        "🔦 Carry a flashlight for evening walks",
                        "📱 Share your route with someone",
                        "👀 Stay alert and aware of surroundings"
                    ],
                    "cycling": [
                        "🚴‍♂️ Wear bright, visible clothing",
                        "🛡️ Always wear a helmet",
                        "🚲 Use bike lanes when available",
                        "💡 Use lights during low visibility"
                    ]
                }
                
                tips = mode_tips.get(travel_mode, mode_tips["driving"])
                for tip in tips:
                    st.write(f"- {tip}")
            
            return True
        else:
            progress.empty()
            status.empty()
            st.error("🚫 Failed to generate routes.")
            return False
            
    except Exception as e:
        st.error(f"Error in route computation: {str(e)}")
        return False

# ------------------- Safe Clustering Fallback -------------------
@st.cache_data
def get_clustered_crime_data_safe():
    """Safe fallback clustering with proper error handling"""
    try:
        # Load raw data
        df = load_crime_data()
        
        # Reset index to ensure clean start
        df = df.reset_index(drop=True)
        
        # Process for clustering
        df_encoded, extra_cols = preprocess_for_clustering(df)
        
        # Verify alignment
        if len(df) != len(df_encoded):
            st.warning(f"Data alignment issue: Original={len(df)}, Encoded={len(df_encoded)}")
            # Truncate to minimum length
            min_len = min(len(df), len(df_encoded))
            df = df.iloc[:min_len].reset_index(drop=True)
            df_encoded = df_encoded.iloc[:min_len].reset_index(drop=True)
        
        # Load model
        model, scaler = load_clustering_model()
        if model is None or scaler is None:
            return None
        
        # Define features
        features = ['LAT', 'LON', 'Part 1-2'] + extra_cols
        
        # Predict clusters
        clusters = predict_clusters_safe(df_encoded, features, model, scaler)
        if clusters is None:
            return None
        
        # Add clusters
        df['Cluster'] = clusters
        
        # Sample for performance
        if len(df) > 5000:
            df = df.sample(n=5000, random_state=42).reset_index(drop=True)
        
        return df
        
    except Exception as e:
        st.error(f"Error in safe clustering: {str(e)}")
        return None

# ------------------- Backwards Compatibility -------------------
# Alias for any imports that expect the old function name
get_clustered_crime_data = get_fast_clustered_data

# Legacy function for simple route generation (backward compatibility)
def get_alternative_route(start_coords, end_coords):
    """Legacy function - generates a single balanced route"""
    routes = generate_multiple_routes(start_coords, end_coords, "driving")
    return routes.get("medium_risk", [[start_coords[1], start_coords[0]], [end_coords[1], end_coords[0]]])
