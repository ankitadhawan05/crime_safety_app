import streamlit as st
import pandas as pd
from utils_maps import compute_and_display_safe_route  # Only import what we need

# Remove forecast import if not needed or fix the import
# from forecast import forecast_crime

@st.cache_data
def load_crime_data():
    """Load crime data with caching"""
    df = pd.read_parquet("data/crime_data.parquet")
    return df.dropna(subset=["LAT", "LON", "AREA NAME"])

def render_ui():
    st.title("🛣️ Safe Route Planning & Crime Analysis")
    st.markdown("Plan your routes while avoiding high-crime areas based on real-time crime data analysis.")
    
    # Load data
    try:
        crime_df = load_crime_data()
        unique_areas = sorted(crime_df["AREA NAME"].unique())
        
        # Main content area
        tab1, tab2, tab3 = st.tabs(["🗺️ Route Planning", "📊 Area Analysis", "🔧 API Configuration"])
        
        with tab1:
            st.header("Safe Route Generator")
            
            # Real Road Routing Configuration (moved to tab for better organization)
            with st.expander("⚙️ Real Road Routing Setup"):
                st.markdown("**Configure Free APIs for Real Road Routes**")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**OpenRouteService (Recommended)**")
                    ors_api_key = st.text_input("🔑 OpenRouteService API Key", 
                        type="password", 
                        help="Get free API key from openrouteservice.org")
                    if st.button("📝 Get Free ORS Key", key="ors_signup"):
                        st.info("Visit: https://openrouteservice.org/dev/#/signup")
                
                with col2:
                    st.markdown("**GraphHopper (Alternative)**")
                    gh_api_key = st.text_input("🔑 GraphHopper API Key", 
                        type="password", 
                        help="Get free API key from graphhopper.com")
                    if st.button("📝 Get Free GH Key", key="gh_signup"):
                        st.info("Visit: https://www.graphhopper.com/")
                
                # API Status
                api_keys = {}
                if ors_api_key:
                    api_keys['openrouteservice'] = ors_api_key
                    st.success("✅ OpenRouteService configured for real roads")
                if gh_api_key:
                    api_keys['graphhopper'] = gh_api_key
                    st.success("✅ GraphHopper configured for real roads")
                
                if not api_keys:
                    st.info("💡 Add API keys above for real road routing, or use simulated routes below")
            
            # Route planning form
            with st.form("comprehensive_route_form"):
                st.markdown("### 📍 Route Configuration")
                
                col1, col2 = st.columns(2)
                with col1:
                    start_area = st.selectbox("🏁 Start Area", unique_areas)
                    travel_mode = st.selectbox("🚗 Travel Mode", 
                        ["driving", "walking", "cycling"],
                        format_func=lambda x: {"driving": "🚗 Driving", "walking": "🚶 Walking", "cycling": "🚴 Cycling"}[x])
                
                with col2:
                    end_area = st.selectbox("🎯 Destination Area", unique_areas)
                    route_preference = st.selectbox("🛡️ Safety Priority", 
                        ["balanced", "safest", "fastest"],
                        format_func=lambda x: {"balanced": "⚖️ Balanced", "safest": "🛡️ Maximum Safety", "fastest": "⚡ Speed Priority"}[x])
                
                # Advanced options
                st.markdown("#### 🔧 Advanced Options")
                col3, col4 = st.columns(2)
                
                with col3:
                    time_of_day = st.selectbox("⏰ Time of Travel", 
                        ["Any Time", "Morning (6-12)", "Afternoon (12-16)", "Evening (16-18)", "Night (18-6)"],
                        help="Crime patterns may vary by time of day")
                    
                    avoid_high_crime = st.checkbox("🚫 Avoid High Crime Areas", value=True,
                        help="Prioritize routes that avoid known high-crime zones")
                
                with col4:
                    gender_profile = st.selectbox("👤 Traveler Profile", 
                        ["Any", "Male", "Female"], 
                        help="Crime patterns may vary by gender")
                    
                    show_crime_overlay = st.checkbox("📊 Show Crime Data on Map", value=True,
                        help="Display crime hotspots as colored dots on the map")
                
                # Generate route button
                generate_route = st.form_submit_button("🚀 Generate Safe Routes", type="primary")
            
            # Process route generation
            if generate_route:
                if start_area == end_area:
                    st.warning("⚠️ Please select different start and destination areas.")
                else:
                    st.markdown("---")
                    st.subheader("🗺️ Your Safe Route Options")
                    
                    # Show routing method
                    if api_keys:
                        st.info("🛣️ Using real road networks for accurate routing")
                    else:
                        st.info("🛣️ Using simulated routing (add API keys above for real roads)")
                    
                    with st.spinner("🔍 Analyzing crime patterns and generating optimal routes..."):
                        # Determine force safe route based on preferences
                        force_safe_route = (route_preference == "safest")
                        
                        # Generate routes with all parameters
                        success = compute_and_display_safe_route(
                            start_area, 
                            end_area, 
                            travel_mode, 
                            force_safe_route, 
                            api_keys
                        )
                        
                        if success:
                            # Additional route information based on selections
                            st.markdown("---")
                            st.markdown("### 📋 Route Summary")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("🚗 Travel Mode", travel_mode.title())
                            
                            with col2:
                                st.metric("🛡️ Safety Priority", route_preference.title())
                            
                            with col3:
                                st.metric("⏰ Time Window", time_of_day)
                            
                            with col4:
                                if api_keys:
                                    st.metric("🛣️ Route Type", "Real Roads")
                                else:
                                    st.metric("🛣️ Route Type", "Simulated")
                            
                            # Contextual safety recommendations
                            with st.expander("🔒 Personalized Safety Recommendations"):
                                st.markdown(f"""
                                **Route-Specific Advice for {start_area} → {end_area}:**
                                """)
                                
                                # Time-based recommendations
                                if time_of_day != "Any Time":
                                    if "Night" in time_of_day:
                                        st.warning("🌙 **Night Travel**: Extra caution recommended. Consider alternative timing if possible.")
                                    elif "Evening" in time_of_day:
                                        st.info("🌆 **Evening Travel**: Stay in well-lit areas and maintain awareness.")
                                    else:
                                        st.success("☀️ **Daytime Travel**: Generally safer conditions.")
                                
                                # Gender-specific advice
                                if gender_profile != "Any":
                                    st.info(f"👤 **{gender_profile} Traveler**: Route analysis considers gender-specific crime patterns.")
                                
                                # Travel mode specific
                                if travel_mode == "walking":
                                    st.markdown("""
                                    **Walking Safety:**
                                    - 👥 Travel with others when possible
                                    - 📱 Share your route with someone
                                    - 🎧 Avoid headphones in unfamiliar areas
                                    - 🏃‍♂️ Trust your instincts about unsafe situations
                                    """)
                                elif travel_mode == "cycling":
                                    st.markdown("""
                                    **Cycling Safety:**
                                    - 🚴‍♂️ Wear bright, reflective clothing
                                    - 🛡️ Always wear a helmet
                                    - 🚲 Use bike lanes when available
                                    - 🔒 Secure your bike when stopping
                                    """)
                                else:  # driving
                                    st.markdown("""
                                    **Driving Safety:**
                                    - 🚗 Keep doors locked at all times
                                    - ⛽ Plan fuel stops in safe, well-lit areas
                                    - 📱 Use hands-free navigation
                                    - 🚨 If unsafe, drive to nearest police station
                                    """)
                                
                                # API-specific information
                                if api_keys:
                                    st.success("🛣️ **Real Road Routing**: Your route follows actual streets and intersections for accurate navigation.")
                                else:
                                    st.info("💡 **Tip**: Add free API keys above for turn-by-turn real road routing.")
                        else:
                            st.error("❌ Unable to generate routes. Please try different areas.")
        
        with tab2:
            st.header("Crime Analysis by Area")
            
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
                    # Key metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("📊 Total Incidents", len(area_data))
                    
                    with col2:
                        if 'Vict Sex' in area_data.columns:
                            most_common_victim = area_data['Vict Sex'].mode()[0] if not area_data['Vict Sex'].mode().empty else "N/A"
                            st.metric("👥 Most Affected", most_common_victim)
                    
                    with col3:
                        if 'Time of Day' in area_data.columns:
                            peak_time = area_data['Time of Day'].mode()[0] if not area_data['Time of Day'].mode().empty else "N/A"
                            st.metric("⏰ Peak Crime Time", peak_time)
                    
                    with col4:
                        if 'Crm Cd Desc' in area_data.columns:
                            top_crime = area_data['Crm Cd Desc'].mode()[0] if not area_data['Crm Cd Desc'].mode().empty else "N/A"
                            st.metric("🚨 Most Common Crime", top_crime[:20] + "..." if len(str(top_crime)) > 20 else str(top_crime))
                    
                    # Detailed analysis
                    if st.button("📈 Show Detailed Analysis", key="detailed_analysis"):
                        st.markdown("---")
                        st.subheader(f"Detailed Analysis for {selected_area}")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Time distribution
                            if 'Time of Day' in area_data.columns:
                                st.markdown("#### 🕐 Crime Distribution by Time")
                                time_dist = area_data['Time of Day'].value_counts()
                                st.bar_chart(time_dist)
                        
                        with col2:
                            # Gender distribution
                            if 'Vict Sex' in area_data.columns:
                                st.markdown("#### 👥 Victim Distribution")
                                gender_dist = area_data['Vict Sex'].value_counts()
                                st.bar_chart(gender_dist)
                        
                        # Crime types
                        if 'Crm Cd Desc' in area_data.columns:
                            st.markdown("#### 🚨 Top Crime Types")
                            crime_types = area_data['Crm Cd Desc'].value_counts().head(10)
                            st.bar_chart(crime_types)
                        
                        # Safety recommendations for this area
                        st.markdown("#### 🛡️ Area-Specific Safety Tips")
                        high_crime_time = area_data['Time of Day'].mode()[0] if not area_data['Time of Day'].mode().empty else "Unknown"
                        st.info(f"⚠️ **Peak crime time in {selected_area}**: {high_crime_time}")
                        
                        if high_crime_time == "Night":
                            st.warning("🌙 Avoid traveling through this area at night when possible.")
                        elif high_crime_time == "Evening":
                            st.info("🌆 Use extra caution during evening hours.")
                        
                else:
                    st.info(f"No crime data available for {selected_area}")
        
        with tab3:
            st.header("🔧 API Configuration & Setup")
            
            st.markdown("""
            ### 🌐 Real Road Routing APIs
            
            Get accurate, turn-by-turn routing on real streets using free APIs:
            """)
            
            # API comparison
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                #### 🎯 OpenRouteService
                - ✅ **2,000+ daily requests** (free tier)
                - ✅ **No credit card required**
                - ✅ **High-quality routing**
                - ✅ **Multiple travel modes**
                - 🌐 **Signup**: [openrouteservice.org](https://openrouteservice.org/dev/#/signup)
                """)
            
            with col2:
                st.markdown("""
                #### 🎯 GraphHopper
                - ✅ **500+ daily requests** (free tier)
                - ✅ **No payment info needed**
                - ✅ **Good backup option**
                - ✅ **Reliable service**
                - 🌐 **Signup**: [graphhopper.com](https://www.graphhopper.com/)
                """)
            
            # Setup instructions
            with st.expander("📋 Step-by-Step Setup Guide"):
                st.markdown("""
                **Setup Instructions:**
                
                1. **Choose an API Provider** (OpenRouteService recommended)
                2. **Visit their website** and create a free account
                3. **Generate an API key** from your dashboard
                4. **Copy the API key**
                5. **Paste it in the Route Planning tab** above
                6. **Start generating real road routes!**
                
                **No credit card or payment required for either service.**
                """)
            
            # Feature comparison
            st.markdown("### 📊 Routing Options Comparison")
            
            comparison_data = {
                "Feature": [
                    "Route Accuracy",
                    "Turn-by-turn Directions", 
                    "Traffic Awareness",
                    "Setup Required",
                    "Internet Required",
                    "Crime Risk Analysis",
                    "Multiple Route Options",
                    "Travel Mode Support"
                ],
                "Simulated Routes": [
                    "Approximate paths",
                    "No",
                    "No", 
                    "None",
                    "No",
                    "✅ Full support",
                    "✅ 3 options",
                    "✅ All modes"
                ],
                "Real Road Routes (API)": [
                    "Actual streets",
                    "Yes",
                    "Yes (some APIs)",
                    "Free registration", 
                    "Yes",
                    "✅ Full support",
                    "✅ 3 options",
                    "✅ All modes"
                ]
            }
            
            comparison_df = pd.DataFrame(comparison_data)
            st.table(comparison_df)
            
            # Troubleshooting
            with st.expander("🔧 Troubleshooting"):
                st.markdown("""
                **Common Issues & Solutions:**
                
                **API Key Issues:**
                - ❌ "Invalid API key" → Double-check the key from your provider dashboard
                - ❌ "Rate limit exceeded" → Wait a few minutes or try the other API
                - ❌ "Quota exceeded" → Check your daily usage limits
                
                **Route Generation Issues:**
                - ❌ "No route found" → Try different start/end areas
                - ❌ "Network error" → Check your internet connection
                - ❌ "Service unavailable" → API may be temporarily down, try later
                
                **Performance Issues:**
                - 🐌 Slow routing → Normal for first-time API calls
                - 🐌 Map loading slowly → Large datasets, this is normal
                - 🐌 App freezing → Refresh the page and try again
                
                **Alternative Solutions:**
                - Use simulated routes (no setup required)
                - Try different API providers
                - Use shorter distances for testing
                """)
    
    except Exception as e:
        st.error(f"Error loading crime data: {str(e)}")
        st.info("Please ensure the crime data file is available and try again.")

# Sidebar information
def add_sidebar_info():
    """Add informational sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ About This Tool")
    st.sidebar.markdown("""
    **🛣️ Safe Route Planning Features:**
    - Real road routing using free APIs
    - AI-powered crime risk analysis
    - Multiple route options (safe, balanced, direct)
    - Travel mode optimization (drive, walk, cycle)
    - Time-aware crime pattern analysis
    
    **Data Sources:**
    - Police crime reports
    - Geographic crime patterns
    - Real-time routing APIs
    - Machine learning clustering
    """)
    
    st.sidebar.markdown("### 🚨 Emergency Contacts")
    st.sidebar.markdown("""
    - **Police**: 911
    - **Emergency**: 911
    - **Non-Emergency**: 311
    """)
    
    st.sidebar.markdown("### 🔧 Quick Setup")
    st.sidebar.markdown("""
    **For Real Road Routing:**
    1. Go to API Configuration tab
    2. Sign up for free API key
    3. Enter key in Route Planning
    4. Generate real road routes!
    """)

if __name__ == "__main__":
    render_ui()
    add_sidebar_info()


