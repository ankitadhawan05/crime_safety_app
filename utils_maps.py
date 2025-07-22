import requests
import pandas as pd
import folium
import streamlit as st
import numpy as np
from shapely.geometry import Point # type: ignore
from streamlit_folium import st_folium
from data_preprocess import load_crime_data, preprocess_for_clustering  # Updated imports
from clustering_engine import load_clustering_model, predict_clusters_safe  # Updated imports

# ================= ENHANCED CRIME DATA LOADING WITH TIME FILTERING =================
@st.cache_data
def load_time_filtered_crime_data(time_of_travel="Any Time"):
    """Load crime data with advanced time and severity filtering"""
    try:
        # Load raw data
        df = load_crime_data()
        
        # Add time of day if not present
        if 'Time of Day' not in df.columns:
            from data_preprocess import add_time_of_day
            df = add_time_of_day(df)
        
        # Apply time filtering
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
        
        # Enhanced crime severity classification
        def classify_advanced_crime_severity(row):
            """Advanced crime classification based on severity and victim impact"""
            crime_desc = str(row.get('Crm Cd Desc', '')).upper()
            
            # High Severity Crimes (Red dots) - Immediate danger to personal safety
            high_severity_keywords = [
                'ROBBERY', 'ASSAULT', 'BURGLARY', 'RAPE', 'HOMICIDE', 'MURDER',
                'KIDNAPPING', 'ARSON', 'SHOTS FIRED', 'CRIMINAL THREATS',
                'BATTERY', 'INTIMATE PARTNER', 'CHILD ABUSE', 'WEAPONS'
            ]
            
            if any(keyword in crime_desc for keyword in high_severity_keywords):
                return 0  # High risk (Red)
            
            # Medium Severity Crimes (Yellow dots) - Property and moderate crimes
            medium_severity_keywords = [
                'THEFT', 'VANDALISM', 'FRAUD', 'SHOPLIFTING', 'VEHICLE',
                'STOLEN', 'TRESPASSING', 'PICKPOCKET', 'BURGLARY TOOLS',
                'FORGERY', 'EMBEZZLEMENT', 'BRIBERY'
            ]
            
            if any(keyword in crime_desc for keyword in medium_severity_keywords):
                return 1  # Medium risk (Yellow)
            
            # Low Severity Crimes (Small green dots) - Minor incidents
            return 2  # Low risk (Green areas)
        
        df['Cluster'] = df.apply(classify_advanced_crime_severity, axis=1)
        
        return df
        
    except Exception as e:
        st.error(f"Error loading time-filtered crime data: {str(e)}")
        return None

# ================= ADVANCED ROUTE CRIME EXPOSURE ANALYSIS =================
def calculate_detailed_crime_exposure(route_coords, crime_df, proximity_thresholds=None):
    """Calculate detailed crime exposure with configurable thresholds"""
    
    if proximity_thresholds is None:
        proximity_thresholds = {
            'high_crime': 0.003,    # 300m for high-crime areas
            'medium_crime': 0.005,  # 500m for medium-crime areas  
            'low_crime': 0.008      # 800m for low-crime areas
        }
    
    if crime_df is None or crime_df.empty or not route_coords:
        return {
            'high_crime_segments': 0,
            'medium_crime_segments': 0,
            'safe_segments': 0,
            'total_segments': len(route_coords),
            'high_crime_percentage': 0,
            'medium_crime_percentage': 0,
            'safe_percentage': 0,
            'overall_risk_score': 0,
            'risk_level': 'low_risk'
        }
    
    try:
        # Extract crime points by severity
        high_crime_points = crime_df[crime_df["Cluster"] == 0][["LAT", "LON"]].values
        medium_crime_points = crime_df[crime_df["Cluster"] == 1][["LAT", "LON"]].values
        low_crime_points = crime_df[crime_df["Cluster"] == 2][["LAT", "LON"]].values
        
        # Initialize counters
        high_crime_segments = 0
        medium_crime_segments = 0
        safe_segments = 0
        total_segments = len(route_coords)
        
        # Analyze each route segment
        for lon, lat in route_coords:
            segment_classified = False
            
            # Check for high crime exposure (highest priority)
            if len(high_crime_points) > 0:
                high_distances = np.sqrt(np.sum((high_crime_points - [lat, lon])**2, axis=1))
                if np.any(high_distances < proximity_thresholds['high_crime']):
                    high_crime_segments += 1
                    segment_classified = True
            
            # Check for medium crime exposure (if not high crime)
            if not segment_classified and len(medium_crime_points) > 0:
                medium_distances = np.sqrt(np.sum((medium_crime_points - [lat, lon])**2, axis=1))
                if np.any(medium_distances < proximity_thresholds['medium_crime']):
                    medium_crime_segments += 1
                    segment_classified = True
            
            # If no crime exposure detected, it's safe
            if not segment_classified:
                safe_segments += 1
        
        # Calculate percentages
        high_crime_percentage = (high_crime_segments / total_segments) * 100 if total_segments > 0 else 0
        medium_crime_percentage = (medium_crime_segments / total_segments) * 100 if total_segments > 0 else 0
        safe_percentage = (safe_segments / total_segments) * 100 if total_segments > 0 else 0
        
        # Calculate overall risk score (weighted)
        risk_score = (high_crime_segments * 3) + (medium_crime_segments * 1) + (safe_segments * 0)
        
        # Determine risk level based on configurable thresholds
        if high_crime_percentage > 15:  # More than 15% through high-crime areas
            risk_level = 'high_risk'
        elif high_crime_percentage > 5 or medium_crime_percentage > 30:  # Some high crime or lots of medium crime
            risk_level = 'medium_risk'
        else:  # Minimal crime exposure
            risk_level = 'low_risk'
        
        return {
            'high_crime_segments': high_crime_segments,
            'medium_crime_segments': medium_crime_segments,
            'safe_segments': safe_segments,
            'total_segments': total_segments,
            'high_crime_percentage': high_crime_percentage,
            'medium_crime_percentage': medium_crime_percentage,
            'safe_percentage': safe_percentage,
            'overall_risk_score': risk_score,
            'risk_level': risk_level
        }
        
    except Exception as e:
        st.error(f"Error in crime exposure analysis: {str(e)}")
        return {
            'high_crime_segments': 0,
            'medium_crime_segments': 0,
            'safe_segments': total_segments,
            'total_segments': total_segments,
            'high_crime_percentage': 0,
            'medium_crime_percentage': 0,
            'safe_percentage': 100,
            'overall_risk_score': 0,
            'risk_level': 'low_risk'
        }

