# simple_free_api_utils.py - Restored version with original Google Maps-style routing + enhanced safety analysis
import requests
import pandas as pd
import folium
import streamlit as st
import numpy as np
from streamlit_folium import st_folium 
from data_preprocess import load_crime_data, add_time_of_day  # Import from your data_preprocess file

# ================= FREE OSRM CONFIGURATION =================
OSRM_HOST = "router.project-osrm.org"  # Free public OSRM server

# ================= ENHANCED CRIME DATA LOADING WITH TIME FILTERING =================
def get_route_specific_peak_crime_time(route_coords, crime_df, proximity_threshold=0.005):
    """Get peak crime time specifically for crimes near this route (optimized)"""
    if not route_coords or crime_df is None or crime_df.empty or 'Time of Day' not in crime_df.columns:
        return None
    
    try:
        # Sample route coordinates for performance (every 5th point)
        sampled_coords = route_coords[::5] if len(route_coords) > 10 else route_coords
        
        nearby_crime_times = []
        
        # Use vectorized operations for better performance
        crime_coords = crime_df[['LAT', 'LON']].values
        crime_times = crime_df['Time of Day'].values
        
        for lon, lat in sampled_coords:
            # Calculate distances to all crimes at once
            distances = np.sqrt(np.sum((crime_coords - [lat, lon])**2, axis=1))
            
            # Find nearby crimes
            nearby_indices = np.where(distances < proximity_threshold)[0]
            
            # Add times of nearby crimes
            for idx in nearby_indices:
                time_val = crime_times[idx]
                if time_val and time_val != 'Unknown':
                    nearby_crime_times.append(time_val)
        
        if nearby_crime_times:
            # Find the most common time for crimes specifically near this route
            from collections import Counter
            time_counts = Counter(nearby_crime_times)
            most_common_time = time_counts.most_common(1)[0][0]
            return most_common_time
        
        return None
    
    except Exception:
        return None

@st.cache_data
def load_crime_data_with_time_filter(time_of_travel="Any Time"):
    """Load and prepare crime data with time-based filtering"""
    try:
        # Use your existing load_crime_data function
        df = load_crime_data()
        
        # Ensure Time of Day exists using your existing function
        if 'Time of Day' not in df.columns:
            df = add_time_of_day(df)
        
        # Filter by time of travel if specified
        if time_of_travel != "Any Time":
            time_mapping = {
                "Morning (6-12)": "Morning",
                "Afternoon (12-16)": "Afternoon", 
                "Evening (16-18)": "Evening",
                "Night (18-6)": "Night"
            }
            
            target_time = time_mapping.get(time_of_travel)
            if target_time:
                df = df[df['Time of Day'] == target_time].copy()
        
        # Enhanced crime severity clustering
        if 'Cluster' not in df.columns:
            # Enhanced clustering based on crime type severity and frequency
            serious_crimes = [
                'ROBBERY', 'ASSAULT', 'BURGLARY', 'RAPE', 'HOMICIDE', 
                'KIDNAPPING', 'ARSON', 'SHOTS FIRED', 'CRIMINAL THREATS'
            ]
            
            def classify_crime_severity(row):
                crime_desc = str(row.get('Crm Cd Desc', '')).upper()
                
                # Check for serious crimes (High Risk - Cluster 0)
                if any(serious_crime in crime_desc for serious_crime in serious_crimes):
                    return 0  # High risk (Red)
                
                # Medium severity crimes (Medium Risk - Cluster 1)
                medium_crimes = [
                    'THEFT', 'VANDALISM', 'FRAUD', 'BATTERY', 'SHOPLIFTING',
                    'VEHICLE', 'STOLEN', 'TRESPASSING'
                ]
                
                if any(medium_crime in crime_desc for medium_crime in medium_crimes):
                    return 1  # Medium risk (Yellow)
                
                # Low severity crimes (Low Risk - Cluster 2)
                return 2  # Low risk (Green areas)
            
            df['Cluster'] = df.apply(classify_crime_severity, axis=1)
        
        return df
    except Exception as e:
        st.error(f"Error loading crime data: {e}")
        return None

