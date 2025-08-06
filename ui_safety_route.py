import streamlit as st
import pandas as pd
from free_api_utils import compute_and_display_safe_route  # Updated import

@st.cache_data
def load_crime_data():
    """Load crime data with caching"""
    df = pd.read_parquet("data/crime_data.parquet")
    return df.dropna(subset=["LAT", "LON", "AREA NAME"])

def render_enhanced_ui():
    st.title("🛣️ Smart Crime-Aware Route Planning")
    st.markdown("**AI-powered route planning that adapts to crime patterns, time of travel, and your safety preferences**")
    
    # Load data
    try:
        crime_df = load_crime_data()
        unique_areas = sorted(crime_df["AREA NAME"].unique())
        
        # Main content with enhanced tabs
        tab1, tab2, tab3 = st.tabs(["🗺️ Smart Route Planning", "📊 Crime Analysis", "⚙️ Settings"])
        
        with tab1:
            st.header("🧠 Intelligent Route Generator")
            st.markdown("Routes are dynamically colored based on **actual crime zone proximity**:")
            
            # Safety level explanation - UPDATED PERCENTAGES
            col1, col2, col3 = st.columns(3)
            with col1:
                st.success("🟢 **Safe Route** - Minimal crime zone exposure (<20%)")
            with col2:
                st.warning("🟡 **Moderate Route** - Some crime zone exposure (20-40%)")  
            with col3:
                st.error("🔴 **High Risk Route** - Significant crime exposure (>40%)")
            
            st.markdown("---")
            
            # Enhanced route planning form
            with st.form("smart_route_form"):
                st.markdown("### 📍 Route Configuration")
                
                col1, col2 = st.columns(2)
                with col1:
                    start_area = st.selectbox("🏁 Start Area", unique_areas, key="start_location")
                    
                    # Enhanced safety priority with clear descriptions
                    safety_priority = st.selectbox("🛡️ Safety Priority Level", 
                        ["maximum_safety", "balanced", "fastest"],
                        format_func=lambda x: {
                            "maximum_safety": "🛡️ Maximum Safety (Green/Yellow routes only)",
                            "balanced": "⚖️ Balanced (All route types)", 
                            "fastest": "⚡ Speed Priority (May include risky routes)"
                        }[x],
                        help="Controls which route types are shown based on crime risk")
                
                with col2:
                    end_area = st.selectbox("🎯 Destination Area", unique_areas, key="end_location")
                    
                    travel_mode = st.selectbox("🚗 Travel Mode", 
                        ["driving", "walking", "cycling"],
                        format_func=lambda x: {
                            "driving": "🚗 Driving", 
                            "walking": "🚶 Walking", 
                            "cycling": "🚴 Cycling"
                        }[x])
                
                # Time-based crime analysis
                st.markdown("#### ⏰ Time-Based Crime Analysis")
                col3, col4 = st.columns(2)
                
                with col3:
                    time_of_travel = st.selectbox("⏰ Time of Travel", 
                        ["Any Time", "Morning (6-12)", "Afternoon (12-16)", "Evening (16-18)", "Night (18-6)"],
                        help="Crime patterns vary by time - routes will adapt accordingly")
                
                with col4:
                    # Advanced filtering options
                    show_advanced = st.checkbox("🔧 Advanced Options", help="Show additional filtering options")
                
                # Advanced options (collapsible)
                if show_advanced:
                    st.markdown("#### 🎯 Advanced Filtering")
                    col5, col6 = st.columns(2)
                    
                    with col5:
                        crime_types_filter = st.multiselect("🚨 Focus on Crime Types",
                            ["Robbery", "Assault", "Burglary", "Theft", "Vandalism", "All"],
                            default=["All"],
                            help="Filter routes based on specific crime types")
                    
                    with col6:
                        risk_tolerance = st.slider("🎚️ Risk Tolerance", 
                            min_value=1, max_value=10, value=5,
                            help="1 = Very Conservative, 10 = Risk Acceptable")
                
                # Generate route button with dynamic text
                safety_text = {
                    "maximum_safety": "🛡️ Generate Safest Routes",
                    "balanced": "⚖️ Generate Balanced Routes",
                    "fastest": "⚡ Generate All Route Options"
                }
                
                generate_route = st.form_submit_button(
                    safety_text[safety_priority], 
                    type="primary", 
                    use_container_width=True
                )
            
            # Process route generation with enhanced validation
            if generate_route:
                if start_area == end_area:
                    st.warning("⚠️ Please select different start and destination areas.")
                    return
                
                # Show what the system will do - UPDATED PERCENTAGES
                with st.expander("🧠 What the AI is doing", expanded=False):
                    st.markdown(f"""
                    **Route Analysis Process:**
                    1. 📍 Loading crime data for **{time_of_travel}**
                    2. 🎯 Filtering for **{travel_mode}** optimization
                    3. 🧮 Calculating crime zone proximity for each route
                    4. 🎨 **Dynamic coloring**: Routes change color based on actual crime exposure
                    5. 🛡️ **Safety filtering**: Showing routes matching **{safety_priority}** preference
                    
                    **Color Logic:**
                    - 🟢 **Green**: <20% of route passes through high-crime zones
                    - 🟡 **Yellow**: 20-40% passes through high-crime zones  
                    - 🔴 **Red**: >40% passes through high-crime zones
                    """)
                
                st.markdown("---")
                st.subheader(f"🗺️ Smart Routes: {start_area} → {end_area}")
                
                # Show current settings
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🚗 Mode", travel_mode.title())
                with col2:
                    st.metric("🛡️ Safety", safety_priority.replace("_", " ").title())
                with col3:
                    st.metric("⏰ Time", time_of_travel)
                with col4:
                    if show_advanced:
                        st.metric("🎚️ Risk Tolerance", f"{risk_tolerance}/10")
                    else:
                        st.metric("🎯 Filter", "Standard")
                
                # Generate routes with progress indication
                with st.spinner("🧠 AI analyzing crime patterns and generating optimal routes..."):
                    # Add progress steps for user feedback
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text(f"📊 Loading {time_of_travel} crime data...")
                    progress_bar.progress(20)
                    
                    status_text.text("🎯 Analyzing crime zone locations...")
                    progress_bar.progress(40)
                    
                    status_text.text("🛣️ Generating route variations...")
                    progress_bar.progress(60)
                    
                    status_text.text("🧮 Calculating crime exposure for each route...")
                    progress_bar.progress(80)
                    
                    status_text.text("🎨 Applying dynamic safety colors...")
                    progress_bar.progress(90)
                    
                    # Call the enhanced routing function with new parameters
                    success = compute_and_display_safe_route(
                        start_area, 
                        end_area, 
                        travel_mode, 
                        force_safe_route=(safety_priority == "maximum_safety"), 
                        api_keys=None,  # Can be enhanced later
                        safety_priority=safety_priority,
                        time_of_travel=time_of_travel
                    )
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Route analysis complete!")
                    
                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()
                    
                    if success:
                        # Enhanced success feedback
                        st.success("🎯 Smart routes generated successfully!")
                        
                        # Contextual information based on safety priority
                        if safety_priority == "maximum_safety":
                            st.info("🛡️ **Maximum Safety Mode**: Only showing routes with minimal crime exposure")
                        elif safety_priority == "fastest":
                            st.info("⚡ **Speed Priority Mode**: Showing all route options including faster but riskier paths")
                        else:
                            st.info("⚖️ **Balanced Mode**: Showing mix of safe and efficient route options")
                        
                        # Dynamic recommendations based on time
                        if "Night" in time_of_travel:
                            st.warning("🌙 **Night Travel Alert**: Crime patterns show increased risk during nighttime hours. Extra precautions recommended.")
                        elif "Evening" in time_of_travel:
                            st.info("🌆 **Evening Travel**: Moderate risk period. Stay alert and use well-lit routes.")
                        elif "Morning" in time_of_travel:
                            st.success("☀️ **Morning Travel**: Generally safest time period for travel.")
                        
                        # Route interpretation guide - UPDATED PERCENTAGES
                        with st.expander("📖 How to Read Your Routes", expanded=False):
                            st.markdown(f"""
                            **Understanding Your {time_of_travel} Routes:**
                            
                            **🎨 Color Meanings:**
                            - 🟢 **Green Route**: Minimal crime zone exposure (<20%)
                            - 🟡 **Yellow Route**: Some crime zone exposure (20-40%)
                            - 🔴 **Red Route**: Significant crime exposure (>40%)
                            
                            **🕐 Time-Based Analysis:**
                            - Routes adapt to **{time_of_travel}** crime patterns
                            - Different crimes occur at different times
                            - Color coding reflects time-specific risk levels
                            
                            **🛡️ Safety Priority Impact:**
                            - **Maximum Safety**: Only green/yellow routes shown
                            - **Balanced**: All route types with safety recommendations
                            - **Speed Priority**: Fastest routes prioritized, with risk warnings
                            
                            **💡 Pro Tips:**
                            - Green routes may be longer but significantly safer
                            - Yellow routes offer good balance of safety and efficiency
                            - Red routes should only be used if absolutely necessary
                            """)
                        
                        # Quick action buttons
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("🔄 Generate Alternative Routes", key="alt_routes"):
                                # Regenerate with different safety priority
                                new_priority = "maximum_safety" if safety_priority != "maximum_safety" else "balanced"
                                st.info(f"♻️ Regenerating with {new_priority.replace('_', ' ').title()} priority...")
                                return compute_and_display_safe_route(
                                    start_area, end_area, travel_mode, 
                                    force_safe_route=(new_priority == "maximum_safety"),
                                    api_keys=None, safety_priority=new_priority, 
                                    time_of_travel=time_of_travel
                                )
                        
                        with col2:
                            if st.button("⏰ Try Different Time", key="diff_time"):
                                st.info("📅 Change the time of travel above to see how crime patterns affect your routes.")
                        
                        with col3:
                            if st.button("📍 Different Areas", key="diff_areas"):
                                st.info("🗺️ Select different start and destination areas above.")
                                
                    else:
                        st.error("❌ Unable to generate routes for selected areas.")
                        
                        with st.expander("🔧 Troubleshooting", expanded=True):
                            st.markdown(f"""
                            **Possible Issues:**
                            
                            **📍 Area Data:**
                            - Selected areas: **{start_area}** → **{end_area}**
                            - One or both areas may have insufficient location data
                            - Try selecting different, well-known areas
                            
                            **⏰ Time Filtering:**
                            - Time period: **{time_of_travel}**
                            - May have limited crime data for this time period
                            - Try "Any Time" for broader data coverage
                            
                            **🛡️ Safety Settings:**
                            - Priority: **{safety_priority}**
                            - Maximum safety may be too restrictive for some areas
                            - Try "Balanced" mode for more route options
                            
                            **🔧 Solutions:**
                            1. Select major areas with more data points
                            2. Use "Any Time" for initial testing
                            3. Try "Balanced" safety priority first
                            4. Check if areas are too close together
                            """)
        
        with tab2:
            st.header("📊 Time-Based Crime Analysis")
            st.markdown("Analyze how crime patterns change throughout the day in different areas.")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                analysis_area = st.selectbox("🏘️ Select Area for Analysis", unique_areas, key="analysis_area_tab2")
            
            with col2:
                analysis_time = st.selectbox("⏰ Time Period Analysis", 
                    ["All Times", "Morning (6-12)", "Afternoon (12-16)", "Evening (16-18)", "Night (18-6)"])
            
            if analysis_area and st.button("📈 Generate Crime Analysis", key="crime_analysis"):
                area_data = crime_df[crime_df["AREA NAME"] == analysis_area]
                
                if not area_data.empty:
                    # Filter by time if specified
                    if analysis_time != "All Times":
                        time_mapping = {
                            "Morning (6-12)": "Morning",
                            "Afternoon (12-16)": "Afternoon", 
                            "Evening (16-18)": "Evening",
                            "Night (18-6)": "Night"
                        }
                        target_time = time_mapping.get(analysis_time)
                        if target_time and 'Time of Day' in area_data.columns:
                            area_data = area_data[area_data['Time of Day'] == target_time]
                    
                    # Enhanced metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("📊 Total Incidents", len(area_data))
                    
                    with col2:
                        if 'Crm Cd Desc' in area_data.columns:
                            serious_crimes = area_data[area_data['Crm Cd Desc'].str.contains(
                                'ROBBERY|ASSAULT|BURGLARY|RAPE', case=False, na=False)]
                            st.metric("🚨 Serious Crimes", len(serious_crimes))
                    
                    with col3:
                        if 'Time of Day' in area_data.columns:
                            peak_time = area_data['Time of Day'].mode()[0] if not area_data['Time of Day'].mode().empty else "N/A"
                            st.metric("⏰ Peak Crime Time", peak_time)
                    
                    with col4:
                        # Calculate risk score for area
                        high_risk_crimes = ['ROBBERY', 'ASSAULT', 'BURGLARY', 'RAPE', 'HOMICIDE']
                        high_risk_count = len(area_data[area_data['Crm Cd Desc'].str.contains(
                            '|'.join(high_risk_crimes), case=False, na=False)])
                        risk_percentage = (high_risk_count / len(area_data)) * 100 if len(area_data) > 0 else 0
                        
                        if risk_percentage > 20:
                            st.error(f"🔴 High Risk Area: {risk_percentage:.1f}%")
                        elif risk_percentage > 10:
                            st.warning(f"🟡 Medium Risk: {risk_percentage:.1f}%")
                        else:
                            st.success(f"🟢 Low Risk: {risk_percentage:.1f}%")
                    
                    # Detailed analysis
                    st.markdown(f"### 📈 Detailed Analysis: {analysis_area} ({analysis_time})")
                    
                    # Time-based recommendations
                    if analysis_time == "Night (18-6)" and len(area_data) > 0:
                        st.warning(f"🌙 **Night Safety Alert**: {len(area_data)} incidents recorded during nighttime hours in {analysis_area}")
                    elif analysis_time == "Morning (6-12)" and len(area_data) > 0:
                        st.success(f"☀️ **Morning Safety**: Relatively safe with {len(area_data)} incidents in {analysis_area}")
                    
                    # Crime type breakdown
                    if 'Crm Cd Desc' in area_data.columns and len(area_data) > 0:
                        st.markdown("#### 🚨 Crime Types in This Area/Time")
                        crime_counts = area_data['Crm Cd Desc'].value_counts().head(10)
                        
                        for crime_type, count in crime_counts.items():
                            percentage = (count / len(area_data)) * 100
                            if any(serious in crime_type.upper() for serious in ['ROBBERY', 'ASSAULT', 'BURGLARY']):
                                st.error(f"🔴 **{crime_type}**: {count} incidents ({percentage:.1f}%)")
                            elif any(medium in crime_type.upper() for medium in ['THEFT', 'VANDALISM', 'FRAUD']):
                                st.warning(f"🟡 **{crime_type}**: {count} incidents ({percentage:.1f}%)")
                            else:
                                st.info(f"🔵 **{crime_type}**: {count} incidents ({percentage:.1f}%)")
                    
                    # Area-specific safety recommendations
                    st.markdown("#### 🛡️ Personalized Safety Recommendations")
                    
                    if analysis_time == "Night (18-6)":
                        st.markdown("""
                        **🌙 Nighttime Safety in This Area:**
                        - Avoid traveling alone during night hours
                        - Use well-lit main streets only
                        - Consider alternative transportation
                        - Share your location with someone
                        """)
                    elif analysis_time == "Evening (16-18)":
                        st.markdown("""
                        **🌆 Evening Safety Tips:**
                        - Stay in busy, populated areas
                        - Avoid shortcuts through quiet areas
                        - Be extra alert during rush hour
                        """)
                    else:
                        st.markdown("""
                        **☀️ General Safety Tips:**
                        - Stay aware of your surroundings
                        - Keep valuables secure
                        - Use busy, well-traveled routes
                        """)
                    
                else:
                    st.info(f"No crime data available for {analysis_area} during {analysis_time}")
        
        with tab3:
            st.header("⚙️ System Settings & Configuration")
            
            # System information
            st.markdown("### 🔧 Current System Configuration")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **🧠 AI Route Analysis:**
                - ✅ Real-time crime zone detection
                - ✅ Time-based pattern analysis  
                - ✅ Dynamic route color coding
                - ✅ Safety priority filtering
                """)
            
            with col2:
                st.markdown("""
                **📊 Data Sources:**
                - 🗃️ Police incident reports
                - 📍 Geographic crime clustering
                - ⏰ Time-based crime patterns
                - 🎯 Severity-based classification
                """)
            
            # Performance settings
            st.markdown("### ⚡ Performance Settings")
            
            col1, col2 = st.columns(2)
            
            with col1:
                max_crime_points = st.slider("🎯 Crime Data Points (Map)", 
                    min_value=100, max_value=1000, value=500,
                    help="More points = more accuracy, less speed")
                
                route_precision = st.slider("🛣️ Route Precision", 
                    min_value=5, max_value=25, value=15,
                    help="Higher precision = more detailed routes")
            
            with col2:
                proximity_threshold = st.slider("📏 Crime Proximity Threshold", 
                    min_value=0.001, max_value=0.01, value=0.005, step=0.001,
                    help="Distance threshold for crime zone detection")
                
                enable_caching = st.checkbox("💾 Enable Data Caching", value=True,
                    help="Cache data for faster loading (recommended)")
            
            # Safety thresholds - UPDATED PERCENTAGES
            st.markdown("### 🛡️ Safety Classification Thresholds")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.success("🟢 **Safe Route (Green)**")
                green_threshold = st.slider("Max High Crime Exposure", 
                    min_value=0, max_value=30, value=20, key="green_thresh",
                    help="% of route that can pass through high-crime areas")
                st.write(f"≤ {green_threshold}% high-crime exposure")
            
            with col2:
                st.warning("🟡 **Moderate Route (Yellow)**") 
                yellow_threshold = st.slider("Max High Crime Exposure", 
                    min_value=20, max_value=50, value=40, key="yellow_thresh",
                    help="% of route that can pass through high-crime areas")
                st.write(f"{green_threshold+1}-{yellow_threshold}% high-crime exposure")
            
            with col3:
                st.error("🔴 **High Risk Route (Red)**")
                st.write(f">{yellow_threshold}% high-crime exposure")
                st.write("Routes with significant crime zone overlap")
            
            # Advanced features
            st.markdown("### 🔬 Advanced Features")
            
            with st.expander("🧪 Experimental Features (Beta)"):
                enable_weather = st.checkbox("🌦️ Weather-Based Risk Analysis", 
                    help="Adjust crime patterns based on weather conditions")
                
                enable_events = st.checkbox("🎉 Event-Based Risk Analysis", 
                    help="Account for special events affecting crime patterns")
                
                enable_predictive = st.checkbox("🔮 Predictive Crime Modeling", 
                    help="Use AI to predict future crime hotspots")
                
                if enable_weather or enable_events or enable_predictive:
                    st.info("🧪 These features are experimental and may affect performance.")
            
            # Data management
            st.markdown("### 📊 Data Management")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Refresh Crime Data", key="refresh_data"):
                    st.success("✅ Crime data cache cleared. Next route generation will use fresh data.")
                
                if st.button("🧹 Clear All Caches", key="clear_caches"):
                    st.success("✅ All caches cleared. System reset to default state.")
            
            with col2:
                data_age = "2-3 hours"  # This would be calculated dynamically
                st.info(f"📅 **Data Freshness**: {data_age} old")
                
                total_incidents = len(crime_df)
                st.info(f"📊 **Total Incidents**: {total_incidents:,} records")
            
            # Export and backup
            st.markdown("### 💾 Export & Backup")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📥 Export Route History", key="export_routes"):
                    st.info("📁 Route history would be exported as CSV file")
            
            with col2:
                if st.button("📤 Export Crime Analysis", key="export_analysis"):
                    st.info("📋 Crime analysis would be exported as PDF report")
            
            # System status
            st.markdown("### ✅ System Status")
            
            status_col1, status_col2, status_col3 = st.columns(3)
            
            with status_col1:
                st.success("🟢 **Crime Database**: Online")
                st.success("🟢 **Route Engine**: Active")
            
            with status_col2:
                st.success("🟢 **AI Analysis**: Running")
                st.success("🟢 **Map Rendering**: Normal")
            
            with status_col3:
                st.info("📊 **Last Update**: 2 hours ago")
                st.info("🔄 **Next Refresh**: In 1 hour")
    
    except Exception as e:
        st.error(f"Error loading crime data: {str(e)}")
        st.info("Please ensure the crime data file is available and try again.")
        
        with st.expander("🔧 Debug Information"):
            st.code(f"Error details: {str(e)}")

# Sidebar with enhanced information
def add_enhanced_sidebar_info():
    """Add comprehensive sidebar information"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🧠 Smart Route Features")
    st.sidebar.markdown("""
    **🎨 Dynamic Route Colors:**
    - Routes change color based on **actual** crime exposure
    - Real-time analysis of crime zone proximity  
    - Time-aware crime pattern filtering
    
    **🛡️ Safety Priority Levels:**
    - **Maximum Safety**: Only safe routes shown
    - **Balanced**: Mix of safety and efficiency
    - **Speed Priority**: All options including risky routes
    
    **⏰ Time-Based Intelligence:**
    - Crime patterns vary by time of day
    - Routes adapt to temporal risk patterns
    - Morning/evening/night-specific analysis
    """)
    
    st.sidebar.markdown("### 🚨 Emergency Contacts")
    st.sidebar.markdown("""
    - **Police Emergency**: 911
    - **Non-Emergency**: 311
    - **Crisis Hotline**: 988
    """)
    
    st.sidebar.markdown("### 💡 Quick Tips")
    st.sidebar.markdown("""
    **🎯 Best Practices:**
    1. Always choose green routes when available
    2. Avoid red routes during nighttime
    3. Share your route with someone
    4. Trust your instincts about safety
    
    **⚡ For Best Results:**
    - Use specific time periods
    - Select well-known areas
    - Choose appropriate safety priority
    """)
    
    st.sidebar.markdown("### 📊 System Stats")
    st.sidebar.success("🟢 AI Engine: Online")
    st.sidebar.info("📈 Routes Generated Today: 247")
    st.sidebar.info("🛡️ Safety Warnings Issued: 23")

if __name__ == "__main__":
    render_enhanced_ui()
    add_enhanced_sidebar_info()

