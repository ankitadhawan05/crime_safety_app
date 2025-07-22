import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
from data_preprocess import load_crime_data, preprocess_for_clustering
from clustering_engine import load_clustering_model

# Cache model load once
@st.cache_resource
def get_model_and_scaler():
    return load_clustering_model()

# Cache data processing
@st.cache_data
def get_processed_data():
    """Load and preprocess data once, cache the result"""
    df = load_crime_data()
    df_encoded, extra_cols = preprocess_for_clustering(df)
    return df, df_encoded, extra_cols

# Cache clustering results - FIXED VERSION
@st.cache_data
def get_clustered_data(_df, _df_encoded, extra_cols):
    """Perform clustering and cache results - Fixed to handle index alignment"""
    features = ['LAT', 'LON', 'Part 1-2'] + extra_cols
    
    # Load model and scaler
    model, scaler = get_model_and_scaler()
    
    # CRITICAL FIX: Ensure both dataframes have the same index
    # Reset index to ensure alignment
    df_copy = _df.reset_index(drop=True)
    df_encoded_copy = _df_encoded.reset_index(drop=True)
    
    # Verify they have the same length
    if len(df_copy) != len(df_encoded_copy):
        st.error(f"Data length mismatch: Original={len(df_copy)}, Encoded={len(df_encoded_copy)}")
        st.stop()
    
    # DTYPE FIX: Ensure consistent data types for features
    feature_data = df_encoded_copy[features].copy()
    
    # Convert all features to float64 to match training data
    for col in features:
        feature_data[col] = feature_data[col].astype(np.float64)
    
    # Scale features & predict clusters
    try:
        scaled = scaler.transform(feature_data)
        
        # Ensure scaled data is float64
        scaled = scaled.astype(np.float64)
        
        clusters = model.predict(scaled)
        
        # Add clusters to original dataframe
        result_df = df_copy.copy()
        result_df['Cluster'] = clusters
        
        return result_df
    except Exception as e:
        st.error(f"Clustering error: {str(e)}")
        st.stop()

# NEW FUNCTION: Apply clustering to filtered data
def apply_clustering_to_filtered_data(original_df, original_encoded, extra_cols, filtered_indices):
    """Apply clustering specifically to filtered data"""
    features = ['LAT', 'LON', 'Part 1-2'] + extra_cols
    
    # Load model and scaler
    model, scaler = get_model_and_scaler()
    
    # Get the corresponding encoded data for filtered indices
    # Reset indices to ensure proper alignment
    filtered_df = original_df.iloc[filtered_indices].reset_index(drop=True)
    filtered_encoded = original_encoded.iloc[filtered_indices].reset_index(drop=True)
    
    # DTYPE FIX: Ensure consistent data types for features
    feature_data = filtered_encoded[features].copy()
    
    # Convert all features to float64 to match training data
    for col in features:
        feature_data[col] = feature_data[col].astype(np.float64)
    
    # Scale features & predict clusters with proper dtype
    scaled = scaler.transform(feature_data)
    
    # Ensure scaled data is float64
    scaled = scaled.astype(np.float64)
    
    clusters = model.predict(scaled)
    
    # Add clusters to filtered dataframe
    result_df = filtered_df.copy()
    result_df['Cluster'] = clusters
    
    return result_df

def generate_cluster_map_optimized(df, max_points=2000):
    """Optimized map generation with sampling for large datasets"""
    
    # Sample data if too large - remove info message
    if len(df) > max_points:
        df_sample = df.sample(n=max_points, random_state=42)
    else:
        df_sample = df
    
    # FIXED: Correct color mapping and cluster labels
    color_map = {0: 'red', 1: 'green', 2: 'orange'}  # 0=High, 1=Low, 2=Medium
    cluster_labels = {0: 'High Risk Zone', 1: 'Low Risk Zone', 2: 'Medium Risk Zone'}
    
    center_lat, center_lon = df['LAT'].mean(), df['LON'].mean()
    
    # Create map with optimized settings
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=12,
        prefer_canvas=True  # Better performance for many markers
    )
    
    # Group markers by cluster for better performance
    for cluster_id in sorted(df_sample['Cluster'].unique()):
        cluster_data = df_sample[df_sample['Cluster'] == cluster_id]
        
        # Create marker cluster for each cluster type
        marker_cluster = folium.plugins.MarkerCluster(
            name=f'Cluster {cluster_id}',
            options={'maxClusterRadius': 50}
        ).add_to(m)
        
        for _, row in cluster_data.iterrows():
            tooltip = (
                f"<b>Zone:</b> {cluster_labels[row['Cluster']]}<br>"
                f"<b>Area:</b> {row['AREA NAME']}<br>"
                f"<b>Victim Sex:</b> {row['Vict Sex']}<br>"
                f"<b>Time of Day:</b> {row['Time of Day']}"
            )
            
            folium.CircleMarker(
                location=(row['LAT'], row['LON']),
                radius=4,
                color=color_map.get(row['Cluster'], 'gray'),
                fill=True,
                fill_opacity=0.6,
                tooltip=tooltip
            ).add_to(marker_cluster)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    return m