# ================= ORIGINAL OSRM ROUTING (RESTORED) =================
def get_free_osrm_routes(start_coords, end_coords, travel_mode="driving"):
    """Get real road routes from free OSRM public server - ORIGINAL VERSION"""
    
    # OSRM profile mapping
    profile_mapping = {
        "driving": "driving",
        "walking": "foot", 
        "cycling": "bike"
    }
    
    profile = profile_mapping.get(travel_mode, "driving")
    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    
    # OSRM public server URL
    url = f"http://{OSRM_HOST}/route/v1/{profile}/{start_lon},{start_lat};{end_lon},{end_lat}"
    
    params = {
        "geometries": "geojson",
        "alternatives": "3",  # Get up to 3 alternative routes
        "steps": "false",
        "overview": "full"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("code") == "Ok" and data.get("routes"):
                routes = {}
                route_info = []
                
                for idx, route in enumerate(data["routes"][:3]):  # Max 3 routes
                    coordinates = route["geometry"]["coordinates"]
                    distance = route.get("distance", 0)
                    duration = route.get("duration", 0)
                    
                    route_data = {
                        "coordinates": coordinates,
                        "distance": f"{distance/1000:.1f} km",
                        "duration": f"{duration//60:.0f} min",
                        "distance_meters": distance,
                        "duration_seconds": duration
                    }
                    route_info.append(route_data)
                
                # Sort by duration and assign safety levels based on crime proximity
                sorted_routes = sorted(route_info, key=lambda x: x["duration_seconds"])
                
                if len(sorted_routes) >= 3:
                    routes["high_risk"] = sorted_routes[0]["coordinates"]      # Fastest (likely through busy/risky areas)
                    routes["medium_risk"] = sorted_routes[1]["coordinates"]    # Medium
                    routes["low_risk"] = sorted_routes[2]["coordinates"]        # Slowest/safest
                elif len(sorted_routes) == 2:
                    routes["high_risk"] = sorted_routes[0]["coordinates"]
                    routes["medium_risk"] = sorted_routes[1]["coordinates"]
                    routes["low_risk"] = create_safer_variation(sorted_routes[1]["coordinates"])
                else:
                    base_route = sorted_routes[0]["coordinates"]
                    routes["high_risk"] = base_route
                    routes["medium_risk"] = create_balanced_variation(base_route)
                    routes["low_risk"] = create_safer_variation(base_route)
                
                return routes, route_info
        
        return None, None
        
    except Exception as e:
        return None, None

def create_safer_variation(base_route):
    """Create a safer variation of a route - ORIGINAL VERSION"""
    if not base_route or len(base_route) < 3:
        return base_route
    
    # Add slight detours for safety
    safe_route = []
    for i, coord in enumerate(base_route):
        safe_route.append(coord)
        
        # Add safety detours every 5 segments
        if i > 0 and i < len(base_route) - 1 and i % 5 == 0:
            lon, lat = coord
            import math
            progress = i / len(base_route)
            detour_lat = lat + 0.002 * math.sin(progress * math.pi * 2)
            detour_lon = lon + 0.002 * math.cos(progress * math.pi * 1.5)
            safe_route.append([detour_lon, detour_lat])
    
    return safe_route

def create_balanced_variation(base_route):
    """Create a balanced variation of a route - ORIGINAL VERSION"""
    if not base_route or len(base_route) < 3:
        return base_route
    
    # Take every other point for a slightly different route
    balanced_route = []
    for i in range(0, len(base_route), 2):
        balanced_route.append(base_route[i])
    
    # Ensure start and end points
    if balanced_route[0] != base_route[0]:
        balanced_route.insert(0, base_route[0])
    if balanced_route[-1] != base_route[-1]:
        balanced_route.append(base_route[-1])
    
    return balanced_route

# ================= ORIGINAL FALLBACK SIMULATED ROUTES =================
def generate_simulated_routes(start_coords, end_coords, travel_mode="driving"):
    """Generate simulated routes when OSRM is unavailable - ORIGINAL VERSION"""
    
    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    
    routes = {}
    
    # Travel mode specific parameters
    mode_params = {
        "driving": {"waypoints": 15, "curve_factor": 0.001, "speed_factor": 1.0},
        "walking": {"waypoints": 25, "curve_factor": 0.0015, "speed_factor": 0.2},
        "cycling": {"waypoints": 20, "curve_factor": 0.0012, "speed_factor": 0.4}
    }
    
    params = mode_params.get(travel_mode, mode_params["driving"])
    waypoints = params["waypoints"]
    
    import math
    
    # High risk route (direct/fastest)
    direct_route = []
    for i in range(waypoints + 1):
        progress = i / waypoints
        lat = start_lat + (end_lat - start_lat) * progress
        lon = start_lon + (end_lon - start_lon) * progress
        direct_route.append([lon, lat])
    
    # Medium risk route (balanced)
    balanced_route = []
    for i in range(waypoints + 1):
        progress = i / waypoints
        lat = start_lat + (end_lat - start_lat) * progress
        lon = start_lon + (end_lon - start_lon) * progress
        
        if 0.2 <= progress <= 0.8:
            curve_factor = params["curve_factor"]
            lat += curve_factor * math.sin(progress * math.pi * 2)
            lon += curve_factor * math.cos(progress * math.pi * 1.5)
        
        balanced_route.append([lon, lat])
    
    # Low risk route (safer with detours)
    safe_route = []
    for i in range(waypoints + 1):
        progress = i / waypoints
        lat = start_lat + (end_lat - start_lat) * progress
        lon = start_lon + (end_lon - start_lon) * progress
        
        if 0.1 <= progress <= 0.9:
            detour_factor = params["curve_factor"] * 2
            lat += detour_factor * math.sin(progress * math.pi * 3)
            lon += detour_factor * math.cos(progress * math.pi * 2)
        
        safe_route.append([lon, lat])
    
    routes = {
        "high_risk": direct_route,
        "medium_risk": balanced_route,
        "low_risk": safe_route
    }
    
    return routes

# ================= ENHANCED ROUTE SAFETY ANALYSIS =================
def analyze_route_crime_exposure(route_coords, crime_df, proximity_threshold=0.005):
    """Analyze how much a route passes through different crime zones"""
    if crime_df is None or crime_df.empty or not route_coords:
        return {"high_crime_exposure": 0, "medium_crime_exposure": 0, "total_segments": len(route_coords)}
    
    try:
        # Get crime points by severity
        high_crime_points = crime_df[crime_df["Cluster"] == 0][["LAT", "LON"]].values  # Red dots
        medium_crime_points = crime_df[crime_df["Cluster"] == 1][["LAT", "LON"]].values  # Yellow dots
        
        high_crime_exposure = 0
        medium_crime_exposure = 0
        total_segments = len(route_coords)
        
        for lon, lat in route_coords:
            # Check proximity to high crime areas (red dots)
            if len(high_crime_points) > 0:
                high_distances = np.sqrt(np.sum((high_crime_points - [lat, lon])**2, axis=1))
                if np.any(high_distances < proximity_threshold):
                    high_crime_exposure += 1
                    continue  # If high crime found, don't check medium
            
            # Check proximity to medium crime areas (yellow dots)
            if len(medium_crime_points) > 0:
                medium_distances = np.sqrt(np.sum((medium_crime_points - [lat, lon])**2, axis=1))
                if np.any(medium_distances < proximity_threshold):
                    medium_crime_exposure += 1
        
        return {
            "high_crime_exposure": high_crime_exposure,
            "medium_crime_exposure": medium_crime_exposure,
            "total_segments": total_segments,
            "high_crime_percentage": (high_crime_exposure / total_segments) * 100,
            "medium_crime_percentage": (medium_crime_exposure / total_segments) * 100
        }
    
    except Exception:
        return {"high_crime_exposure": 0, "medium_crime_exposure": 0, "total_segments": total_segments}

def determine_route_safety_level(exposure_analysis):
    """Determine route safety level based on crime exposure with corrected thresholds"""
    high_percentage = exposure_analysis["high_crime_percentage"]
    medium_percentage = exposure_analysis["medium_crime_percentage"]
    total_percentage = high_percentage + medium_percentage
    
    # FIXED: More accurate thresholds for route coloring
    if high_percentage > 10:  # Routes with significant high-crime exposure
        return "high_risk", "red"
    elif high_percentage > 3 or total_percentage > 20:  # Some high crime or moderate total crime
        return "medium_risk", "orange"
    else:  # Minimal exposure to crime areas (should be green)
        return "low_risk", "green"

# ================= ORIGINAL GOOGLE MAPS-LIKE DISPLAY (RESTORED) =================
def create_enhanced_map(routes_data, crime_df, start_coords, end_coords, travel_mode, time_of_travel, safety_priority, route_info=None):
    """Create Google Maps-like visualization with crime-aware routing - ORIGINAL + ENHANCED"""
    
    center_lat = (start_coords[0] + end_coords[0]) / 2
    center_lon = (start_coords[1] + end_coords[1]) / 2
    
    # Create map with Google Maps-like styling - ORIGINAL
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=12,
        prefer_canvas=True
    )
    
    # Add multiple tile layers - ORIGINAL
    folium.TileLayer(
        tiles='OpenStreetMap',
        name='Street Map',
        overlay=False,
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
        attr='&copy; <a href="https://carto.com/attributions">CARTO</a>',
        name='Satellite-like',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Add crime data visualization - ENHANCED with time filtering
    if crime_df is not None and not crime_df.empty:
        crime_layer = folium.FeatureGroup(name=f"Crime Risk Zones ({time_of_travel})", show=True)
        
        # Sample for performance - ORIGINAL
        max_crime_points = 400
        if len(crime_df) > max_crime_points:
            crime_sample = crime_df.sample(n=max_crime_points, random_state=42)
        else:
            crime_sample = crime_df
        
        # Crime visualization with clear color coding - ORIGINAL
        crime_colors = {0: '#FF0000', 1: '#FFA500', 2: '#00FF00'}  # Red, Orange, Green
        crime_names = {0: 'High Crime Risk', 1: 'Medium Crime Risk', 2: 'Low Crime Risk'}
        
        for _, row in crime_sample.iterrows():
            cluster = row.get('Cluster', 1)
            color = crime_colors.get(cluster, '#FFA500')
            
            folium.CircleMarker(
                location=(row['LAT'], row['LON']),
                radius=3,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=1,
                popup=f"<b>{crime_names.get(cluster, 'Medium Risk')}</b><br>Area: {row.get('AREA NAME', 'Unknown')}"
            ).add_to(crime_layer)
        
        crime_layer.add_to(m)
    
    # ENHANCED: Analyze routes for actual safety colors
    route_metadata = {}
    for route_type, route_coords in routes_data.items():
        if route_coords:
            exposure = analyze_route_crime_exposure(route_coords, crime_df)
            safety_level, color = determine_route_safety_level(exposure)
            route_metadata[route_type] = {
                "exposure": exposure,
                "safety_level": safety_level,
                "color": color
            }
    
    # Add routes with ENHANCED crime-aware coloring but ORIGINAL Google Maps styling
    for route_type, route_coords in routes_data.items():
        if route_coords:
            # ENHANCED: Use actual crime exposure to determine color
            if route_type in route_metadata:
                metadata = route_metadata[route_type]
                actual_safety = metadata["safety_level"]
                
                if actual_safety == "low_risk":
                    color = "#00AA00"  # Green - actually safe
                    weight = 6
                    opacity = 0.9
                    label = "🟢 Safe Route"
                elif actual_safety == "medium_risk":
                    color = "#FF8C00"  # Orange - moderate risk
                    weight = 5
                    opacity = 0.8
                    label = "🟡 Moderate Risk Route"
                else:  # high_risk
                    color = "#DC143C"  # Red - high risk
                    weight = 5
                    opacity = 0.8
                    label = "🔴 High Risk Route"
            else:
                # ORIGINAL fallback styling
                route_styles = {
                    "low_risk": {"color": "#00FF00", "weight": 6, "opacity": 0.8, "label": "🟢 Safe Route"},
                    "medium_risk": {"color": "#FFA500", "weight": 5, "opacity": 0.7, "label": "🟡 Balanced Route"},
                    "high_risk": {"color": "#FF0000", "weight": 5, "opacity": 0.7, "label": "🔴 Direct Route"}
                }
                style = route_styles.get(route_type, route_styles["medium_risk"])
                color = style["color"]
                weight = style["weight"]
                opacity = style["opacity"]
                label = style["label"]
            
            route_points = [[lat, lon] for lon, lat in route_coords]
            
            # Add route info to popup if available - ORIGINAL
            popup_text = label
            if route_info:
                for info in route_info:
                    if info.get("coordinates") == route_coords:
                        popup_text += f"<br>Distance: {info.get('distance', 'N/A')}<br>Duration: {info.get('duration', 'N/A')}"
                        break
            
            folium.PolyLine(
                route_points,
                color=color,
                weight=weight,
                opacity=opacity,
                popup=popup_text
            ).add_to(m)
    
    # Add travel mode specific markers - ORIGINAL
    mode_icons = {
        "driving": "car",
        "walking": "walking",
        "cycling": "bicycle"
    }
    
    icon_name = mode_icons.get(travel_mode, "location-arrow")
    
    folium.Marker(
        location=start_coords,
        popup=f"<b>🏁 Start</b><br>Travel Mode: {travel_mode.title()}",
        icon=folium.Icon(color='green', icon=icon_name, prefix='fa')
    ).add_to(m)
    
    folium.Marker(
        location=end_coords,
        popup=f"<b>🎯 Destination</b><br>Mode: {travel_mode.title()}",
        icon=folium.Icon(color='red', icon='flag', prefix='fa')
    ).add_to(m)
    
    # ENHANCED legend with time and safety information
    legend_html = f'''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 280px; height: auto; 
                background: white; border: 2px solid #ccc; z-index:9999; 
                font-size: 13px; padding: 12px; border-radius: 8px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
    <p style="margin: 0 0 10px 0; font-weight: bold; color: #333;">🗺️ Smart Route Options - {travel_mode.title()}</p>
    <p style="margin: 2px 0; font-size: 11px;"><b>Time:</b> {time_of_travel}</p>
    <p style="margin: 2px 0; font-size: 11px;"><b>Safety:</b> {safety_priority.replace("_", " ").title()}</p>
    <hr style="margin: 8px 0; border: 1px solid #eee;">
    <p style="margin: 3px 0;"><span style="color:#00AA00; font-size: 16px;">●</span> Safe Route (Avoids Crime Zones)</p>
    <p style="margin: 3px 0;"><span style="color:#FF8C00; font-size: 16px;">●</span> Moderate Risk Route</p>
    <p style="margin: 3px 0;"><span style="color:#DC143C; font-size: 16px;">●</span> High Risk Route</p>
    <hr style="margin: 10px 0; border: 1px solid #eee;">
    <p style="margin: 0 0 6px 0; font-weight: bold; color: #333;">🚨 Crime Risk Zones:</p>
    <p style="margin: 2px 0;"><span style="color:#FF0000; font-size: 14px;">●</span> High Crime Risk</p>
    <p style="margin: 2px 0;"><span style="color:#FFA500; font-size: 14px;">●</span> Medium Crime Risk</p>
    <p style="margin: 2px 0;"><span style="color:#00FF00; font-size: 14px;">●</span> Low Crime Risk</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add layer control - ORIGINAL
    folium.LayerControl(position='topleft').add_to(m)
    
    return m, route_metadata

# ================= ENHANCED ROUTE ANALYSIS =================
def analyze_route_safety(routes_data, crime_df, safety_priority="balanced", time_of_travel="Any Time"):
    """Analyze route safety and provide intelligent recommendations with corrected logic"""
    
    if not routes_data:
        return "No routes available", "medium"
    
    route_scores = {}
    route_details = {}
    
    for route_type, route_coords in routes_data.items():
        if route_coords:
            exposure = analyze_route_crime_exposure(route_coords, crime_df)
            safety_level, _ = determine_route_safety_level(exposure)
            
            route_scores[route_type] = exposure["high_crime_percentage"]
            route_details[route_type] = {
                "exposure": exposure,
                "safety_level": safety_level
            }
    
    if not route_scores:
        return "No routes could be analyzed", "medium"
    
    # Find the safest route
    safest_route = min(route_scores.keys(), key=lambda x: route_scores[x])
    safest_score = route_scores[safest_route]
    
    # Check available safety levels
    safety_levels = [details["safety_level"] for details in route_details.values()]
    has_safe = "low_risk" in safety_levels
    has_medium = "medium_risk" in safety_levels
    has_risky = "high_risk" in safety_levels
    
    # FIXED: Generate contextual message with corrected thresholds
    if has_safe and safest_score < 2:
        return "✅ Excellent! Safe routes found with minimal crime zone exposure.", "success"
    elif has_safe:
        return "✅ Safe routes available! The green route avoids high-crime areas effectively.", "success"
    elif has_medium and not has_risky:
        return f"⚠️ Routes pass through some crime zones. Exercise normal caution.", "warning"
    elif has_medium and has_risky:
        return f"⚠️ This route passes through medium to high crime risk zones. Be aware while travelling.", "warning"
    elif has_risky:
        if safety_priority == "maximum_safety":
            return "🚨 No safe routes available for maximum safety settings. Consider different areas or times.", "error"
        else:
            return "🚨 High crime risk detected along the route. For more information, please check Route Safety Information.", "error"
    else:
        return "ℹ️ Route analysis completed. Review individual route safety details below.", "info"

# ================= OPTIMIZED ROUTE SAFETY DISPLAY =================
def get_simple_route_safety_message(route_metadata, crime_df, routes_data, time_of_travel="Any Time"):
    """Generate specific safety messages based on optimized route analysis"""
    if not route_metadata or crime_df is None or crime_df.empty:
        return "Route safety information is not available at this time."
    
    # Find the best (safest) route to analyze
    best_route = None
    lowest_risk = float('inf')
    
    for route_type, meta in route_metadata.items():
        risk_percentage = meta["exposure"]["high_crime_percentage"]
        if risk_percentage < lowest_risk:
            lowest_risk = risk_percentage
            best_route = route_type
    
    if best_route is None:
        return "Route safety analysis completed. Follow standard safety precautions during your travel."
    
    # Get data for the best route
    best_meta = route_metadata[best_route]
    exposure = best_meta["exposure"]
    
    # Calculate risk exposure percentage
    high_risk_percentage = exposure["high_crime_percentage"]
    medium_risk_percentage = exposure["medium_crime_percentage"]
    total_risk_percentage = high_risk_percentage + medium_risk_percentage
    
    # Only get peak crime time if user selected "Any Time"
    peak_crime_time = None
    if time_of_travel == "Any Time":
        peak_crime_time = get_route_specific_peak_crime_time(routes_data.get(best_route, []), crime_df)
    
    # Build the message
    message_parts = []
    
    # Risk exposure message with different logic for low risk
    if total_risk_percentage == 0:
        # Special case for 0% exposure
        emoji = "✅"
        message_parts.append(f"{emoji} The chosen route has {total_risk_percentage:.1f}% crime risk exposure.")
        
        # Peak crime time message only if "Any Time" selected
        if peak_crime_time and peak_crime_time != "Unknown":
            message_parts.append(f"Maximum crimes for this route occur during the {peak_crime_time.lower()}.")
        
        # Zero risk specific message
        message_parts.append("It also has low proximity to serious crimes since it has minimal to no crimes. It is safe to travel on this route.")
        
    elif total_risk_percentage < 20:
        risk_level = "not that high"
        emoji = "✅"
        
        # Regular low-risk messaging
        message_parts.append(f"{emoji} The chosen route has {total_risk_percentage:.1f}% crime risk exposure which is {risk_level}.")
        
        # Peak crime time message only if "Any Time" selected
        if peak_crime_time and peak_crime_time != "Unknown":
            message_parts.append(f"Maximum crimes for this route occur during the {peak_crime_time.lower()}.")
        
        # Low risk specific message
        if high_risk_percentage < 5:
            message_parts.append("It also has low proximity to serious crimes since it has minimal to no crimes. It is safe to travel on this route.")
        else:
            message_parts.append("It also has low proximity to serious crimes. It is safe to travel on this route.")
            
    elif total_risk_percentage < 40:
        risk_level = "moderate"
        emoji = "⚠️"
        
        message_parts.append(f"{emoji} The chosen route has {total_risk_percentage:.1f}% crime risk exposure which is {risk_level}.")
        
        # Peak crime time message only if "Any Time" selected
        if peak_crime_time and peak_crime_time != "Unknown":
            message_parts.append(f"Maximum crimes for this route occur during the {peak_crime_time.lower()}.")
        
        # Moderate risk messaging
        if high_risk_percentage > 5:
            message_parts.append("It also has moderate proximity to serious crimes.")
        else:
            message_parts.append("It also has low proximity to serious crimes.")
            
    else:
        risk_level = "high"
        emoji = "🚨"
        
        message_parts.append(f"{emoji} The chosen route has {total_risk_percentage:.1f}% crime risk exposure which is {risk_level}.")
        
        # Peak crime time message only if "Any Time" selected
        if peak_crime_time and peak_crime_time != "Unknown":
            message_parts.append(f"Maximum crimes for this route occur during the {peak_crime_time.lower()}.")
        
        # High risk messaging
        if high_risk_percentage > 15:
            message_parts.append("It also has high proximity to serious crimes. Consider alternative routes or travel times.")
        else:
            message_parts.append("It also has moderate proximity to serious crimes. Consider alternative routes or travel times.")
    
    return " ".join(message_parts)

@st.cache_data
def get_peak_crime_time_from_data(crime_df):
    """Get peak crime time from overall crime data (cached for performance)"""
    try:
        if 'Time of Day' not in crime_df.columns:
            return "Unknown"
        
        # Sample data for performance if dataset is large
        if len(crime_df) > 1000:
            sample_df = crime_df.sample(n=1000, random_state=42)
        else:
            sample_df = crime_df
        
        time_counts = sample_df['Time of Day'].value_counts()
        if not time_counts.empty:
            return time_counts.index[0]
        
        return "Unknown"
    except Exception:
        return "Unknown"

@st.cache_data
def analyze_crime_severity_distribution(crime_df):
    """Analyze overall crime severity distribution (cached for performance)"""
    try:
        if 'Cluster' not in crime_df.columns:
            return {"serious_percentage": 30}  # Default assumption
        
        # Sample for performance
        if len(crime_df) > 1000:
            sample_df = crime_df.sample(n=1000, random_state=42)
        else:
            sample_df = crime_df
        
        cluster_counts = sample_df['Cluster'].value_counts()
        total_crimes = len(sample_df)
        
        serious_crimes = cluster_counts.get(0, 0)  # High risk crimes
        serious_percentage = (serious_crimes / total_crimes) * 100 if total_crimes > 0 else 0
        
        return {"serious_percentage": serious_percentage}
    
    except Exception:
        return {"serious_percentage": 30}  # Default assumption

# ================= MAIN COMPUTATION FUNCTION WITH SIMPLIFIED DISPLAY =================
def compute_and_display_safe_route(start_area, end_area, travel_mode="driving", force_safe_route=False, 
                                 api_keys=None, safety_priority="balanced", time_of_travel="Any Time"):
    """Enhanced route computation with ORIGINAL Google Maps-style routing + simplified safety display"""
    
    try:
        # Load crime data with time filtering - ENHANCED
        crime_df = load_crime_data_with_time_filter(time_of_travel)
        if crime_df is None:
            st.error("Could not load crime data")
            return False
        
        # Get coordinates for areas - ORIGINAL
        start_data = crime_df[crime_df['AREA NAME'] == start_area][['LAT', 'LON']].dropna()
        end_data = crime_df[crime_df['AREA NAME'] == end_area][['LAT', 'LON']].dropna()
        
        if start_data.empty or end_data.empty:
            st.error(f"No coordinate data found for {start_area} or {end_area}")
            return False
        
        # Get center coordinates - ORIGINAL
        start_coords = start_data.mean()
        end_coords = end_data.mean()
        start_lat, start_lon = float(start_coords['LAT']), float(start_coords['LON'])
        end_lat, end_lon = float(end_coords['LAT']), float(end_coords['LON'])
        
        # ORIGINAL: Try to get real routes from free OSRM server
        routes, route_info = get_free_osrm_routes((start_lat, start_lon), (end_lat, end_lon), travel_mode)
        
        # ORIGINAL: Fallback to simulated routes if OSRM fails
        if routes is None:
            routes = generate_simulated_routes((start_lat, start_lon), (end_lat, end_lon), travel_mode)
            route_info = None
        
        # ENHANCED: Filter routes based on safety priority
        if safety_priority == "maximum_safety":
            # Analyze routes and keep only safe ones
            filtered_routes = {}
            for route_type, route_coords in routes.items():
                if route_coords:
                    exposure = analyze_route_crime_exposure(route_coords, crime_df)
                    safety_level, _ = determine_route_safety_level(exposure)
                    
                    # Only keep low and medium risk routes for maximum safety
                    if safety_level in ["low_risk", "medium_risk"]:
                        filtered_routes[route_type] = route_coords
            
            routes = filtered_routes if filtered_routes else routes
        
        elif safety_priority == "speed_priority":
            # Show all routes including risky ones - no filtering
            pass
        
        # For balanced, show all routes (original behavior)
        
        # ENHANCED: Analyze route safety with safety_priority parameter
        safety_message, safety_level = analyze_route_safety(routes, crime_df, safety_priority, time_of_travel)
        
        # Display safety message - ENHANCED
        if safety_level == "success":
            st.success(safety_message)
        elif safety_level == "warning":
            st.warning(safety_message)
        elif safety_level == "error":
            st.error(safety_message)
        else:
            st.info(safety_message)
        
        # ORIGINAL + ENHANCED: Create and display enhanced map with original routing
        map_obj, route_metadata = create_enhanced_map(
            routes, crime_df, 
            (start_lat, start_lon), (end_lat, end_lon), 
            travel_mode, time_of_travel, safety_priority, route_info
        )
        
        # Display map - ORIGINAL
        st_folium(map_obj, width=900, height=600, returned_objects=[])
        
        # ORIGINAL: Display travel time and distance information
        st.markdown("### ⏱️ Travel Time & Distance")
        
        if route_info:
            # Use real data from OSRM - ORIGINAL
            time_distance_cols = st.columns(3)
            
            for i, info in enumerate(route_info[:3]):
                route_names = ["🔴 Fastest Route", "🟡 Balanced Route", "🟢 Safest Route"]
                route_name = route_names[i] if i < 3 else f"Route {i+1}"
                
                with time_distance_cols[i]:
                    st.metric(
                        label=route_name,
                        value=f"⏱️ {info.get('duration', 'N/A')}",
                        delta=f"📏 {info.get('distance', 'N/A')}"
                    )
        else:
            # Calculate estimated times based on travel mode for simulated routes - ORIGINAL
            if routes:
                # Calculate base distance (rough estimate)
                import math
                lat_diff = end_lat - start_lat
                lon_diff = end_lon - start_lon
                distance_km = math.sqrt(lat_diff**2 + lon_diff**2) * 111  # Rough conversion to km
                
                # Travel mode speeds (km/h) - ORIGINAL
                speeds = {
                    "driving": 50,    # Urban driving speed
                    "walking": 5,     # Average walking speed
                    "cycling": 15     # Average cycling speed
                }
                
                base_speed = speeds.get(travel_mode, 50)
                
                time_distance_cols = st.columns(3)
                route_factors = {"high_risk": 1.0, "medium_risk": 1.2, "low_risk": 1.4}  # Safety routes are longer
                
                for i, (route_type, factor) in enumerate(route_factors.items()):
                    route_names = ["🔴 Fastest Route", "🟡 Balanced Route", "🟢 Safest Route"]
                    route_name = route_names[i]
                    
                    estimated_distance = distance_km * factor
                    estimated_time = (estimated_distance / base_speed) * 60  # Convert to minutes
                    
                    with time_distance_cols[i]:
                        st.metric(
                            label=route_name,
                            value=f"⏱️ {estimated_time:.0f} min",
                            delta=f"📏 {estimated_distance:.1f} km"
                        )
        
        # ORIGINAL: Add travel mode comparison
        st.markdown("### 🚗🚶🚴 Travel Mode Comparison")
        
        if route_info and len(route_info) > 0:
            # Use the balanced route as reference - ORIGINAL
            base_duration = route_info[0].get('duration_seconds', 3600)
            base_distance = route_info[0].get('distance_meters', 10000)
        else:
            # Estimate from coordinates - ORIGINAL
            import math
            lat_diff = end_lat - start_lat
            lon_diff = end_lon - start_lon
            base_distance = math.sqrt(lat_diff**2 + lon_diff**2) * 111000  # Convert to meters
            base_duration = 3600  # 1 hour default
        
        # Calculate times for different modes - ORIGINAL
        mode_factors = {
            "driving": {"time": 1.0, "icon": "🚗"},
            "cycling": {"time": 3.0, "icon": "🚴"},
            "walking": {"time": 10.0, "icon": "🚶"}
        }
        
        comparison_cols = st.columns(3)
        
        for i, (mode, data) in enumerate(mode_factors.items()):
            estimated_minutes = (base_duration * data["time"]) / 60
            
            with comparison_cols[i]:
                is_current = mode == travel_mode
                
                if is_current:
                    st.success(f"""
                    **{data["icon"]} {mode.title()} (Current)**
                    
                    ⏱️ **{estimated_minutes:.0f} minutes**
                    📏 **{base_distance/1000:.1f} km**
                    """)
                else:
                    st.info(f"""
                    **{data["icon"]} {mode.title()}**
                    
                    ⏱️ {estimated_minutes:.0f} minutes
                    📏 {base_distance/1000:.1f} km
                    """)
        
        st.markdown("*Times are estimates and may vary based on traffic, weather, and route conditions.*")
        
        # SIMPLIFIED: Display simple route safety message (REPLACED COMPLEX ANALYSIS)
        if routes and route_metadata:
            st.markdown("### 🛡️ Route Safety Information")
            
            # Get specific safety message with actual data analysis
            safety_info = get_simple_route_safety_message(route_metadata, crime_df, routes, time_of_travel)
            
            # Display the specific message
            if "✅" in safety_info:
                st.success(safety_info)
            elif "⚠️" in safety_info:
                st.warning(safety_info)
            elif "🚨" in safety_info:
                st.error(safety_info)
            else:
                st.info(safety_info)
            
            # Add simple recommendation
            st.write("**Recommendation:** Choose the green-colored route on the map for safest travel, or yellow for a balanced option.")
        
        # ORIGINAL: Risk Score Legend
        st.markdown("### 📊 Route Safety Guide")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.success("**🟢 Safe Routes**\nMinimal crime zone exposure (<20%)")
        with col2:
            st.warning("**🟡 Moderate Routes**\nSome crime zone exposure (20-40%)")
        with col3:
            st.error("**🔴 High Risk Routes**\nSignificant crime exposure (>40%)")
        
        # ENHANCED: Safety tips with time-awareness
        st.markdown(f"### 🛡️ Safety Tips for {travel_mode.title()} Travel")
        
        # Time-specific advice
        if "Night" in time_of_travel:
            st.warning(f"🌙 **Night Travel Warning ({time_of_travel})**: Crime rates are typically higher at night. Extra precautions recommended.")
        elif "Evening" in time_of_travel:
            st.info(f"🌆 **Evening Travel ({time_of_travel})**: Be extra vigilant during evening hours.")
        elif "Morning" in time_of_travel:
            st.success(f"☀️ **Morning Travel ({time_of_travel})**: Generally safest time period for travel.")
        
        # ORIGINAL: Mode-specific safety tips
        mode_tips = {
            "driving": [
                "🚗 Keep vehicle doors locked at all times",
                "⛽ Plan fuel stops in well-lit, busy areas",
                "📱 Use hands-free navigation to stay focused",
                "🚨 If you feel unsafe, drive to the nearest police station"
            ],
            "walking": [
                "👥 Walk with companions when possible",
                "🔦 Carry a flashlight for evening walks",
                "📱 Share your route and ETA with someone you trust",
                "👀 Stay alert and avoid distractions like headphones"
            ],
            "cycling": [
                "🚴‍♂️ Wear bright, reflective clothing for visibility",
                "🛡️ Always wear a properly fitted helmet",
                "🚲 Use designated bike lanes when available",
                "💡 Use front and rear lights during low visibility conditions"
            ]
        }
        
        tips = mode_tips.get(travel_mode, mode_tips["driving"])
        for tip in tips:
            st.write(f"- {tip}")
        
        return True
        
    except Exception as e:
        st.error(f"Error generating routes: {str(e)}")
        return False

# ================= SYSTEM INFO =================
def get_system_info():
    """Get information about the enhanced routing system"""
    return {
        "routing_system": "Google Maps-Style + Enhanced Crime Analysis",
        "features": [
            "Original Google Maps-like road routing",
            "Real OSRM server integration",
            "Time-of-day crime pattern filtering",
            "Dynamic route safety classification",
            "Safety-priority based route filtering",
            "Accurate crime exposure calculation"
        ],
        "routing_method": "OSRM public server with simulated fallback",
        "safety_analysis": "AI-powered crime zone proximity analysis"
    }
