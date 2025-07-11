import streamlit as st
import pandas as pd
from utils_maps import compute_and_display_safe_route

def run_risk_scoring():
    st.markdown("### 🛣️ Safe Route Generator & Risk Analysis")
    st.markdown("Generate optimal routes that avoid high-crime areas based on real crime data clustering.")
    
    # OSRM Configuration option
    with st.expander("⚙️ Real Road Routing (Free APIs)"):
        st.markdown("**Get Real Road Routes Using Free APIs**")
        
        # API Key inputs
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**OpenRouteService (Recommended)**")
            ors_api_key = st.text_input("🔑 OpenRouteService API Key", 
                type="password", 
                help="Sign up at openrouteservice.org for free")
            if st.button("📝 Get Free ORS API Key"):
                st.info("Visit: https://openrouteservice.org/dev/#/signup")
        
        with col2:
            st.markdown("**GraphHopper (Alternative)**")
            gh_api_key = st.text_input("🔑 GraphHopper API Key", 
                type="password", 
                help="Sign up at graphhopper.com for free tier")
            if st.button("📝 Get Free GraphHopper Key"):
                st.info("Visit: https://www.graphhopper.com/")
        
        # API Status
        api_keys = {}
        if ors_api_key:
            api_keys['openrouteservice'] = ors_api_key
            st.success("✅ OpenRouteService API configured")
        if gh_api_key:
            api_keys['graphhopper'] = gh_api_key
            st.success("✅ GraphHopper API configured")
        
        if not api_keys:
            st.info("💡 Enter API keys above to get real road routes. Otherwise, simulated routes will be used.")
            
            # Show comparison of routing options
            st.markdown("""
            **Routing Options Comparison:**
            
            | Feature | Simulated Routes | Real Road Routes (APIs) |
            |---------|------------------|------------------------|
            | **Accuracy** | Approximate | Actual streets & roads |
            | **Turn-by-turn** | No | Yes |
            | **Traffic awareness** | No | Yes (some APIs) |
            | **Setup required** | None | Free registration |
            | **Internet needed** | No | Yes |
            | **Crime analysis** | ✅ Full support | ✅ Full support |
            """)
        
        # API Information
        with st.expander("ℹ️ About Free Routing APIs"):
            st.markdown("""
            **OpenRouteService (Recommended):**
            - ✅ 2,000+ free requests per day
            - ✅ No credit card required for signup
            - ✅ Supports driving, walking, cycling
            - ✅ High-quality road data
            - 🌐 Website: openrouteservice.org
            
            **GraphHopper:**
            - ✅ 500+ free requests per day
            - ✅ No credit card required
            - ✅ Multiple travel modes
            - ✅ Good for backup/alternative
            - 🌐 Website: graphhopper.com
            
            **Setup Steps:**
            1. Visit the API provider website
            2. Create free account (no payment needed)
            3. Generate API key from dashboard
            4. Copy and paste key above
            5. Enjoy real road routing!
            """)
        
        # Legacy OSRM option
        st.markdown("---")
        st.markdown("**Local OSRM Server (Advanced)**")
        use_osrm = st.checkbox("🖥️ Use Local OSRM Server", 
            help="Enable if you have OSRM server running locally")
        
        if use_osrm:
            st.info("📡 OSRM server should be running on localhost:5000")
        else:
            st.info("🛣️ Using API-based or simulated routing")
    
    # Load data once and cache it
    @st.cache_data
    def load_area_data():
        df = pd.read_parquet("data/crime_data.parquet")
        return df['AREA NAME'].dropna().unique()
    
    try:
        unique_areas = load_area_data()
        
        # Create input form
        with st.form("route_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                start_area = st.selectbox("🏁 Select Start Area", unique_areas, help="Choose your starting location")
            
            with col2:
                end_area = st.selectbox("🏁 Select Destination Area", unique_areas, help="Choose your destination")
            
            # Additional options
            st.markdown("#### ⚙️ Route Options")
            col3, col4 = st.columns(2)
            
            with col3:
                travel_mode = st.selectbox("🚗 Travel Mode", 
                    ["driving", "walking", "cycling"],
                    format_func=lambda x: {"driving": "🚗 Driving", "walking": "🚶 Walking", "cycling": "🚴 Cycling"}[x],
                    help="Different modes show routes optimized for that travel type")
            
            with col4:
                route_preference = st.selectbox("🛡️ Route Preference", 
                    ["balanced", "safest", "fastest"],
                    format_func=lambda x: {"balanced": "⚖️ Balanced", "safest": "🛡️ Safest", "fastest": "⚡ Fastest"}[x],
                    help="Choose your priority: safety vs speed")
            
            # Submit button
            generate_route = st.form_submit_button("🚀 Generate Safe Route", type="primary", use_container_width=True)
        
        # Validation
        if generate_route:
            if start_area == end_area:
                st.warning("⚠️ Start and destination areas are the same. Please select different areas.")
                return
            
            # Show route generation progress
            with st.spinner("🔍 Analyzing crime patterns and computing optimal route..."):
                # Add progress steps
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Loading crime data...")
                progress_bar.progress(25)
                
                status_text.text("Clustering crime patterns...")
                progress_bar.progress(50)
                
                status_text.text("Computing optimal routes...")
                progress_bar.progress(75)
                
                # Determine if we should force safest route
                force_safe_route = (route_preference == "safest")
                
                # Generate the routes with travel mode and API keys
                success = compute_and_display_safe_route(start_area, end_area, travel_mode, force_safe_route, api_keys)
                
                progress_bar.progress(100)
                status_text.text("Route generation complete!")
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                if success:
                    st.success("✅ Routes generated successfully!")
                    
                    # Show API usage info
                    if api_keys:
                        st.info("🛣️ Real road routes generated using free APIs!")
                    else:
                        st.info("🛣️ Simulated routes generated. Add API keys above for real roads.")
                    
                    # Add route tips based on travel mode and preference
                    with st.expander("💡 Safety Tips for Your Journey"):
                        st.markdown(f"""
                        **Safety Recommendations for {travel_mode.title()}:**
                        """)
                        
                        # Mode-specific recommendations
                        if travel_mode == "driving":
                            st.markdown("""
                            - 🚗 Keep vehicle doors locked at all times
                            - ⛽ Plan fuel stops in well-lit, busy areas
                            - 📱 Use hands-free navigation devices
                            - 🚨 If you feel unsafe, drive to nearest police station
                            - 💰 Avoid displaying valuable items in the car
                            """)
                        elif travel_mode == "walking":
                            st.markdown("""
                            - 👥 Walk with companions when possible
                            - 🔦 Carry a flashlight for evening walks
                            - 👀 Stay alert and avoid distractions like headphones
                            - 📱 Share your route and ETA with someone
                            - 🏃‍♂️ Trust your instincts - if area feels unsafe, leave
                            """)
                        elif travel_mode == "cycling":
                            st.markdown("""
                            - 🚴‍♂️ Wear bright, reflective clothing
                            - 🛡️ Always wear a properly fitted helmet
                            - 🚲 Use designated bike lanes when available
                            - 💡 Use front and rear lights during low visibility
                            - 🔒 Secure your bike properly when stopping
                            """)
                        
                        # Route preference specific tips
                        if route_preference == "safest":
                            st.info("🛡️ You selected the safest route option. This may take longer but avoids high-crime areas.")
                        elif route_preference == "fastest":
                            st.warning("⚡ You selected the fastest route. Stay extra alert as this may pass through higher-risk areas.")
                        
                        # API-specific tips
                        if api_keys:
                            st.success("🛣️ Real road routing provides accurate turn-by-turn navigation on actual streets.")
                        else:
                            st.info("💡 For real road routing, get free API keys from OpenRouteService or GraphHopper above.")
                        
                        # General safety tips
                        st.markdown("""
                        **General Safety Tips:**
                        - 🕐 Avoid traveling during late night hours when possible
                        - 📍 Stay on main roads and well-lit areas
                        - 🚨 Keep emergency contacts readily available
                        - 📱 Ensure your phone is fully charged
                        """)
                else:
                    st.error("❌ Could not generate routes. Please try different areas or check your connection.")
                    
                    with st.expander("🔧 Troubleshooting"):
                        st.markdown("""
                        **If route generation fails:**
                        1. Try selecting different start and destination areas
                        2. Check if the selected areas have sufficient location data
                        3. Try a different travel mode
                        4. For real roads: verify your API keys are correct
                        5. Check your internet connection
                        6. Contact support if the issue persists
                        
                        **API-Related Issues:**
                        - Invalid API key: Double-check the key from your provider
                        - Rate limit exceeded: Wait a few minutes before trying again
                        - Quota exceeded: Check your API usage limits
                        - Network issues: Verify internet connectivity
                        
                        **Alternative Solutions:**
                        - Use simulated routes (no API key required)
                        - Try different free API providers
                        - Use shorter distances for testing
                        """)
    
    except Exception as e:
        st.error(f"An error occurred while loading the application: {str(e)}")
        st.info("Please refresh the page and try again.")

# Additional utility function for the main app
def run_safe_route_ui():
    """Wrapper function for page routing"""
    run_risk_scoring()