# ================= INTELLIGENT ROUTE GENERATION WITH SAFETY FILTERING =================
def generate_safety_filtered_routes(start_coords, end_coords, crime_df, safety_priority="balanced", 
                                   time_of_travel="Any Time", num_base_routes=8):
    """Generate multiple route variations and filter based on safety priority"""
    
    # Generate diverse base routes
    base_routes = []
    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    
    # Create different route patterns for analysis
    route_patterns = [
        {"name": "direct", "waypoints": 12, "detour": 0.0},
        {"name": "northern_arc", "waypoints": 15, "detour": 0.008},
        {"name": "southern_arc", "waypoints": 15, "detour": -0.008},
        {"name": "eastern_detour", "waypoints": 18, "detour": 0.006},
        {"name": "western_detour", "waypoints": 18, "detour": -0.006},
        {"name": "conservative", "waypoints": 22, "detour": 0.012},
        {"name": "scenic_route", "waypoints": 20, "detour": 0.010},
        {"name": "highway_style", "waypoints": 10, "detour": 0.002}
    ]
    
    for i, pattern in enumerate(route_patterns[:num_base_routes]):
        route_coords = []
        waypoints = pattern["waypoints"]
        detour = pattern["detour"]
        
        for j in range(waypoints + 1):
            progress = j / waypoints
            
            # Base interpolation
            lat = start_lat + (end_lat - start_lat) * progress
            lon = start_lon + (end_lon - start_lon) * progress
            
            # Apply route-specific modifications
            if pattern["name"] == "direct":
                pass  # No modification for direct route
            elif pattern["name"] == "northern_arc":
                if 0.2 <= progress <= 0.8:
                    lat += detour * np.sin(progress * np.pi)
            elif pattern["name"] == "southern_arc":
                if 0.2 <= progress <= 0.8:
                    lat += detour * np.sin(progress * np.pi)
            elif pattern["name"] == "eastern_detour":
                if 0.3 <= progress <= 0.7:
                    lon += detour * np.cos(progress * np.pi * 2)
            elif pattern["name"] == "western_detour":
                if 0.3 <= progress <= 0.7:
                    lon += detour * np.cos(progress * np.pi * 2)
            elif pattern["name"] == "conservative":
                # Add multiple small detours for safety
                if 0.15 <= progress <= 0.85:
                    lat += detour * 0.7 * np.sin(progress * np.pi * 3)
                    lon += detour * 0.5 * np.cos(progress * np.pi * 2.5)
            elif pattern["name"] == "scenic_route":
                # Curved route that might avoid urban centers
                if 0.2 <= progress <= 0.8:
                    lat += detour * np.sin(progress * np.pi * 2)
                    lon += detour * 0.6 * np.cos(progress * np.pi * 1.8)
            elif pattern["name"] == "highway_style":
                # More direct with minimal detours (potentially higher risk)
                if 0.4 <= progress <= 0.6:
                    lat += detour * np.sin(progress * np.pi * 4)
            
            route_coords.append([lon, lat])
        
        base_routes.append({
            "coords": route_coords,
            "pattern": pattern["name"],
            "base_risk_estimate": i  # Higher index = potentially more detour
        })
    
    # Analyze crime exposure for each route
    route_analyses = []
    for i, route_data in enumerate(base_routes):
        exposure_analysis = calculate_detailed_crime_exposure(route_data["coords"], crime_df)
        
        route_analyses.append({
            "route_id": i,
            "coords": route_data["coords"],
            "pattern": route_data["pattern"],
            "exposure": exposure_analysis,
            "safety_level": exposure_analysis["risk_level"],
            "risk_score": exposure_analysis["overall_risk_score"]
        })
    
    # Filter and select routes based on safety priority
    selected_routes = {}
    route_metadata = {}
    
    # Sort routes by safety (lower risk score = safer)
    sorted_routes = sorted(route_analyses, key=lambda x: x["risk_score"])
    
    # Categorize routes by safety level
    green_routes = [r for r in sorted_routes if r["safety_level"] == "low_risk"]
    yellow_routes = [r for r in sorted_routes if r["safety_level"] == "medium_risk"]
    red_routes = [r for r in sorted_routes if r["safety_level"] == "high_risk"]
    
    # Select routes based on safety priority
    if safety_priority == "maximum_safety":
        # Only show green and yellow routes
        if green_routes:
            selected_routes["low_risk"] = green_routes[0]["coords"]
            route_metadata["low_risk"] = green_routes[0]
        if yellow_routes:
            selected_routes["medium_risk"] = yellow_routes[0]["coords"] 
            route_metadata["medium_risk"] = yellow_routes[0]
        # No red routes in maximum safety mode
        
    elif safety_priority == "fastest":
        # Show all route types, prioritizing directness over safety
        if red_routes:
            selected_routes["high_risk"] = red_routes[0]["coords"]
            route_metadata["high_risk"] = red_routes[0]
        if yellow_routes:
            selected_routes["medium_risk"] = yellow_routes[0]["coords"]
            route_metadata["medium_risk"] = yellow_routes[0]
        if green_routes:
            selected_routes["low_risk"] = green_routes[0]["coords"]
            route_metadata["low_risk"] = green_routes[0]
            
    else:  # balanced
        # Show best route from each category if available
        if green_routes:
            selected_routes["low_risk"] = green_routes[0]["coords"]
            route_metadata["low_risk"] = green_routes[0]
        if yellow_routes:
            selected_routes["medium_risk"] = yellow_routes[0]["coords"]
            route_metadata["medium_risk"] = yellow_routes[0]
        if red_routes and len(selected_routes) < 2:  # Only add red if we don't have enough options
            selected_routes["high_risk"] = red_routes[0]["coords"]
            route_metadata["high_risk"] = red_routes[0]
    
    return selected_routes, route_metadata

