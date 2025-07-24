import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ✅ Set page config
st.set_page_config(
    page_title="🛡️ Crime Safety Travel Assistant", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ✅ Import modules with error handling
try:
    from forecast import run_forecast
except ImportError:
    def run_forecast():
        st.error("Forecast module not available")

try:
    from clustering import run_clustering_ui
except ImportError:
    def run_clustering_ui():
        st.error("Clustering module not available")

# Import enhanced crime alerts system with official LAPD data
try:
    from crime_alerts import add_crime_alert_integration, show_crime_alerts_sidebar, run_crime_alerts_page
    ALERTS_AVAILABLE = True
except ImportError:
    def add_crime_alert_integration():
        pass
    def show_crime_alerts_sidebar():
        return 0
    def run_crime_alerts_page():
        st.error("Crime alerts system not available. Please ensure crime_alerts.py is in the project directory.")
    ALERTS_AVAILABLE = False

try:
    # Import the ENHANCED system with dynamic safety analysis
    from free_api_utils import compute_and_display_safe_route as enhanced_route
    
    def run_safe_route_mapping():
        """Enhanced Safe Route Mapping with Dynamic Crime-Aware Analysis"""
        st.markdown("### 🗺️ Smart Crime-Aware Route Planning")
        st.markdown("**AI-powered routing that adapts to real crime patterns and time-of-day risk levels.**")
        

        
        # Load area data
        @st.cache_data
        def load_area_data():
            import pandas as pd
            try:
                df = pd.read_parquet("data/crime_data.parquet")
                return sorted(df['AREA NAME'].dropna().unique())
            except Exception as e:
                st.error(f"Error loading area data: {e}")
                return []
        
        unique_areas = load_area_data()
        
        if not unique_areas:
            st.error("❌ No area data available. Please ensure data/crime_data.parquet exists.")
            return
        
        # Enhanced route planning form with new features
        with st.form("enhanced_safe_route_mapping_form"):
            st.markdown("### 📍 Smart Route Configuration")
            
            col1, col2 = st.columns(2)
            
            with col1:
                start_area = st.selectbox("🏁 Start Area", unique_areas,
                    help="Select your starting location")
                travel_mode = st.selectbox("🚗 Travel Mode", 
                    ["driving", "walking", "cycling"],
                    format_func=lambda x: {"driving": "🚗 Driving", "walking": "🚶 Walking", "cycling": "🚴 Cycling"}[x],
                    help="Routes will be optimized for your selected travel mode")
            
            with col2:
                end_area = st.selectbox("🎯 Destination Area", unique_areas,
                    help="Select your destination")
                
                # ENHANCED: New safety priority with clear descriptions
                safety_priority = st.selectbox("🛡️ Safety Priority Level", 
                    ["balanced", "maximum_safety", "speed_priority"],
                    format_func=lambda x: {
                        "balanced": "⚖️ Balanced (All route types)", 
                        "maximum_safety": "🛡️ Maximum Safety (Green/Yellow only)", 
                        "speed_priority": "⚡ Speed Priority (May include risky routes)"
                    }[x],
                    help="Controls which route types are shown based on actual crime risk analysis")
            
            # ENHANCED: New time-based crime analysis
            st.markdown("#### ⏰ Time-Based Crime Analysis")
            col3, col4 = st.columns(2)
            
            with col3:
                # ENHANCED: More specific time periods
                time_of_travel = st.selectbox("⏰ Time of Travel", 
                    ["Any Time", "Morning (6-12)", "Afternoon (12-16)", "Evening (16-18)", "Night (18-6)"],
                    help="🆕 Crime patterns vary by time - routes will adapt accordingly")
                
                show_crime_overlay = st.checkbox("🔍 Show Crime Risk Zones", value=True,
                    help="Display crime hotspots with accurate severity colors on the map")
            
            with col4:
                # Advanced filtering options
                gender_profile = st.selectbox("👤 Traveler Profile", 
                    ["Any", "Male", "Female"], 
                    help="Crime patterns may vary by gender demographics")
                
                avoid_high_crime = st.checkbox("🚫 Strictly Avoid High Crime Areas", value=True,
                    help="🆕 Prioritize routes that completely avoid known high-crime zones")
            
            # ENHANCED: Dynamic button text based on safety priority
            safety_button_text = {
                "maximum_safety": "🛡️ Generate Safest Routes Only",
                "balanced": "⚖️ Generate Balanced Route Options", 
                "speed_priority": "⚡ Generate All Route Options (Including Risky)"
            }
            
            generate_route = st.form_submit_button(
                safety_button_text[safety_priority], 
                type="primary", 
                use_container_width=True
            )
        
        # Process route generation with enhanced features
        if generate_route:
            if start_area == end_area:
                st.warning("⚠️ Please select different start and destination areas.")
            else:
                # Show what the enhanced system will do
                st.markdown("---")
                st.subheader(f"🧠 Smart Routes: {start_area} → {end_area}")
                
                # Show current enhanced settings
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🚗 Travel Mode", travel_mode.title())
                with col2:
                    safety_display = safety_priority.replace("_", " ").title()
                    st.metric("🛡️ Safety Level", safety_display)
                with col3:
                    st.metric("⏰ Time Period", time_of_travel)
                with col4:
                    profile_display = "Standard" if gender_profile == "Any" else gender_profile
                    st.metric("👤 Profile", profile_display)
                
                with st.spinner("🧠 Enhanced AI analyzing crime patterns and generating intelligent routes..."):
                    # Add progress feedback
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text(f"📊 Loading {time_of_travel} crime data...")
                    progress_bar.progress(20)
                    
                    status_text.text("🎯 Analyzing crime severity and locations...")
                    progress_bar.progress(40)
                    
                    status_text.text("🛣️ Generating route variations...")
                    progress_bar.progress(60)
                    
                    status_text.text("🧮 Calculating crime zone proximity for each route...")
                    progress_bar.progress(80)
                    
                    status_text.text("🎨 Applying dynamic safety colors...")
                    progress_bar.progress(90)
                    
                    # ENHANCED: Call enhanced routing with all new parameters
                    force_safe = (safety_priority == "maximum_safety")
                    success = enhanced_route(
                        start_area, 
                        end_area, 
                        travel_mode, 
                        force_safe, 
                        api_keys=None,
                        safety_priority=safety_priority,
                        time_of_travel=time_of_travel
                    )
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Enhanced route analysis complete!")
                    
                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()
                    
                    if success:
                        # Enhanced success feedback with contextual information
                        st.success("🎯 Smart routes generated with enhanced crime analysis!")
                        
                        # Provide contextual feedback based on settings
                        if safety_priority == "maximum_safety":
                            st.info("🛡️ **Maximum Safety Mode**: Only showing routes with minimal crime zone exposure")
                        elif safety_priority == "speed_priority":
                            st.warning("⚡ **Speed Priority Mode**: Showing fastest routes - some may pass through crime areas")
                        else:
                            st.info("⚖️ **Balanced Mode**: Showing optimal mix of safe and efficient route options")
                        
                        # Time-specific contextual advice
                        if "Night" in time_of_travel:
                            st.warning("🌙 **Night Travel Alert**: Crime rates are higher at night. Extra precautions strongly recommended.")
                        elif "Evening" in time_of_travel:
                            st.info("🌆 **Evening Travel**: Moderate risk period. Stay alert and use well-lit routes.")
                        elif "Morning" in time_of_travel:
                            st.success("☀️ **Morning Travel**: Generally safest time period for travel.")
                        
                        # Enhanced action buttons
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("🔄 Try Different Safety Level", key="change_safety"):
                                new_safety = "maximum_safety" if safety_priority != "maximum_safety" else "balanced"
                                st.info(f"💡 Try changing Safety Priority to '{new_safety.replace('_', ' ').title()}' above for different route options.")
                        
                        with col2:
                            if st.button("⏰ Analyze Different Time", key="change_time"):
                                st.info("📅 Try different times above to see how crime patterns affect your routes throughout the day.")
                        
                        with col3:
                            if st.button("📍 Different Route", key="change_route"):
                                st.info("🗺️ Select different start/destination areas above to explore other routes.")
                    
                    else:
                        st.error("❌ Unable to generate routes for selected criteria.")
                        
                        # Enhanced troubleshooting with specific guidance
                        with st.expander("🔧 Enhanced Troubleshooting", expanded=True):
                            st.markdown(f"""
                            **🔍 Diagnosis for Your Settings:**
                            
                            **📍 Selected Route:** {start_area} → {end_area}
                            **⏰ Time Period:** {time_of_travel}
                            **🛡️ Safety Priority:** {safety_priority.replace('_', ' ').title()}
                            **🚗 Travel Mode:** {travel_mode.title()}
                            
                            **🚨 Possible Issues:**
                            
                            1. **⏰ Time Filtering Too Restrictive:**
                               - {time_of_travel} may have limited crime data
                               - **Solution:** Try "Any Time" for broader coverage
                            
                            2. **🛡️ Safety Priority Too Strict:**
                               - Maximum Safety mode may be too restrictive for this area
                               - **Solution:** Try "Balanced" mode first
                            
                            3. **📍 Area Data Insufficient:**
                               - Selected areas may have limited location data
                               - **Solution:** Try well-known, major areas
                            
                            4. **🚫 No Safe Routes Available:**
                               - Area combination may not have safe route options
                               - **Solution:** Consider different areas or travel times
                            
                            **✅ Recommended Actions:**
                            - Set Safety Priority to "Balanced"
                            - Use "Any Time" initially
                            - Select major metropolitan areas
                            - Try different travel modes
                            """)
    
    # Enhanced Area Analysis with better integration
    def run_area_analysis():
        """Enhanced Area Analysis with improved crime pattern visualization"""
        st.markdown("### 📊 Enhanced Crime Analysis by Area")
        st.markdown("**Analyze time-based crime patterns and get area-specific safety recommendations.**")
        
        # Load area data with enhanced processing
        @st.cache_data
        def load_enhanced_crime_data_for_analysis():
            try:
                df = pd.read_parquet("data/crime_data.parquet")
                df = df.dropna(subset=["LAT", "LON", "AREA NAME"])
                
                # Enhanced time processing
                if 'Time of Day' not in df.columns and 'TIME OCC' in df.columns:
                    df['TIME OCC'] = pd.to_numeric(df['TIME OCC'], errors='coerce')
                    df['Hour'] = (df['TIME OCC'] // 100).fillna(12).astype(int)
                    
                    # Enhanced time categorization matching route system
                    def enhanced_categorize_time(hour):
                        if 6 <= hour < 12:
                            return "Morning"
                        elif 12 <= hour < 16:
                            return "Afternoon"
                        elif 16 <= hour < 18:
                            return "Evening"
                        else:  # 18-6 (night)
                            return "Night"
                    
                    df['Time of Day'] = df['Hour'].apply(enhanced_categorize_time)
                
                # Enhanced crime severity classification (matching route system)
                def classify_enhanced_crime_severity(row):
                    crime_desc = str(row.get('Crm Cd Desc', '')).upper()
                    
                    # High severity crimes (Red level)
                    high_severity = ['ROBBERY', 'ASSAULT', 'BURGLARY', 'RAPE', 'HOMICIDE', 'MURDER',
                                   'KIDNAPPING', 'ARSON', 'SHOTS FIRED', 'CRIMINAL THREATS', 'BATTERY']
                    
                    if any(crime in crime_desc for crime in high_severity):
                        return 'High Risk'
                    
                    # Medium severity crimes (Yellow level) 
                    medium_severity = ['THEFT', 'VANDALISM', 'FRAUD', 'SHOPLIFTING', 'VEHICLE',
                                     'STOLEN', 'TRESPASSING', 'PICKPOCKET']
                    
                    if any(crime in crime_desc for crime in medium_severity):
                        return 'Medium Risk'
                    
                    return 'Low Risk'
                
                df['Risk Level'] = df.apply(classify_enhanced_crime_severity, axis=1)
                
                return df
            except Exception as e:
                st.error(f"Error loading enhanced crime data: {e}")
                return None
        
        crime_df = load_enhanced_crime_data_for_analysis()
        
        if crime_df is None:
            st.error("Could not load crime data for enhanced analysis.")
            return
        
        unique_areas = sorted(crime_df["AREA NAME"].unique())
        
        # Enhanced selection interface
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            selected_area = st.selectbox("🏘️ Select Area for Enhanced Analysis", unique_areas, key="enhanced_analysis_area")
        
        with col2:
            # Time-based analysis matching route system
            time_filter = st.selectbox("⏰ Time Period Analysis", 
                ["All Times", "Morning (6-12)", "Afternoon (12-16)", "Evening (16-18)", "Night (18-6)"])
        
        with col3:
            # Risk level filter
            risk_filter = st.selectbox("🚨 Risk Level Filter",
                ["All Risks", "High Risk", "Medium Risk", "Low Risk"])
        
        if selected_area:
            # Filter data for selected area and criteria
            area_data = crime_df[crime_df["AREA NAME"] == selected_area].copy()
            
            # Apply time filter
            if time_filter != "All Times":
                time_mapping = {
                    "Morning (6-12)": "Morning",
                    "Afternoon (12-16)": "Afternoon", 
                    "Evening (16-18)": "Evening",
                    "Night (18-6)": "Night"
                }
                target_time = time_mapping.get(time_filter)
                if target_time and 'Time of Day' in area_data.columns:
                    area_data = area_data[area_data['Time of Day'] == target_time]
            
            # Apply risk filter
            if risk_filter != "All Risks" and 'Risk Level' in area_data.columns:
                area_data = area_data[area_data['Risk Level'] == risk_filter]
            
            if not area_data.empty:
                # Enhanced metrics with risk-aware analysis
                st.markdown(f"#### 📊 Enhanced Analysis: {selected_area}")
                if time_filter != "All Times":
                    st.markdown(f"**Time Period:** {time_filter}")
                if risk_filter != "All Risks":
                    st.markdown(f"**Risk Level:** {risk_filter}")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_incidents = len(area_data)
                    st.markdown(f"""
                    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 4px solid #1f77b4;">
                        <div style="color: #262730; font-size: 14px; font-weight: 600; margin-bottom: 4px;">
                            📊 Total Incidents
                        </div>
                        <div style="color: #262730; font-size: 18px; font-weight: 700; line-height: 1.2;">
                            {total_incidents:,}
                        </div>
                        <div style="color: #666; font-size: 11px;">
                            {time_filter} • {risk_filter}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # Enhanced risk distribution
                    if 'Risk Level' in area_data.columns:
                        risk_counts = area_data['Risk Level'].value_counts()
                        high_risk_pct = (risk_counts.get('High Risk', 0) / len(area_data) * 100) if len(area_data) > 0 else 0
                        
                        risk_color = "#ff4b4b" if high_risk_pct > 25 else "#ffa500" if high_risk_pct > 10 else "#00cc44"
                        risk_level_text = "High" if high_risk_pct > 25 else "Medium" if high_risk_pct > 10 else "Low"
                        
                        st.markdown(f"""
                        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 4px solid {risk_color};">
                            <div style="color: #262730; font-size: 14px; font-weight: 600; margin-bottom: 4px;">
                                🚨 Area Risk Level
                            </div>
                            <div style="color: #262730; font-size: 18px; font-weight: 700; line-height: 1.2;">
                                {risk_level_text}
                            </div>
                            <div style="color: #666; font-size: 11px;">
                                {high_risk_pct:.1f}% High Risk Crimes
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                with col3:
                    # Enhanced time analysis
                    if 'Time of Day' in area_data.columns:
                        peak_time = area_data['Time of Day'].mode()[0] if not area_data['Time of Day'].mode().empty else "N/A"
                        
                        time_color = "#ff4b4b" if peak_time == "Night" else "#ffa500" if peak_time == "Evening" else "#00cc44"
                        
                        st.markdown(f"""
                        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 4px solid {time_color};">
                            <div style="color: #262730; font-size: 14px; font-weight: 600; margin-bottom: 4px;">
                                ⏰ Peak Crime Time
                            </div>
                            <div style="color: #262730; font-size: 18px; font-weight: 700; line-height: 1.2;">
                                {peak_time}
                            </div>
                            <div style="color: #666; font-size: 11px;">
                                Most incidents occur
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                with col4:
                    # Enhanced route recommendation
                    if 'Risk Level' in area_data.columns and 'Time of Day' in area_data.columns:
                        high_risk_count = len(area_data[area_data['Risk Level'] == 'High Risk'])
                        night_crimes = len(area_data[area_data['Time of Day'] == 'Night'])
                        
                        if high_risk_count > len(area_data) * 0.3 or night_crimes > len(area_data) * 0.4:
                            route_rec = "Avoid"
                            rec_color = "#ff4b4b"
                        elif high_risk_count > len(area_data) * 0.15:
                            route_rec = "Caution"
                            rec_color = "#ffa500"
                        else:
                            route_rec = "Safe"
                            rec_color = "#00cc44"
                        
                        st.markdown(f"""
                        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 4px solid {rec_color};">
                            <div style="color: #262730; font-size: 14px; font-weight: 600; margin-bottom: 4px;">
                                🛣️ Route Recommendation
                            </div>
                            <div style="color: #262730; font-size: 18px; font-weight: 700; line-height: 1.2;">
                                {route_rec}
                            </div>
                            <div style="color: #666; font-size: 11px;">
                                For route planning
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Continue with existing detailed analysis...
                # (Keep all your existing analysis code from here)
                
                # Enhanced detailed analysis
                if st.button("📈 Show Enhanced Detailed Analysis", key="enhanced_detailed_analysis"):
                    st.markdown("---")
                    st.subheader(f"🔍 Enhanced Analysis: {selected_area}")
                    
                    # Enhanced risk breakdown
                    if 'Risk Level' in area_data.columns:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### 🚨 Crime Risk Distribution")
                            risk_dist = area_data['Risk Level'].value_counts()
                            
                            # Create enhanced risk chart
                            risk_colors = {'High Risk': '#ff4b4b', 'Medium Risk': '#ffa500', 'Low Risk': '#00cc44'}
                            fig_risk = go.Figure(data=[
                                go.Bar(
                                    x=risk_dist.index,
                                    y=risk_dist.values,
                                    marker_color=[risk_colors.get(risk, '#cccccc') for risk in risk_dist.index],
                                    text=[f"{count}<br>({count/len(area_data)*100:.1f}%)" for count in risk_dist.values],
                                    textposition='auto'
                                )
                            ])
                            
                            fig_risk.update_layout(
                                title=f"Crime Risk Levels in {selected_area}",
                                xaxis_title="Risk Level",
                                yaxis_title="Number of Incidents",
                                showlegend=False,
                                height=400
                            )
                            
                            st.plotly_chart(fig_risk, use_container_width=True)
                        
                        with col2:
                            st.markdown("#### ⏰ Time vs Risk Analysis")
                            if 'Time of Day' in area_data.columns:
                                time_risk_crosstab = pd.crosstab(area_data['Time of Day'], area_data['Risk Level'])
                                
                                fig_time_risk = px.imshow(
                                    time_risk_crosstab.values,
                                    x=time_risk_crosstab.columns,
                                    y=time_risk_crosstab.index,
                                    aspect='auto',
                                    color_continuous_scale='Reds',
                                    title=f"Crime Risk by Time Period"
                                )
                                
                                fig_time_risk.update_layout(height=400)
                                st.plotly_chart(fig_time_risk, use_container_width=True)
                    
                    # Enhanced safety recommendations based on analysis
                    st.markdown("#### 🛡️ Enhanced Safety Recommendations")
                    
                    if 'Risk Level' in area_data.columns and 'Time of Day' in area_data.columns:
                        high_risk_times = area_data[area_data['Risk Level'] == 'High Risk']['Time of Day'].value_counts()
                        
                        if len(high_risk_times) > 0:
                            worst_time = high_risk_times.index[0]
                            worst_count = high_risk_times.iloc[0]
                            
                            if worst_time == "Night":
                                st.error(f"""
                                🌙 **HIGH RISK - NIGHT TRAVEL**
                                - {worst_count} high-risk incidents during night hours
                                - **Recommendation**: Avoid this area at night completely
                                - If travel necessary, use only green routes from route planner
                                - Consider alternative areas or daytime travel
                                """)
                            elif worst_time == "Evening":
                                st.warning(f"""
                                🌆 **MODERATE RISK - EVENING TRAVEL**
                                - {worst_count} high-risk incidents during evening hours  
                                - **Recommendation**: Use caution during evening travel
                                - Prefer yellow or green routes from route planner
                                - Complete travel before full darkness
                                """)
                            else:
                                st.info(f"""
                                ☀️ **DAYTIME RISK PRESENT**
                                - {worst_count} high-risk incidents during {worst_time}
                                - **Recommendation**: Standard safety precautions
                                - Use route planner for safest paths
                                - Stay alert during {worst_time} hours
                                """)
                    
                    # Integration with route planning
                    st.markdown("#### 🗺️ Route Planning Integration")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"🛣️ Plan Safe Routes FROM {selected_area}", key="plan_from"):
                            st.session_state.route_start = selected_area
                            st.success(f"✅ Set {selected_area} as starting point. Go to Route Planning tab to select destination.")
                    
                    with col2:
                        if st.button(f"🎯 Plan Safe Routes TO {selected_area}", key="plan_to"):
                            st.session_state.route_end = selected_area
                            st.success(f"✅ Set {selected_area} as destination. Go to Route Planning tab to select starting point.")
            
            else:
                st.info(f"No data available for {selected_area} with current filters.")
                st.markdown("**Try adjusting the filters above or selecting a different area.**")
    
    ENHANCED_AVAILABLE = True
    
except ImportError:
    # Fallback to existing system  
    try:
        from free_api_utils import compute_and_display_safe_route as enhanced_route
        
        def run_safe_route_mapping():
            """Fallback Safe Route Mapping"""
            st.markdown("### 🗺️ Safe Route Mapping")
            st.markdown("Plan your routes with crime analysis and visualization.")
            
            # Load area data
            @st.cache_data
            def load_area_data():
                import pandas as pd
                try:
                    df = pd.read_parquet("data/crime_data.parquet")
                    return sorted(df['AREA NAME'].dropna().unique())
                except Exception as e:
                    st.error(f"Error loading area data: {e}")
                    return []
            
            unique_areas = load_area_data()
            
            if not unique_areas:
                st.error("❌ No area data available. Please ensure data/crime_data.parquet exists.")
                return
            
            # Basic route planning form
            with st.form("basic_safe_route_mapping_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    start_area = st.selectbox("🏁 Start Area", unique_areas)
                    travel_mode = st.selectbox("🚗 Travel Mode", 
                        ["driving", "walking", "cycling"],
                        format_func=lambda x: {"driving": "🚗 Driving", "walking": "🚶 Walking", "cycling": "🚴 Cycling"}[x])
                
                with col2:
                    end_area = st.selectbox("🎯 Destination Area", unique_areas)
                    safety_priority = st.selectbox("🛡️ Safety Priority", 
                        ["balanced", "maximum_safety", "speed_priority"],
                        format_func=lambda x: {"balanced": "⚖️ Balanced", "maximum_safety": "🛡️ Maximum Safety", "speed_priority": "⚡ Speed Priority"}[x])
                
                generate_route = st.form_submit_button("🚀 Generate Safe Routes", type="primary")
            
            if generate_route:
                if start_area == end_area:
                    st.warning("⚠️ Please select different start and destination areas.")
                else:
                    with st.spinner("🔍 Analyzing crime patterns and generating routes..."):
                        force_safe = (safety_priority == "maximum_safety")
                        success = enhanced_route(start_area, end_area, travel_mode, force_safe)
                        
                        if not success:
                            st.error("❌ Unable to generate routes. Please try different areas.")
        
        # Keep existing area analysis
        def run_area_analysis():
            """Keep your existing area analysis code here"""
            st.markdown("### 📊 Crime Analysis by Area")
            
            # [Insert all your existing area analysis code from the original app.py]
            # ... (all the existing code for area analysis)
        
        ENHANCED_AVAILABLE = False
        
    except ImportError:
        def run_safe_route_mapping():
            st.error("Safe route mapping not available")
        
        def run_area_analysis():
            st.error("Area analysis not available")
        
        ENHANCED_AVAILABLE = False

# ✅ Initialize session state for page navigation
if "page" not in st.session_state:
    st.session_state.page = "clustering"

# Initialize route planning session state
if "route_start" not in st.session_state:
    st.session_state.route_start = None
if "route_end" not in st.session_state:
    st.session_state.route_end = None

# ✅ Main UI Header
st.title("🛡️ Crime Safety Travel Assistant")
if ENHANCED_AVAILABLE:
    st.markdown("*🆕 Enhanced with AI-powered dynamic crime-aware routing*")
else:
    st.markdown("*AI-powered crime analysis with intelligent route planning*")

# ✅ Add crime alert integration with official LAPD data
if ALERTS_AVAILABLE:
    add_crime_alert_integration()

# ✅ Handle page routing from clustering page
def handle_page_routing():
    """Handle navigation between pages"""
    if st.session_state.page == "safe_route":
        st.sidebar.success("🎯 Navigated from Crime Hotspot Analysis")
        
        try:
            run_safe_route_mapping()
        except Exception as e:
            st.error(f"Error loading safe route interface: {str(e)}")
        
        if st.sidebar.button("⬅️ Back to Crime Hotspots"):
            st.session_state.page = "clustering"
            st.rerun()
        return True
    return False

# ✅ Check if we're in a routed page
if handle_page_routing():
    pass
else:
    # ✅ Normal sidebar navigation
    menu_options = [
        "🧭 Crime Hotspot Clustering",
        "🗺️ Safe Route Mapping", 
        "📊 Crime Forecasting"
    ]
    
    # Add crime alerts option if available
    if ALERTS_AVAILABLE:
        menu_options.append("🚨 Crime Alerts")
    
    menu = st.sidebar.radio(
        "🧭 Choose Feature",
        menu_options,
        help="Select the feature you want to use"
    )

    # ✅ Reset page state when using normal navigation
    if menu == "🧭 Crime Hotspot Clustering":
        st.session_state.page = "clustering"

    # ✅ Menu logic
    try:
        if menu == "🧭 Crime Hotspot Clustering":
            st.markdown("### 🧭 Crime Hotspot Analysis")
            st.markdown("Analyze crime patterns and identify high-risk areas using machine learning clustering.")
            run_clustering_ui()

        elif menu == "🗺️ Safe Route Mapping":
            # Enhanced tabs for route mapping and area analysis
            if ENHANCED_AVAILABLE:
                tab1, tab2 = st.tabs(["🗺️ Smart Route Planning", "📊 Enhanced Area Analysis"])
            else:
                tab1, tab2 = st.tabs(["🗺️ Route Planning", "📊 Area Analysis"])
            
            with tab1:
                # Pre-populate route form if coming from area analysis
                if st.session_state.route_start or st.session_state.route_end:
                    if st.session_state.route_start and st.session_state.route_end:
                        st.success(f"🎯 Route: {st.session_state.route_start} → {st.session_state.route_end}")
                    elif st.session_state.route_start:
                        st.info(f"📍 Starting from: {st.session_state.route_start}")
                    elif st.session_state.route_end:
                        st.info(f"🎯 Going to: {st.session_state.route_end}")
                    
                    if st.button("🔄 Clear Route Selection"):
                        st.session_state.route_start = None
                        st.session_state.route_end = None
                        st.rerun()
                
                run_safe_route_mapping()
            
            with tab2:
                run_area_analysis()

        elif menu == "📊 Crime Forecasting":
            st.markdown("### 📊 Crime Forecasting")
            st.markdown("Predict future crime trends using advanced AI forecasting models.")
            run_forecast()
        
        elif menu == "🚨 Crime Alerts" and ALERTS_AVAILABLE:
            run_crime_alerts_page()

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        
        with st.expander("🔧 Troubleshooting"):
            st.markdown("""
            **Common Solutions:**
            
            1. **Refresh the page** - Fixes most temporary issues
            2. **Check data files** - Ensure all required data files are in data/ folder
            3. **Try different areas** - Some may have limited data
            4. **Check dependencies** - Ensure required packages are installed
            5. **LAPD Data** - Ensure LAPD_Police_Stations CSV is in data/ folder
            6. **Enhanced Features** - Install enhanced modules for full functionality
            """)

# ✅ Enhanced Sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ System Features")

if ENHANCED_AVAILABLE:
    st.sidebar.success("""
    **🆕 Enhanced Smart Routing** ✅
    
    ✅ Dynamic crime-aware route colors
    ✅ Time-based crime pattern analysis
    ✅ Safety priority filtering
    ✅ Intelligent route recommendations
    ✅ Real-time crime zone detection
    ✅ Enhanced safety messaging
    """)
    
    st.sidebar.success("""
    **🗺️ Advanced Mapping** ✅
    
    ✅ Google Maps-like visualization
    ✅ Real road routing via OSRM
    ✅ Crime-aware route analysis
    ✅ Multi-modal travel support
    """)
else:
    st.sidebar.info("""
    **🗺️ Basic Mapping** ✅
    
    ✅ Crime pattern analysis
    ✅ Route planning
    ✅ Safety recommendations
    
    💡 Install enhanced modules for advanced features
    """)

if ALERTS_AVAILABLE:
    st.sidebar.success("""
    **🚨 Crime Alerts** ✅
    
    ✅ Real-time crime notifications
    ✅ Official LAPD station locator
    ✅ Interactive alert map
    ✅ Customizable alert settings
    ✅ Data from geohub.lacity.org
    """)

# Enhanced emergency section
st.sidebar.markdown("### 🚨 Emergency")
st.sidebar.error("""
**🆘 IMMEDIATE DANGER**
- **Police Emergency**: 911
- **Fire/Medical**: 911
""")

st.sidebar.warning("""
**📞 NON-EMERGENCY**
- **Police Reports**: 311
- **Traffic Issues**: 311
""")

# ✅ Data source information
st.sidebar.markdown("### 📊 Data Sources")
if ENHANCED_AVAILABLE:
    st.sidebar.markdown("""
    - **Crime Data**: LA Crime Database (Enhanced)
    - **Police Stations**: geohub.lacity.org
    - **Route Data**: OSRM/Free APIs
    - **Time Analysis**: Enhanced time-based filtering
    - **Risk Analysis**: AI-powered severity classification
    """)
else:
    st.sidebar.markdown("""
    - **Crime Data**: LA Crime Database
    - **Police Stations**: geohub.lacity.org
    - **Route Data**: Basic routing
    """)

# ✅ Current page and feature indicator
with st.sidebar:
    if st.session_state.page == "safe_route":
        if ENHANCED_AVAILABLE:
            st.info("📍 Currently: Enhanced Smart Route Mapping")
        else:
            st.info("📍 Currently: Basic Safe Route Mapping")
    else:
        st.info(f"📍 Currently: {menu}")
    
    # Feature status
    if ENHANCED_AVAILABLE:
        st.success("🚀 Enhanced Features: ACTIVE")
    else:
        st.warning("⚙️ Basic Features: ACTIVE")

# ✅ Enhanced Footer
st.markdown("---")
if ENHANCED_AVAILABLE:
    st.markdown(
        """
        <div style='text-align: center; color: #888;'>
            🛡️ Crime Safety Travel Assistant | 🆕 Enhanced AI-Powered Dynamic Route Planning<br>
            <small>🎯 Smart crime-aware routing with time-based pattern analysis | Official LAPD Data from LA City GeoHub</small>
        </div>
        """, 
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <div style='text-align: center; color: #888;'>
            🛡️ Crime Safety Travel Assistant | AI-Powered Route Planning with Crime Analysis<br>
            <small>Official LAPD Data from LA City GeoHub</small>
        </div>
        """, 
        unsafe_allow_html=True
    )