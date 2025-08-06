import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ✅ Set page config with enhanced styling
st.set_page_config(
    page_title="🛡️ Crime Safety Travel Assistant", 
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🛡️"
)

# ✅ Enhanced CSS styling for professional appearance
st.markdown("""
<style>
    /* Main background and typography */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    
    /* Feature cards */
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        margin: 1rem 0;
        border-left: 4px solid #667eea;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Metrics */
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        text-align: center;
    }
    
    /* Success/Warning/Error styling */
    .stSuccess {
        background: linear-gradient(135deg, #4CAF50, #45a049);
        border-radius: 8px;
    }
    
    .stWarning {
        background: linear-gradient(135deg, #ff9800, #f57c00);
        border-radius: 8px;
    }
    
    .stError {
        background: linear-gradient(135deg, #f44336, #d32f2f);
        border-radius: 8px;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    
    /* Custom font sizes */
    .big-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    
    .medium-title {
        font-size: 1.8rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .small-title {
        font-size: 1.2rem;
        font-weight: 500;
        color: #666;
    }
    
    /* Introduction page specific styling */
    .intro-hero {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.15);
    }
    
    /* Safety images styling */
    .safety-images {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 3rem;
        margin: 2rem 0;
        padding: 2rem;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
    }
    
    .safety-image-container {
        position: relative;
        width: 240px;
        height: 180px;
    }
    
    .safety-pins-bg {
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, #87CEEB 0%, #4682B4 100%);
        border-radius: 10px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .safety-pin {
        position: absolute;
        width: 30px;
        height: 15px;
        border: 2px solid #C0C0C0;
        border-radius: 20px 20px 0 0;
        background: transparent;
    }
    
    .safety-pin::after {
        content: '';
        position: absolute;
        bottom: -8px;
        left: 2px;
        width: 2px;
        height: 20px;
        background: #C0C0C0;
    }
    
    .pin1 { top: 20px; left: 30px; transform: rotate(-15deg); }
    .pin2 { top: 40px; right: 40px; transform: rotate(25deg); }
    .pin3 { bottom: 60px; left: 20px; transform: rotate(45deg); }
    .pin4 { bottom: 30px; right: 20px; transform: rotate(-30deg); }
    .pin5 { top: 70px; left: 80px; transform: rotate(10deg); }
    
    .location-pin {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 60px;
        height: 80px;
        z-index: 2;
    }
    
    .location-pin svg {
        width: 100%;
        height: 100%;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
    }
    
    .safety-text {
        flex: 1;
        max-width: 300px;
    }
    
    .safety-byline {
        font-size: 2.5rem;
        font-weight: 700;
        color: #4682B4;
        text-align: left;
        line-height: 1.2;
        margin: 0;
    }
    
    @media (max-width: 768px) {
        .safety-images {
            flex-direction: column;
            gap: 2rem;
        }
        
        .safety-byline {
            text-align: center;
            font-size: 2rem;
        }
    }
    
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

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
                        
                        # THE MAP WOULD BE DISPLAYED HERE BY THE enhanced_route FUNCTION
                        
                        # ROUTE SAFETY GUIDE - Now appears BELOW the map with updated percentages
                        st.markdown("### 📊 Route Safety Guide")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.success("🟢 **Safe Routes** - Minimal crime zone exposure (<20%)")
                        with col2:
                            st.warning("🟡 **Moderate Routes** - Some crime zone exposure (20-40%)")
                        with col3:
                            st.error("🔴 **High Risk Routes** - Significant crime exposure (>40%)")
                        
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
    
    # FIXED Enhanced Area Analysis with better integration
    def run_area_analysis():
        """Enhanced Area Analysis functionality with uniform purple color scheme"""
        st.markdown("### 📊 Crime Analysis by Area")
        
        # Load area data
        @st.cache_data
        def load_crime_data_for_analysis():
            try:
                df = pd.read_parquet("data/crime_data.parquet")
                df = df.dropna(subset=["LAT", "LON", "AREA NAME"])
                
                # Extract time of day from TIME OCC if not present
                if 'Time of Day' not in df.columns and 'TIME OCC' in df.columns:
                    # Convert TIME OCC to proper time format
                    df['TIME OCC'] = pd.to_numeric(df['TIME OCC'], errors='coerce')
                    df['Hour'] = (df['TIME OCC'] // 100).fillna(12).astype(int)
                    
                    # Create time of day categories
                    def categorize_time(hour):
                        if 6 <= hour < 12:
                            return "Morning"
                        elif 12 <= hour < 18:
                            return "Afternoon"
                        elif 18 <= hour < 22:
                            return "Evening"
                        else:
                            return "Night"
                    
                    df['Time of Day'] = df['Hour'].apply(categorize_time)
                
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
                st.error(f"Error loading crime data: {e}")
                return None
        
        crime_df = load_crime_data_for_analysis()
        
        if crime_df is None:
            st.error("Could not load crime data for analysis.")
            return
        
        unique_areas = sorted(crime_df["AREA NAME"].unique())
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            selected_area = st.selectbox("🏘️ Select Area for Analysis", unique_areas, key="analysis_area")
        
        with col2:
            analysis_timeframe = st.selectbox("📅 Time Period", 
                ["All Time", "Last Year", "Last 6 Months", "Last 3 Months"])
        
        if selected_area:
            # Filter data for selected area
            area_data = crime_df[crime_df["AREA NAME"] == selected_area]
            
            # Apply time period filtering
            if analysis_timeframe != "All Time":
                from datetime import datetime, timedelta
                current_date = datetime.now()
                
                if analysis_timeframe == "Last Year":
                    cutoff_date = current_date - timedelta(days=365)
                elif analysis_timeframe == "Last 6 Months":
                    cutoff_date = current_date - timedelta(days=180)
                elif analysis_timeframe == "Last 3 Months":
                    cutoff_date = current_date - timedelta(days=90)
                
                # Filter based on DATE OCC if available
                if 'DATE OCC' in area_data.columns:
                    try:
                        area_data['DATE OCC'] = pd.to_datetime(area_data['DATE OCC'], errors='coerce')
                        area_data = area_data[area_data['DATE OCC'] >= cutoff_date]
                    except:
                        st.info(f"Note: Time filtering not applied - date format issues in data")
            
            if not area_data.empty:
                # Key metrics with improved formatting and purple accent
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_incidents = len(area_data)
                    st.markdown(f"""
                    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 4px solid #9c27b0;">
                        <div style="color: #262730; font-size: 14px; font-weight: 600; margin-bottom: 4px;">
                            📊 Total Incidents
                        </div>
                        <div style="color: #262730; font-size: 18px; font-weight: 700; line-height: 1.2;">
                            {total_incidents:,}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if 'Vict Sex' in area_data.columns:
                        # Clean and categorize victim sex data into exactly 3 categories
                        victim_sex_cleaned = area_data['Vict Sex'].fillna('Others').str.upper().str.strip()
                        
                        # Map all variations to 3 categories only
                        def categorize_victim_sex(sex):
                            if sex in ['M', 'MALE']:
                                return 'Male'
                            elif sex in ['F', 'FEMALE']:
                                return 'Female'
                            else:  # X, H, -, NaN, Others, etc.
                                return 'Others'
                        
                        victim_sex_final = victim_sex_cleaned.apply(categorize_victim_sex)
                        
                        # Get most common victim category
                        most_common_victim = victim_sex_final.mode()[0] if not victim_sex_final.mode().empty else "N/A"
                        
                        st.markdown(f"""
                        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 4px solid #9c27b0;">
                            <div style="color: #262730; font-size: 14px; font-weight: 600; margin-bottom: 4px;">
                                👥 Most Affected
                            </div>
                            <div style="color: #262730; font-size: 18px; font-weight: 700; line-height: 1.2;">
                                {most_common_victim}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                with col3:
                    if 'Time of Day' in area_data.columns:
                        peak_time = area_data['Time of Day'].mode()[0] if not area_data['Time of Day'].mode().empty else "N/A"
                        
                        st.markdown(f"""
                        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 4px solid #9c27b0;">
                            <div style="color: #262730; font-size: 14px; font-weight: 600; margin-bottom: 4px;">
                                ⏰ Peak Crime Time
                            </div>
                            <div style="color: #262730; font-size: 18px; font-weight: 700; line-height: 1.2;">
                                {peak_time}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                with col4:
                    if 'Crm Cd Desc' in area_data.columns:
                        top_crime = area_data['Crm Cd Desc'].mode()[0] if not area_data['Crm Cd Desc'].mode().empty else "N/A"
                        # Display full crime text with smaller font using HTML
                        crime_text = str(top_crime)
                        
                        # Use HTML to make the text smaller and wrap if needed
                        st.markdown(f"""
                        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 4px solid #9c27b0;">
                            <div style="color: #262730; font-size: 14px; font-weight: 600; margin-bottom: 4px;">
                                🚨 Most Common Crime
                            </div>
                            <div style="color: #262730; font-size: 11px; line-height: 1.2; word-wrap: break-word; font-weight: 500;">
                                {crime_text}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("Crime description data not available")
                
                # Rest of the detailed analysis code continues here...
                # [Include all the detailed analysis code from the original file]
    
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
            # Include your existing area analysis implementation
            st.info("Area analysis feature - implementation needed")
        
        ENHANCED_AVAILABLE = False
        
    except ImportError:
        def run_safe_route_mapping():
            st.error("Safe route mapping not available")
        
        def run_area_analysis():
            st.error("Area analysis not available")
        
        ENHANCED_AVAILABLE = False

# ✅ NEW INTRODUCTION PAGE FUNCTION
def show_introduction_page():
    """Show the introduction/welcome page"""
    
    # Hero section
    st.markdown("""
    <div class="intro-hero">
        <div class="big-title">🛡️ Welcome to the Crime Safety Travel Assistant</div>
        <div class="medium-title">A Smart Travel Planner for Safer Journeys</div>
        <p style="font-size: 1.2rem; margin-top: 1rem; opacity: 0.9;">
            Keep yourself and your loved ones safe from crime risks with AI-powered route planning 
            and real-time safety intelligence.
        </p>
        <p style="font-size: 0.9rem; margin-top: 1rem; opacity: 0.8; background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px;">
            🌐 <strong>This is a free public service</strong> - Anyone can use this tool to plan safer routes in Los Angeles
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Safety images section
    st.markdown("""
    <div class="safety-images">
        <div class="safety-image-container">
            <div class="safety-pins-bg">
                <div class="safety-pin pin1"></div>
                <div class="safety-pin pin2"></div>
                <div class="safety-pin pin3"></div>
                <div class="safety-pin pin4"></div>
                <div class="safety-pin pin5"></div>
            </div>
            <div class="location-pin">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" fill="#000000"/>
                    <circle cx="12" cy="9" r="2.5" fill="#FFFFFF"/>
                </svg>
            </div>
        </div>
        <div class="safety-text">
            <div class="safety-byline">Pin your<br>safety</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Core features section
    st.markdown('<div class="feature-grid">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3 style="color: #667eea; margin-bottom: 1rem;">🗺️ Enhanced Smart Routing</h3>
            <ul style="line-height: 1.8; color: #444;">
                <li><strong>Crime-aware route planning</strong> that adapts to real crime patterns</li>
                <li><strong>Safety priority filtering</strong> with maximum safety, balanced, and speed options</li>
                <li><strong>Time-based analysis</strong> considering crime patterns throughout the day</li>
                <li><strong>Intelligent route recommendations</strong> with dynamic safety messaging</li>
                <li><strong>Multi-modal support</strong> for driving, walking, and cycling</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3 style="color: #667eea; margin-bottom: 1rem;">🎯 Advanced Mapping & Analysis</h3>
            <ul style="line-height: 1.8; color: #444;">
                <li><strong>Interactive crime visualization</strong> with Google Maps-like interface</li>
                <li><strong>Alternative route generation</strong> based on crime risk levels</li>
                <li><strong>Gender and time-specific routing</strong> for personalized safety</li>
                <li><strong>Street-level safety analysis</strong> showing which areas to avoid</li>
                <li><strong>Real-time risk assessment</strong> for different times of day</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h3 style="color: #667eea; margin-bottom: 1rem;">🚨 Crime Alerts & Intelligence</h3>
            <ul style="line-height: 1.8; color: #444;">
                <li><strong>Real-time crime notifications</strong> for your travel areas</li>
                <li><strong>Official LAPD station locator</strong> with contact information</li>
                <li><strong>Interactive alert mapping</strong> showing recent incidents</li>
                <li><strong>Customizable alert settings</strong> for personalized monitoring</li>
                <li><strong>Official data integration</strong> from LA City GeoHub</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # How it works section
    st.markdown("---")
    st.markdown('<div class="medium-title" style="text-align: center; margin: 2rem 0;">🧠 How It Works</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📊</div>
            <h4 style="color: #667eea;">Analyze Crime Data</h4>
            <p style="color: #666;">AI processes historical crime patterns and real-time incidents</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🗺️</div>
            <h4 style="color: #667eea;">Generate Routes</h4>
            <p style="color: #666;">Create multiple route options with different safety levels</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🎯</div>
            <h4 style="color: #667eea;">Risk Assessment</h4>
            <p style="color: #666;">Color-code routes based on actual crime zone proximity</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🛡️</div>
            <h4 style="color: #667eea;">Stay Safe</h4>
            <p style="color: #666;">Get personalized safety recommendations and alerts</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Getting started section
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; background: white; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
            <h3 style="color: #667eea; margin-bottom: 1rem;">🚀 Ready to Start?</h3>
            <p style="color: #666; margin-bottom: 1.5rem;">
                Begin by exploring crime hotspots in your area, then plan safer routes for your journeys.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🧭 Explore Crime Hotspots", type="primary", use_container_width=True):
            st.session_state.current_page = "Crime Hotspot Clustering"
            st.rerun()
    
    # Data source and disclaimer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 1rem; color: #666; font-size: 0.9rem;">
        <p><strong>Data Sources:</strong> Official LAPD crime data from LA City GeoHub • Police station locations from geohub.lacity.org</p>
        <p><strong>Disclaimer:</strong> This tool provides guidance based on historical data. Always use your judgment and follow local safety guidelines.</p>
    </div>
    """, unsafe_allow_html=True)

# ✅ Initialize session state for page navigation
if "page" not in st.session_state:
    st.session_state.page = "clustering"

if "current_page" not in st.session_state:
    st.session_state.current_page = "Introduction"

# Initialize route planning session state
if "route_start" not in st.session_state:
    st.session_state.route_start = None
if "route_end" not in st.session_state:
    st.session_state.route_end = None

# ✅ Main UI Header (only show if not on introduction page)
if st.session_state.current_page != "Introduction":
    st.markdown("""
    <div class="main-header">
        <div class="big-title">🛡️ Crime Safety Travel Assistant</div>
        <p style="font-size: 1.1rem; margin: 0; opacity: 0.9;">
            AI-powered route planning with enhanced crime analysis and safety intelligence
        </p>
    </div>
    """, unsafe_allow_html=True)

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
    # ✅ Navigation with Introduction page
    menu_options = [
        "🏠 Introduction",
        "🧭 Crime Hotspot Clustering",
        "🗺️ Safe Route Mapping", 
        "📊 Crime Forecasting"
    ]
    
    # Add crime alerts option if available
    if ALERTS_AVAILABLE:
        menu_options.append("🚨 Crime Alerts")
    
    # Use current_page from session state for navigation
    if st.session_state.current_page not in [opt.split(" ", 1)[1] for opt in menu_options]:
        st.session_state.current_page = "Introduction"
    
    # Create menu with current selection
    menu_index = 0
    for i, opt in enumerate(menu_options):
        if opt.split(" ", 1)[1] == st.session_state.current_page:
            menu_index = i
            break
    
    menu = st.sidebar.radio(
        "🧭 Navigation",
        menu_options,
        index=menu_index,
        help="Select the feature you want to use"
    )
    
    # Update current page when menu changes
    selected_page = menu.split(" ", 1)[1]
    if selected_page != st.session_state.current_page:
        st.session_state.current_page = selected_page
        st.rerun()

    # ✅ Reset page state when using normal navigation
    if st.session_state.current_page == "Crime Hotspot Clustering":
        st.session_state.page = "clustering"

    # ✅ Menu logic
    try:
        if st.session_state.current_page == "Introduction":
            show_introduction_page()
            
        elif st.session_state.current_page == "Crime Hotspot Clustering":
            # Updated font sizes as requested
            st.markdown('<h1 style="font-size: 2.2rem; font-weight: 700; color: #333; margin-bottom: 0.5rem;">🧭 Crime Hotspot Analysis</h1>', unsafe_allow_html=True)
            st.markdown('<p style="font-size: 1rem; color: #666; margin-bottom: 1.5rem;">Check areas with Crime Hotspots</p>', unsafe_allow_html=True)
            run_clustering_ui()

        elif st.session_state.current_page == "Safe Route Mapping":
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

        elif st.session_state.current_page == "Crime Forecasting":
            st.markdown("### 📊 Crime Forecasting")
            st.markdown("Predict future crime trends using advanced AI forecasting models.")
            run_forecast()
        
        elif st.session_state.current_page == "Crime Alerts" and ALERTS_AVAILABLE:
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

# ✅ Simplified Sidebar (removed the system features section as requested)
st.sidebar.markdown("---")

# Public Service Notice
st.sidebar.markdown("""
### 🌐 Public Access
This tool is **free and open to everyone**.
Help us improve by reporting any issues.
""")

st.sidebar.markdown("---")

# Enhanced emergency section
st.sidebar.markdown("### 🚨 Emergency Contacts")
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

# ✅ Current page indicator
with st.sidebar:
    st.info(f"📍 Currently: {st.session_state.current_page}")

# ✅ Enhanced Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888; padding: 1rem; background: white; border-radius: 10px; margin-top: 2rem;'>
        <div style='font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;'>
            🛡️ Crime Safety Travel Assistant
        </div>
        <div style='font-size: 0.9rem;'>
            AI-Powered Route Planning with Enhanced Crime Analysis<br>
            <small>Official LAPD Data from LA City GeoHub</small><br>
            <small style='color: #667eea; font-weight: 600;'>🌐 Free Public Service - Open to Everyone</small>
        </div>
        <div style='font-size: 0.8rem; margin-top: 0.5rem; color: #999;'>
            <strong>Disclaimer:</strong> This tool uses historical crime data for educational and safety planning purposes only.<br>
            Always use your judgment and follow official safety guidelines.
        </div>
    </div>
    """, 
    unsafe_allow_html=True
)