# ================= ENHANCED MAP VISUALIZATION WITH ACCURATE COLORS =================
def create_accurate_crime_map(routes_data, route_metadata, crime_df, start_coords, end_coords, 
                             travel_mode, time_of_travel, safety_priority):
    """Create map with accurate route colors based on actual crime exposure"""
    
    center_lat = (start_coords[0] + end_coords[0]) / 2
    center_lon = (start_coords[1] + end_coords[1]) / 2
    
    # Create map with enhanced styling
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=12,
        prefer_canvas=True
    )
    
    # Add enhanced tile layers
    folium.TileLayer('OpenStreetMap', name='Street Map', overlay=False, control=True).add_to(m)
    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
        attr='&copy; <a href="https://carto.com/attributions">CARTO</a>',
        name='Clean View',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Crime data visualization with enhanced accuracy
    if crime_df is not None and not crime_df.empty:
        crime_layer = folium.FeatureGroup(name=f"Crime Zones - {time_of_travel}", show=True)
        
        # Intelligent sampling for performance
        max_points = 600
        if len(crime_df) > max_points:
            # Stratified sampling to maintain crime distribution
            high_crime = crime_df[crime_df["Cluster"] == 0]
            medium_crime = crime_df[crime_df["Cluster"] == 1]  
            low_crime = crime_df[crime_df["Cluster"] == 2]
            
            # Sample proportionally
            high_sample = min(len(high_crime), max_points // 2)
            medium_sample = min(len(medium_crime), max_points // 3)
            low_sample = min(len(low_crime), max_points // 6)
            
            crime_sample = pd.concat([
                high_crime.sample(n=high_sample, random_state=42) if high_sample > 0 else pd.DataFrame(),
                medium_crime.sample(n=medium_sample, random_state=42) if medium_sample > 0 else pd.DataFrame(),
                low_crime.sample(n=low_sample, random_state=42) if low_sample > 0 else pd.DataFrame()
            ])
        else:
            crime_sample = crime_df
        
        # Add crime points with enhanced visualization
        for _, row in crime_sample.iterrows():
            cluster = row.get('Cluster', 1)
            crime_type = row.get('Crm Cd Desc', 'Unknown Crime')
            area_name = row.get('AREA NAME', 'Unknown Area')
            
            # Enhanced color scheme and sizing
            if cluster == 0:  # High crime (Red)
                color = '#DC143C'
                fill_color = '#FF6B6B'
                radius = 5
                weight = 2
                fillOpacity = 0.8
                popup_text = f"""
                <b>🔴 HIGH CRIME RISK</b><br>
                <b>Type:</b> {crime_type}<br>
                <b>Area:</b> {area_name}<br>
                <b>Time:</b> {time_of_travel}<br>
                <b>Risk:</b> Routes should avoid this area
                """
            elif cluster == 1:  # Medium crime (Yellow/Orange)
                color = '#FF8C00'
                fill_color = '#FFD700'
                radius = 3
                weight = 1
                fillOpacity = 0.6
                popup_text = f"""
                <b>🟡 MEDIUM CRIME RISK</b><br>
                <b>Type:</b> {crime_type}<br>
                <b>Area:</b> {area_name}<br>
                <b>Time:</b> {time_of_travel}<br>
                <b>Risk:</b> Exercise caution in this area
                """
            else:  # Low crime (Light green)
                color = '#32CD32'
                fill_color = '#98FB98'
                radius = 2
                weight = 1
                fillOpacity = 0.4
                popup_text = f"""
                <b>🟢 LOW CRIME RISK</b><br>
                <b>Type:</b> {crime_type}<br>
                <b>Area:</b> {area_name}<br>
                <b>Time:</b> {time_of_travel}<br>
                <b>Risk:</b> Generally safe area
                """
            
            folium.CircleMarker(
                location=(row['LAT'], row['LON']),
                radius=radius,
                color=color,
                fill=True,
                fillColor=fill_color,
                fillOpacity=fillOpacity,
                weight=weight,
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(crime_layer)
        
        crime_layer.add_to(m)
    
    # Add routes with ACCURATE safety-based coloring
    for route_type, route_coords in routes_data.items():
        if route_coords and route_type in route_metadata:
            metadata = route_metadata[route_type]
            exposure = metadata["exposure"]
            
            # Determine ACTUAL route color based on crime exposure analysis
            actual_safety_level = exposure["risk_level"]
            high_crime_pct = exposure["high_crime_percentage"]
            medium_crime_pct = exposure["medium_crime_percentage"]
            
            # Color based on ACTUAL risk analysis
            if actual_safety_level == "low_risk":
                color = "#00AA00"  # Green - actually safe
                weight = 6
                opacity = 0.9
                dash_array = None
                route_label = "🟢 Safe Route"
                safety_desc = f"Minimal crime exposure ({high_crime_pct:.1f}% high-risk areas)"
            elif actual_safety_level == "medium_risk":
                color = "#FF8C00"  # Orange - moderate risk
                weight = 5
                opacity = 0.8
                dash_array = "10,5"
                route_label = "🟡 Moderate Risk"
                safety_desc = f"Some crime exposure ({high_crime_pct:.1f}% high-risk, {medium_crime_pct:.1f}% medium-risk)"
            else:  # high_risk
                color = "#DC143C"  # Red - high risk
                weight = 5
                opacity = 0.8
                dash_array = "5,5"
                route_label = "🔴 High Risk Route"
                safety_desc = f"Significant crime exposure ({high_crime_pct:.1f}% high-risk areas)"
            
            # Convert route coordinates
            route_points = [[lat, lon] for lon, lat in route_coords]
            
            # Detailed popup with risk analysis
            popup_html = f"""
            <div style="width: 250px;">
                <h4>{route_label}</h4>
                <p><b>Travel Mode:</b> {travel_mode.title()}</p>
                <p><b>Time Period:</b> {time_of_travel}</p>
                <hr>
                <p><b>Crime Exposure Analysis:</b></p>
                <p>🔴 High Crime: {high_crime_pct:.1f}%</p>
                <p>🟡 Medium Crime: {medium_crime_pct:.1f}%</p>
                <p>🟢 Safe Segments: {exposure['safe_percentage']:.1f}%</p>
                <hr>
                <p><small>{safety_desc}</small></p>
            </div>
            """
            
            folium.PolyLine(
                route_points,
                color=color,
                weight=weight,
                opacity=opacity,
                dash_array=dash_array,
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(m)
    
    # Enhanced start/end markers
    folium.Marker(
        location=start_coords,
        popup=folium.Popup(f"""
        <b>🏁 STARTING POINT</b><br>
        <b>Mode:</b> {travel_mode.title()}<br>
        <b>Time:</b> {time_of_travel}<br>
        <b>Safety Priority:</b> {safety_priority.title()}
        """, max_width=200),
        icon=folium.Icon(color='green', icon='play', prefix='fa')
    ).add_to(m)
    
    folium.Marker(
        location=end_coords,
        popup=folium.Popup(f"""
        <b>🎯 DESTINATION</b><br>
        <b>Mode:</b> {travel_mode.title()}<br>
        <b>Routes Generated:</b> {len(routes_data)}
        """, max_width=200),
        icon=folium.Icon(color='red', icon='flag', prefix='fa')
    ).add_to(m)
    
    # Comprehensive legend
    legend_html = f'''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 320px; height: auto; 
                background: rgba(255, 255, 255, 0.95); 
                border: 2px solid #333; z-index:9999; 
                font-size: 11px; padding: 10px; border-radius: 10px;
                box-shadow: 0 6px 20px rgba(0,0,0,0.3); font-family: Arial, sans-serif;">
    
    <div style="text-align: center; margin-bottom: 8px;">
        <h3 style="margin: 0; color: #333;">🧠 Smart Crime-Aware Routes</h3>
        <p style="margin: 2px 0; font-weight: bold; color: #555;">{travel_mode.title()} • {time_of_travel} • {safety_priority.title()}</p>
    </div>
    
    <div style="border-top: 1px solid #ddd; padding-top: 6px; margin-bottom: 6px;">
        <p style="margin: 0 0 4px 0; font-weight: bold; color: #333;">📍 Crime Risk Zones ({time_of_travel}):</p>
        <div style="display: flex; align-items: center; margin: 1px 0;">
            <span style="color:#DC143C; font-size: 16px; margin-right: 6px;">●</span>
            <span>High Risk - Serious crimes (avoid if possible)</span>
        </div>
        <div style="display: flex; align-items: center; margin: 1px 0;">
            <span style="color:#FF8C00; font-size: 14px; margin-right: 8px;">●</span>
            <span>Medium Risk - Property crimes (use caution)</span>
        </div>
        <div style="display: flex; align-items: center; margin: 1px 0;">
            <span style="color:#32CD32; font-size: 12px; margin-right: 10px;">●</span>
            <span>Low Risk - Minor incidents (generally safe)</span>
        </div>
    </div>
    
    <div style="border-top: 1px solid #ddd; padding-top: 6px; margin-bottom: 6px;">
        <p style="margin: 0 0 4px 0; font-weight: bold; color: #333;">🛣️ Route Safety (AI-Analyzed):</p>
        <div style="display: flex; align-items: center; margin: 1px 0;">
            <span style="color:#00AA00; font-size: 16px; margin-right: 6px;">━</span>
            <span><b>Safe Route</b> - &lt;5% high-crime exposure</span>
        </div>
        <div style="display: flex; align-items: center; margin: 1px 0;">
            <span style="color:#FF8C00; font-size: 16px; margin-right: 6px;">┅</span>
            <span><b>Moderate Route</b> - 5-15% high-crime exposure</span>
        </div>
        <div style="display: flex; align-items: center; margin: 1px 0;">
            <span style="color:#DC143C; font-size: 16px; margin-right: 6px;">┉</span>
            <span><b>High Risk Route</b> - &gt;15% high-crime exposure</span>
        </div>
    </div>
    
    <div style="border-top: 1px solid #ddd; padding-top: 6px;">
        <p style="margin: 0; font-size: 10px; color: #666; text-align: center;">
            🎯 Routes dynamically colored by actual crime zone proximity<br>
            💡 Click routes for detailed safety analysis
        </p>
    </div>
    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(legend_html))
    folium.LayerControl(position='topleft').add_to(m)
    
    return m

# ================= INTELLIGENT SAFETY MESSAGE GENERATION =================
def generate_intelligent_safety_message(routes_data, route_metadata, safety_priority, time_of_travel):
    """Generate contextual safety messages based on actual route analysis"""
    
    if not routes_data or not route_metadata:
        return "No routes available for the selected criteria.", "error"
    
    # Analyze available routes
    safety_levels = []
    high_crime_exposures = []
    
    for route_type, metadata in route_metadata.items():
        safety_levels.append(metadata["exposure"]["risk_level"])
        high_crime_exposures.append(metadata["exposure"]["high_crime_percentage"])
    
    has_safe_route = "low_risk" in safety_levels
    has_moderate_route = "medium_risk" in safety_levels
    has_risky_route = "high_risk" in safety_levels
    
    max_high_crime_exposure = max(high_crime_exposures) if high_crime_exposures else 0
    
    # Generate contextual message
    if has_safe_route and max_high_crime_exposure < 3:
        message = "✅ Excellent! Safe routes found with minimal crime zone exposure."
        level = "success"
    elif has_safe_route:
        message = "✅ Safe routes available! The green route avoids high-crime areas effectively."
        level = "success"
    elif has_moderate_route and not has_risky_route:
        message = f"⚠️ Routes pass through some crime zones ({max_high_crime_exposure:.1f}% high-risk exposure). Exercise normal caution."
        level = "warning"
    elif has_moderate_route and has_risky_route:
        message = f"⚠️ This route passes through medium to high crime risk zones. Be aware while travelling."
        level = "warning"
    elif has_risky_route:
        if safety_priority == "maximum_safety":
            message = "🚨 No safe routes available for maximum safety settings. Consider different areas or times."
            level = "error"
        else:
            message = f"🚨 High crime risk detected ({max_high_crime_exposure:.1f}% exposure). Consider alternative routes or travel times."
            level = "error"
    else:
        message = "ℹ️ Route analysis completed. Review individual route safety details below."
        level = "info"
    
    # Add time-specific context
    if "Night" in time_of_travel and has_risky_route:
        message += f" Night travel amplifies risks - extra precautions strongly recommended."
    elif "Night" in time_of_travel:
        message += f" Night travel detected - stay alert even on safer routes."
    
    return message, level

# ================= MAIN ENHANCED COMPUTATION FUNCTION =================
def compute_and_display_safe_route(start_area, end_area, travel_mode="driving", force_safe_route=False, 
                                 api_keys=None, safety_priority="balanced", time_of_travel="Any Time"):
    """Enhanced route computation with accurate crime-based safety analysis"""
    
    try:
        # Load time-filtered crime data
        crime_df = load_time_filtered_crime_data(time_of_travel)
        if crime_df is None:
            st.error("❌ Could not load crime data for the specified time period.")
            return False
        
        # Validate areas have sufficient data
        start_data = crime_df[crime_df['AREA NAME'] == start_area][['LAT', 'LON']].dropna()
        end_data = crime_df[crime_df['AREA NAME'] == end_area][['LAT', 'LON']].dropna()
        
        if start_data.empty:
            st.error(f"❌ No location data found for {start_area} in {time_of_travel} time period.")
            return False
        
        if end_data.empty:
            st.error(f"❌ No location data found for {end_area} in {time_of_travel} time period.")
            return False
        
        # Calculate center coordinates
        start_coords = start_data.mean()
        end_coords = end_data.mean()
        start_lat, start_lon = float(start_coords['LAT']), float(start_coords['LON'])
        end_lat, end_lon = float(end_coords['LAT']), float(end_coords['LON'])
        
        # Generate safety-filtered routes
        with st.spinner("🧠 Analyzing crime patterns and generating intelligent routes..."):
            routes, route_metadata = generate_safety_filtered_routes(
                (start_lat, start_lon), (end_lat, end_lon), 
                crime_df, safety_priority, time_of_travel
            )
        
        if not routes:
            st.error(f"❌ No routes meeting {safety_priority} safety criteria found.")
            return False
        
        # Generate intelligent safety message
        safety_message, message_level = generate_intelligent_safety_message(
            routes, route_metadata, safety_priority, time_of_travel
        )
        
        # Display safety message with appropriate styling
        if message_level == "success":
            st.success(safety_message)
        elif message_level == "warning":
            st.warning(safety_message)
        elif message_level == "error":
            st.error(safety_message)
        else:
            st.info(safety_message)
        
        # Create and display the accurate crime-aware map
        map_obj = create_accurate_crime_map(
            routes, route_metadata, crime_df,
            (start_lat, start_lon), (end_lat, end_lon),
            travel_mode, time_of_travel, safety_priority
        )
        
        # Display the map
        st_folium(map_obj, width=900, height=650, returned_objects=[])
        
        # Enhanced route analysis display
        if routes and route_metadata:
            st.markdown("### 📊 Detailed Route Safety Analysis")
            
            # Sort routes by safety level for display
            route_display_order = []
            for safety_level in ["low_risk", "medium_risk", "high_risk"]:
                for route_type, metadata in route_metadata.items():
                    if metadata["exposure"]["risk_level"] == safety_level:
                        route_display_order.append((route_type, metadata))
            
            # Create columns for route analysis
            if len(route_display_order) > 0:
                cols = st.columns(len(route_display_order))
                
                for i, (route_type, metadata) in enumerate(route_display_order):
                    exposure = metadata["exposure"]
                    actual_safety = exposure["risk_level"]
                    
                    with cols[i]:
                        # Display route with accurate coloring
                        if actual_safety == "low_risk":
                            st.success("🟢 **SAFE ROUTE**")
                            recommendation = "✅ Recommended - Low crime exposure"
                            st.markdown(f"**Crime Exposure:** {exposure['high_crime_percentage']:.1f}% high-risk")
                        elif actual_safety == "medium_risk":
                            st.warning("🟡 **MODERATE RISK**") 
                            recommendation = "⚠️ Use caution - Some crime zones"
                            st.markdown(f"**Crime Exposure:** {exposure['high_crime_percentage']:.1f}% high-risk")
                        else:
                            st.error("🔴 **HIGH RISK ROUTE**")
                            recommendation = "🚨 Not recommended - Significant crime exposure"
                            st.markdown(f"**Crime Exposure:** {exposure['high_crime_percentage']:.1f}% high-risk")
                        
                        # Detailed metrics
                        st.metric("High Crime Segments", f"{exposure['high_crime_segments']}/{exposure['total_segments']}")
                        st.metric("Medium Crime Segments", f"{exposure['medium_crime_segments']}/{exposure['total_segments']}")
                        st.metric("Safe Segments", f"{exposure['safe_segments']}/{exposure['total_segments']}")
                        
                        st.markdown(f"**🎯 {recommendation}**")
                        
                        # Route pattern information
                        st.caption(f"Pattern: {metadata.get('pattern', 'Unknown')}")
            
            # Time-specific safety recommendations
            st.markdown(f"### 🛡️ Safety Recommendations for {travel_mode.title()} at {time_of_travel}")
            
            # Time-based advice
            if "Night" in time_of_travel:
                st.error("""
                🌙 **NIGHT TRAVEL - HIGH ALERT**:
                - Crime rates increase significantly at night
                - Only use green routes if available
                - Avoid red routes completely during night hours
                - Travel in groups when possible
                - Keep emergency contacts ready
                """)
            elif "Evening" in time_of_travel:
                st.warning("""
                🌆 **EVENING CAUTION**:
                - Crime activity begins to increase
                - Prefer green and yellow routes
                - Avoid isolated areas
                - Complete travel before full darkness
                """)
            elif "Morning" in time_of_travel:
                st.success("""
                ☀️ **MORNING TRAVEL - OPTIMAL**:
                - Generally safest time period
                - Most crime types are at lowest levels
                - All route colors are relatively safer
                - Good visibility and activity levels
                """)
            else:  # Afternoon
                st.info("""
                🌤️ **AFTERNOON TRAVEL**:
                - Moderate safety conditions
                - Property crimes may be elevated
                - Generally safe with normal precautions
                """)
            
            # Mode-specific enhanced tips
            mode_safety_tips = {
                "driving": [
                    "🚗 Keep doors locked and windows up at all times",
                    "⛽ Plan fuel stops in well-lit, busy locations only",
                    "📱 Use hands-free navigation - avoid phone distractions",
                    "🚨 If threatened, drive to nearest police station",
                    "💰 Keep valuables out of sight in vehicle",
                    "🅿️ Park only in well-lit areas with security"
                ],
                "walking": [
                    "👥 Walk with companions, especially during evening/night",
                    "🔦 Carry flashlight and keep phone fully charged",
                    "📱 Share live location with trusted contact",
                    "👀 Stay alert - avoid headphones in risky areas",
                    "🏃‍♂️ Trust instincts - leave if situation feels unsafe",
                    "💰 Keep valuables secure and out of sight"
                ],
                "cycling": [
                    "🚴‍♂️ Wear bright, reflective clothing for visibility",
                    "🛡️ Always wear properly fitted helmet",
                    "🚲 Use designated bike lanes when available",
                    "💡 Use front/rear lights during low visibility",
                    "🔒 Secure bike with high-quality lock when stopping",
                    "⚠️ Avoid cycling alone during night hours"
                ]
            }
            
            tips = mode_safety_tips.get(travel_mode, mode_safety_tips["driving"])
            for tip in tips:
                st.write(f"- {tip}")
            
            # Additional contextual warnings based on route analysis
            st.markdown("### ⚠️ Route-Specific Warnings")
            
            high_risk_routes = [rt for rt, meta in route_metadata.items() 
                              if meta["exposure"]["risk_level"] == "high_risk"]
            medium_risk_routes = [rt for rt, meta in route_metadata.items() 
                                if meta["exposure"]["risk_level"] == "medium_risk"]
            
            if high_risk_routes:
                st.error(f"""
                🚨 **HIGH RISK ROUTES DETECTED**: {len(high_risk_routes)} route(s) pass through significant crime zones.
                - Consider alternative areas or travel times
                - If travel is necessary, use extreme caution
                - Inform others of your route and expected arrival
                - Consider professional security escort if available
                """)
            
            if medium_risk_routes and "Night" in time_of_travel:
                st.warning(f"""
                ⚠️ **NIGHT + MEDIUM RISK COMBINATION**: Exercise heightened caution.
                - Medium-risk areas become higher risk at night
                - Consider postponing travel until morning if possible
                - Use additional safety measures if travel necessary
                """)
            
            # Emergency contact information
            st.markdown("### 🆘 Emergency Information")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.error("""
                **🚨 EMERGENCY**
                - **Police**: 911
                - **Fire/Medical**: 911
                - **Crisis Line**: 988
                """)
            
            with col2:
                st.warning("""
                **🚔 NON-EMERGENCY**
                - **Police Reports**: 311
                - **Traffic Issues**: 311
                - **City Services**: 311
                """)
            
            with col3:
                st.info("""
                **📱 SAFETY APPS**
                - Share location with contacts
                - Emergency alert apps
                - Local safety notifications
                """)
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error in route computation: {str(e)}")
        
        # Enhanced error handling with specific guidance
        with st.expander("🔧 Detailed Error Information", expanded=False):
            st.code(f"""
            Error Type: {type(e).__name__}
            Error Message: {str(e)}
            
            Troubleshooting Steps:
            1. Verify selected areas have crime data for {time_of_travel}
            2. Try different time periods (Any Time for broader coverage)
            3. Select major areas with more data points
            4. Check if safety priority settings are too restrictive
            5. Ensure start and end areas are different
            """)
        
        return False

# ================= BACKWARDS COMPATIBILITY FUNCTIONS =================
@st.cache_data 
def get_fast_clustered_data():
    """Backwards compatibility function"""
    return load_time_filtered_crime_data("Any Time")

def get_clustered_crime_data_safe():
    """Backwards compatibility function"""
    return load_time_filtered_crime_data("Any Time")

def score_route_risk(route_coords, clustered_df, risk_threshold=0.005):
    """Backwards compatibility function"""
    exposure = calculate_detailed_crime_exposure(route_coords, clustered_df)
    return exposure["overall_risk_score"], {
        "high_risk": exposure["high_crime_segments"],
        "medium_risk": exposure["medium_crime_segments"],
        "safe_segments": exposure["safe_segments"]
    }

def display_multi_route_map(routes_data, clustered_df, start_coords, end_coords, travel_mode):
    """Backwards compatibility function"""
    # Create dummy metadata for backwards compatibility
    route_metadata = {}
    for route_type, route_coords in routes_data.items():
        exposure = calculate_detailed_crime_exposure(route_coords, clustered_df)
        route_metadata[route_type] = {"exposure": exposure}
    
    map_obj = create_accurate_crime_map(
        routes_data, route_metadata, clustered_df,
        start_coords, end_coords, travel_mode, "Any Time", "balanced"
    )
    
    return map_obj, route_metadata

def generate_multiple_routes_real_roads(start_coords, end_coords, travel_mode="driving", api_keys=None):
    """Backwards compatibility function"""
    # Load default crime data
    crime_df = load_time_filtered_crime_data("Any Time")
    routes, _ = generate_safety_filtered_routes(start_coords, end_coords, crime_df, "balanced")
    return routes

def get_route_recommendation(risk_scores, travel_mode):
    """Backwards compatibility function"""
    if not risk_scores:
        return {"status": "error", "message": "No routes available", "color": "error"}
    
    min_risk = min(risk_scores.values())
    
    if min_risk <= 5:
        return {"status": "safe", "message": "✅ Safe routes available", "color": "success"}
    elif min_risk <= 15:
        return {"status": "moderate", "message": "⚠️ Moderate risk detected", "color": "warning"}
    else:
        return {"status": "unsafe", "message": "🚨 High risk detected", "color": "error"}

# ================= SYSTEM INFORMATION =================
def get_enhanced_system_info():
    """Get comprehensive information about the enhanced system"""
    return {
        "system_name": "Dynamic Crime-Aware Routing System",
        "version": "2.0",
        "features": [
            "Real-time crime zone proximity analysis",
            "Time-of-day crime pattern filtering",
            "AI-powered route safety classification", 
            "Dynamic route coloring based on actual risk",
            "Safety priority-based route filtering",
            "Intelligent safety message generation",
            "Enhanced crime data visualization",
            "Contextual safety recommendations"
        ],
        "safety_analysis": {
            "crime_classification": "3-tier severity system (High/Medium/Low)",
            "route_analysis": "Segment-by-segment crime exposure calculation",
            "color_coding": "Dynamic based on actual crime zone proximity",
            "safety_thresholds": "Configurable high/medium/low risk percentages"
        },
        "data_sources": [
            "Police incident reports",
            "Geographic crime clustering",
            "Time-based crime patterns",
            "Crime type severity classification"
        ],
        "accuracy": {
            "crime_detection": "Sub-kilometer precision",
            "route_analysis": "Per-segment risk assessment", 
            "safety_classification": "Multi-factor analysis",
            "time_filtering": "Hour-specific pattern matching"
        }
    }
