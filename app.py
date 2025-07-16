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

try:
    # Import the enhanced system
    from free_api_utils import compute_and_display_safe_route as enhanced_route
    
    def run_safe_route_mapping():
        """Safe Route Mapping with Google Maps-like experience"""
        st.markdown("### 🗺️ Safe Route Mapping")
        st.markdown("Plan your routes with real-time crime analysis and Google Maps-like visualization.")
        
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
        
        # Route planning form
        with st.form("safe_route_mapping_form"):
            st.markdown("### 📍 Route Configuration")
            
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
                safety_priority = st.selectbox("🛡️ Safety Priority", 
                    ["balanced", "maximum_safety", "speed_priority"],
                    format_func=lambda x: {"balanced": "⚖️ Balanced", "maximum_safety": "🛡️ Maximum Safety", "speed_priority": "⚡ Speed Priority"}[x],
                    help="How to balance safety vs speed")
            
            # Enhanced options
            st.markdown("#### 🔧 Route Options")
            col3, col4 = st.columns(2)
            
            with col3:
                time_of_day = st.selectbox("⏰ Time of Travel", 
                    ["Any Time", "Morning (6-12)", "Afternoon (12-18)", "Evening (18-22)", "Night (22-6)"],
                    help="Crime patterns may vary by time of day")
                
                avoid_high_crime = st.checkbox("🚫 Avoid High Crime Areas", value=True,
                    help="Prioritize routes that avoid known high-crime zones")
            
            with col4:
                gender_profile = st.selectbox("👤 Traveler Profile", 
                    ["Any", "Male", "Female"], 
                    help="Crime patterns may vary by gender")
                
                show_crime_overlay = st.checkbox("🔍 Show Crime Risk Zones", value=True,
                    help="Display crime hotspots on the map")
            
            # Generate route button
            generate_route = st.form_submit_button("🚀 Generate Safe Routes", type="primary", use_container_width=True)
        
        # Process route generation
        if generate_route:
            if start_area == end_area:
                st.warning("⚠️ Please select different start and destination areas.")
            else:
                st.markdown("---")
                
                with st.spinner("🔍 Analyzing crime patterns and generating routes..."):
                    # Generate routes with safety_priority parameter
                    force_safe = (safety_priority == "maximum_safety")
                    success = enhanced_route(start_area, end_area, travel_mode, force_safe, None, safety_priority)
                    
                    if not success:
                        st.error("❌ Unable to generate routes. Please try different areas.")
    
    def run_area_analysis():
        """Enhanced Area Analysis functionality with improved formatting and visualization"""
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
            
            if not area_data.empty:
                # Key metrics with improved formatting
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
                        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 4px solid #9467bd;">
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
                        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 4px solid #ff7f0e;">
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
                        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 4px solid #ff4b4b;">
                            <div style="color: #262730; font-size: 14px; font-weight: 600; margin-bottom: 4px;">
                                🚨 Most Common Crime
                            </div>
                            <div style="color: #262730; font-size: 11px; line-height: 1.2; word-wrap: break-word; font-weight: 500;">
                                {crime_text}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Detailed analysis
                if st.button("📈 Show Detailed Analysis", key="detailed_analysis"):
                    st.markdown("---")
                    st.subheader(f"Detailed Analysis for {selected_area}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if 'Time of Day' in area_data.columns:
                            st.markdown("#### 🕐 Crime Distribution by Time of Day")
                            time_dist = area_data['Time of Day'].value_counts()
                            st.bar_chart(time_dist)
                    
                    with col2:
                        if 'Vict Sex' in area_data.columns:
                            st.markdown("#### 👥 Victim Distribution by Gender")
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
                            
                            # Create clean distribution with exactly 3 categories
                            gender_dist = victim_sex_final.value_counts()
                            st.bar_chart(gender_dist)
                    
                    # Add victim distribution by age group
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        if 'Vict Age' in area_data.columns:
                            st.markdown("#### 👶👦👨👴 Victim Distribution by Age Group")
                            
                            # Clean age data and convert to numeric
                            victim_ages = pd.to_numeric(area_data['Vict Age'], errors='coerce')
                            
                            # Define age group categorization function (only for valid ages)
                            def categorize_age_group(age):
                                if pd.isna(age) or age < 0 or age > 120:  # Filter out invalid ages
                                    return None  # Will be filtered out
                                elif age < 12:
                                    return 'Children (0-11)'
                                elif age < 18:
                                    return 'Adolescents (12-17)'
                                elif age < 40:
                                    return 'Adults (18-39)'
                                elif age < 60:
                                    return 'Middle-aged (40-59)'
                                else:
                                    return 'Elderly (60+)'
                            
                            # Apply age group categorization and filter out invalid ages
                            age_groups = victim_ages.apply(categorize_age_group)
                            age_groups_valid = age_groups.dropna()  # Remove None values (invalid ages)
                            
                            # Create age group distribution (only valid ages)
                            age_dist = age_groups_valid.value_counts()
                            
                            # Reorder for logical display (youngest to oldest)
                            desired_order = ['Children (0-11)', 'Adolescents (12-17)', 'Adults (18-39)', 
                                           'Middle-aged (40-59)', 'Elderly (60+)']
                            age_dist_ordered = age_dist.reindex([cat for cat in desired_order if cat in age_dist.index])
                            
                            st.bar_chart(age_dist_ordered)
                    
                    with col4:
                        # Add some statistics about age distribution
                        if 'Vict Age' in area_data.columns:
                            st.markdown("#### 📊 Age Group Statistics")
                            
                            # Calculate statistics
                            victim_ages_clean = pd.to_numeric(area_data['Vict Age'], errors='coerce')
                            valid_ages = victim_ages_clean.dropna()
                            valid_ages = valid_ages[(valid_ages >= 0) & (valid_ages <= 120)]  # Filter realistic ages
                            
                            if len(valid_ages) > 0:
                                avg_age = valid_ages.mean()
                                median_age = valid_ages.median()
                                # Use only valid age groups for most vulnerable calculation
                                most_vulnerable_group = age_groups_valid.value_counts().index[0] if len(age_groups_valid.value_counts()) > 0 else "No data"
                                
                                st.markdown(f"""
                                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #17a2b8;">
                                    <div style="margin-bottom: 10px;">
                                        <strong>📈 Average Age:</strong> {avg_age:.1f} years
                                    </div>
                                    <div style="margin-bottom: 10px;">
                                        <strong>📊 Median Age:</strong> {median_age:.0f} years
                                    </div>
                                    <div style="margin-bottom: 10px;">
                                        <strong>🎯 Most Affected Group:</strong><br>
                                        <span style="color: #dc3545; font-weight: 600;">{most_vulnerable_group}</span>
                                    </div>
                                    <div style="font-size: 11px; color: #6c757d; margin-top: 10px;">
                                        Based on {len(valid_ages):,} valid age records
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.info("No valid age data available for analysis")
                        else:
                            st.info("Age data not available in this dataset")
                    
                    if 'Crm Cd Desc' in area_data.columns:
                        st.markdown("#### 🚨 Most Frequent Crime Types")
                        crime_types = area_data['Crm Cd Desc'].value_counts().head(10)
                        
                        # Calculate percentages
                        total_crimes = len(area_data)
                        crime_percentages = (crime_types / total_crimes * 100).round(1)
                        
                        # Create a custom chart with colors and better formatting
                        # Prepare data for plotting
                        crime_data_for_plot = pd.DataFrame({
                            'Crime Type': crime_percentages.index,
                            'Percentage': crime_percentages.values,
                            'Count': crime_types.values  # Keep count for tooltip
                        })
                        
                        # Truncate long crime names for better display
                        crime_data_for_plot['Crime Type'] = crime_data_for_plot['Crime Type'].apply(
                            lambda x: x[:25] + "..." if len(str(x)) > 25 else str(x)
                        )
                        
                        # Define colors for top 5 crimes
                        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', 
                                 '#FF9F43', '#6C5CE7', '#A29BFE', '#FD79A8', '#E17055']
                        
                        # Create the bar chart with percentages
                        fig = go.Figure(data=[
                            go.Bar(
                                x=crime_data_for_plot['Crime Type'],
                                y=crime_data_for_plot['Percentage'],
                                marker_color=colors[:len(crime_data_for_plot)],
                                text=[f"{pct}%" for pct in crime_data_for_plot['Percentage']],
                                textposition='auto',
                                hovertemplate='<b>%{x}</b><br>' +
                                            'Percentage: %{y}%<br>' +
                                            'Count: %{customdata}<br>' +
                                            '<extra></extra>',
                                customdata=crime_data_for_plot['Count']
                            )
                        ])
                        
                        # Update layout for better readability
                        fig.update_layout(
                            title=f"Most Frequent Crime Types in {selected_area} (% Distribution)",
                            xaxis_title="Crime Type",
                            yaxis_title="Percentage of Total Crimes (%)",
                            showlegend=False,
                            height=500,
                            xaxis=dict(
                                tickangle=-45,
                                tickfont=dict(size=10),
                            ),
                            yaxis=dict(
                                tickfont=dict(size=10),
                                ticksuffix="%"
                            ),
                            title_font=dict(size=14),
                            margin=dict(b=150)  # Increase bottom margin for rotated labels
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Area-specific safety recommendations
                    st.markdown("#### 🛡️ Area-Specific Safety Tips")
                    if 'Time of Day' in area_data.columns:
                        peak_time = area_data['Time of Day'].mode()[0] if not area_data['Time of Day'].mode().empty else "Any Time"
                        if peak_time == "Night":
                            st.warning(f"🌙 **Peak crime time in {selected_area}**: Night hours. Avoid traveling through this area at night when possible.")
                        elif peak_time == "Evening":
                            st.info(f"🌆 **Peak crime time in {selected_area}**: Evening hours. Use extra caution during evening.")
                        else:
                            st.success(f"☀️ **Peak crime time in {selected_area}**: {peak_time}. Generally safer conditions.")
                    
                    # Additional safety recommendations based on most common crimes
                    if 'Crm Cd Desc' in area_data.columns:
                        top_crimes = area_data['Crm Cd Desc'].value_counts().head(3)
                        st.markdown("##### 🎯 Crime-Specific Precautions")
                        
                        for i, (crime, count) in enumerate(top_crimes.items()):
                            crime_lower = str(crime).lower()
                            
                            if any(word in crime_lower for word in ['theft', 'burglary', 'robbery']):
                                st.info(f"🔒 **{crime}** ({count} incidents): Secure valuables, avoid displaying expensive items")
                            elif any(word in crime_lower for word in ['assault', 'battery']):
                                st.warning(f"⚠️ **{crime}** ({count} incidents): Stay in well-lit areas, avoid isolated locations")
                            elif any(word in crime_lower for word in ['vehicle', 'auto']):
                                st.info(f"🚗 **{crime}** ({count} incidents): Park in secure areas, lock vehicles, remove valuables")
                            else:
                                st.info(f"📊 **{crime}** ({count} incidents): Stay alert and follow general safety precautions")
            
            else:
                st.info(f"No crime data available for {selected_area}")
    
    ENHANCED_AVAILABLE = True
    
except ImportError:
    # Fallback to existing system
    try:
        from ui_safety_route import render_ui
        def run_safe_route_mapping():
            render_ui()
        ENHANCED_AVAILABLE = False
    except ImportError:
        def run_safe_route_mapping():
            st.error("Safe route mapping not available")
        ENHANCED_AVAILABLE = False

# ✅ Initialize session state for page navigation
if "page" not in st.session_state:
    st.session_state.page = "clustering"

# ✅ Main UI Header
st.title("🛡️ Crime Safety Travel Assistant")
st.markdown("*AI-powered crime analysis with intelligent route planning*")

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
    menu = st.sidebar.radio(
        "🧭 Choose Feature",
        [
            "🧭 Crime Hotspot Clustering",
            "🗺️ Safe Route Mapping", 
            "📊 Crime Forecasting"
        ],
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
            # Create tabs for route mapping and area analysis
            tab1, tab2 = st.tabs(["🗺️ Route Planning", "📊 Area Analysis"])
            
            with tab1:
                run_safe_route_mapping()
            
            with tab2:
                run_area_analysis()

        elif menu == "📊 Crime Forecasting":
            st.markdown("### 📊 Crime Forecasting")
            st.markdown("Predict future crime trends using advanced AI forecasting models.")
            run_forecast()

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        
        with st.expander("🔧 Troubleshooting"):
            st.markdown("""
            **Common Solutions:**
            
            1. **Refresh the page** - Fixes most temporary issues
            2. **Check data files** - Ensure data/crime_data.parquet exists
            3. **Try different areas** - Some may have limited data
            4. **Check dependencies** - Ensure required packages are installed
            """)

# ✅ Sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ System Features")

if ENHANCED_AVAILABLE:
    st.sidebar.success("""
    **🗺️ Enhanced Mapping** ✅
    
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
    """)

st.sidebar.markdown("### 🚨 Emergency")
st.sidebar.markdown("""
- **Police**: 911
- **Emergency**: 911
- **Non-Emergency**: 311
""")

# ✅ Current page indicator
with st.sidebar:
    if st.session_state.page == "safe_route":
        st.info("📍 Currently: Safe Route Mapping")
    else:
        st.info(f"📍 Currently: {menu}")

# ✅ Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888;'>
        🛡️ Crime Safety Travel Assistant | AI-Powered Route Planning with Crime Analysis
    </div>
    """, 
    unsafe_allow_html=True
)
    
    
    