@st.cache_data
def get_cluster_summary(_df):
    """Cache cluster summary statistics"""
    label_map = {0: 'High Crime Zone', 1: 'Low Crime Zone', 2: 'Medium Risk Zone'}
    
    # Pre-compute all statistics
    cluster_stats = {}
    for cluster_id in sorted(_df['Cluster'].unique()):
        cluster_df = _df[_df['Cluster'] == cluster_id]
        count = len(cluster_df)
        
        # Crime type counts
        serious_count = cluster_df[cluster_df['Part 1-2'] == 1].shape[0]
        less_serious_count = cluster_df[cluster_df['Part 1-2'] == 2].shape[0]
        
        # Gender distribution
        sex_counts = cluster_df['Vict Sex'].value_counts().to_dict()
        f_count = sex_counts.get('F', 0)
        m_count = sex_counts.get('M', 0)
        o_count = sex_counts.get('Others', 0)
        
        f_pct = round((f_count / count) * 100, 1) if count > 0 else 0
        m_pct = round((m_count / count) * 100, 1) if count > 0 else 0
        o_pct = round((o_count / count) * 100, 1) if count > 0 else 0
        
        # Top crimes by gender
        def top_crime(df_subset):
            if 'Crm Cd Desc' in df_subset.columns and not df_subset.empty:
                return df_subset['Crm Cd Desc'].value_counts().idxmax()
            return "N/A"
        
        top_female = top_crime(cluster_df[cluster_df['Vict Sex'] == 'F'])
        top_male = top_crime(cluster_df[cluster_df['Vict Sex'] == 'M'])
        top_others = top_crime(cluster_df[cluster_df['Vict Sex'] == 'Others'])
        
        # Top areas in cluster
        top_areas = cluster_df['AREA NAME'].value_counts().head(3).index.tolist()
        
        cluster_stats[cluster_id] = {
            'label': label_map.get(cluster_id),
            'count': count,
            'serious_count': serious_count,
            'less_serious_count': less_serious_count,
            'f_pct': f_pct, 'f_count': f_count,
            'm_pct': m_pct, 'm_count': m_count,
            'o_pct': o_pct, 'o_count': o_count,
            'top_female': top_female,
            'top_male': top_male,
            'top_others': top_others,
            'top_areas': top_areas
        }
    
    return cluster_stats

def generate_cluster_stats_optimized(cluster_stats):
    """Display pre-computed cluster statistics"""
    for cluster_id, stats in cluster_stats.items():
        with st.expander(f"🔹 Cluster {cluster_id}: {stats['label']}"):
            st.markdown(f"""
**Total Incidents:** {stats['count']}  
**Serious Crimes (Part 1):** {stats['serious_count']}  
**Less Serious Crimes (Part 2):** {stats['less_serious_count']}  

**Victim Distribution:**  
Women: {stats['f_pct']}% ({stats['f_count']}) | Men: {stats['m_pct']}% ({stats['m_count']}) | Others: {stats['o_pct']}% ({stats['o_count']})  

**Most frequent crimes:**  
- Women: _{stats['top_female']}_  
- Men: _{stats['top_male']}_  
- Others: _{stats['top_others']}_

**Top Areas:** {', '.join(stats['top_areas'])}
""")

def run_clustering_ui():
    st.header("Check areas with Crime Hotspots")
    
    # Add informational message about police stations
    st.info("💡 **Tip:** To view the list of police stations near crime risk zones and the full stations directory, click on **Crime Alerts** in the sidebar.")
    
    # Initialize session state
    if "clustered_data" not in st.session_state:
        st.session_state.clustered_data = None
    if "cluster_stats" not in st.session_state:
        st.session_state.cluster_stats = None
    
    # Load and process data (cached)
    df, df_encoded, extra_cols = get_processed_data()
    
    # CRITICAL: Ensure both dataframes have same index from the start
    df = df.reset_index(drop=True)
    df_encoded = df_encoded.reset_index(drop=True)
    
    # Verify data alignment
    if len(df) != len(df_encoded):
        st.error(f"Data preprocessing issue: Original data has {len(df)} rows, encoded data has {len(df_encoded)} rows")
        st.stop()
    
    # Filters - simplified layout
    col1, col2 = st.columns(2)
    
    with col1:
        time_filter = st.multiselect(
            "Select Time of Day",
            ['Morning', 'Afternoon', 'Evening', 'Night'],
            default=['Morning', 'Afternoon', 'Evening', 'Night']
        )
    
    with col2:
        sex_filter = st.multiselect(
            "Select Victim Sex",
            ['M', 'F', 'Others'],
            default=['M', 'F', 'Others']
        )
    
    # Apply filters and get indices
    filter_mask = (
        (df['Time of Day'].isin(time_filter)) &
        (df['Vict Sex'].isin(sex_filter))
    )
    
    if not filter_mask.any():
        st.warning("No data available for selected filters.")
        return
    
    # Get filtered indices
    filtered_indices = df[filter_mask].index.tolist()
    
    # Only the View Clusters button (Clear Filters button removed)
    if st.button("View Clusters", type="primary", use_container_width=True):
        with st.spinner("Generating clusters..."):
            # Apply clustering to filtered data using indices
            clustered_data = apply_clustering_to_filtered_data(
                df, df_encoded, extra_cols, filtered_indices
            )
            
            # Store in session state
            st.session_state.clustered_data = clustered_data
            st.session_state.cluster_stats = get_cluster_summary(clustered_data)
        
        st.success("Clusters generated successfully!")
    
    # Display results if available
    if st.session_state.clustered_data is not None:
        clustered_df = st.session_state.clustered_data
        
        # Generate and display map
        st.subheader("🗺️ Crime Cluster Map")
        
        # Map generation with progress
        with st.spinner("Rendering map..."):
            m = generate_cluster_map_optimized(clustered_df)
        
        # Display map
        st_folium(m, width=900, height=600, key="cluster_map")
        
        # Legend - moved directly under map
        st.markdown("""
        <style>
        .legend {
            display: flex;
            gap: 15px;
            font-weight: bold;
            margin: 10px 0;
            justify-content: center;
        }
        .legend span {
            display: inline-block;
            padding: 8px 15px;
            border-radius: 8px;
            color: white;
            font-size: 14px;
        }
        .high { background-color: red; }
        .medium { background-color: orange; }
        .low { background-color: green; }
        </style>
        <div class="legend">
            <span class="high">🔴 High Crime Zone</span>
            <span class="medium">🟠 Medium Risk Zone</span>
            <span class="low">🟢 Low Crime Zone</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Area summary - moved under legend
        areas_by_cluster = {}
        for cluster_id in sorted(clustered_df['Cluster'].unique()):
            cluster_areas = clustered_df[clustered_df['Cluster'] == cluster_id]['AREA NAME'].value_counts().head(3).index.tolist()
            areas_by_cluster[cluster_id] = cluster_areas
        
        label_map = {0: 'High Crime Zones', 1: 'Low Crime Zones', 2: 'Medium Risk Crime Zones'}
        text_parts = []
        for c in [0, 1, 2]:
            areas = ', '.join(areas_by_cluster.get(c, []))
            text_parts.append(f"{label_map[c]} are in {areas if areas else 'N/A'}")
        
        st.markdown("**" + "; ".join(text_parts) + ".**")
        
        # Statistics - moved directly under area summary
        st.subheader("📊 Cluster Statistics")
        
        if st.session_state.cluster_stats:
            generate_cluster_stats_optimized(st.session_state.cluster_stats)

