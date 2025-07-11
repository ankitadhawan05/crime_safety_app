import pandas as pd
import numpy as np
import datetime
import streamlit as st
from sklearn.preprocessing import StandardScaler

# --------------------------- Load Data ---------------------------
@st.cache_data
def load_crime_data():
    """Load and preprocess crime data with caching"""
    df = pd.read_parquet("data/crime_data.parquet")
    
    # Reset index to ensure clean indexing from the start
    df = df.reset_index(drop=True)
    
    # Optimize data types for memory efficiency
    df = optimize_dtypes(df)
    
    # Ensure 'Time of Day' exists by computing from 'TIME OCC'
    if 'Time of Day' not in df.columns:
        df = add_time_of_day(df)
    
    # Normalize Victim Sex
    df['Vict Sex'] = df['Vict Sex'].apply(lambda x: x if x in ['M', 'F'] else 'Others')
    df['Vict Sex'] = df['Vict Sex'].astype('category')
    
    # Drop rows with missing values in critical columns - do this efficiently
    critical_cols = ["LAT", "LON", "Part 1-2", "Time of Day", "Vict Sex", "AREA NAME"]
    initial_len = len(df)
    df = df.dropna(subset=critical_cols).reset_index(drop=True)  # Reset index after dropping
    final_len = len(df)
    
    if initial_len != final_len:
        print(f"Dropped {initial_len - final_len} rows with missing critical data")
    
    return df

def optimize_dtypes(df):
    """Optimize data types to reduce memory usage"""
    # Convert categorical columns
    categorical_cols = ['AREA NAME', 'Crm Cd Desc', 'Vict Sex']
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].astype('category')
    
    # DTYPE FIX: Use consistent float64 for numeric columns to avoid sklearn errors
    if 'Part 1-2' in df.columns:
        df['Part 1-2'] = pd.to_numeric(df['Part 1-2'], downcast='integer').astype(np.float64)
    
    # Use float64 for coordinate columns to ensure consistency
    for col in ['LAT', 'LON']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col]).astype(np.float64)
    
    return df

def add_time_of_day(df):
    """Add time of day categorization efficiently"""
    # Convert TIME OCC to string and pad with zeros
    df['time_str'] = df['TIME OCC'].astype(str).str.zfill(4)
    
    # Extract hour more efficiently
    df['Time_occ_hour'] = df['time_str'].str[:2].astype(int)
    
    # Vectorized time of day assignment
    conditions = [
        (df['Time_occ_hour'] >= 6) & (df['Time_occ_hour'] < 12),
        (df['Time_occ_hour'] >= 12) & (df['Time_occ_hour'] < 16),
        (df['Time_occ_hour'] >= 16) & (df['Time_occ_hour'] < 18)
    ]
    choices = ['Morning', 'Afternoon', 'Evening']
    df['Time of Day'] = np.select(conditions, choices, default='Night')
    df['Time of Day'] = df['Time of Day'].astype('category')
    
    # Clean up temporary columns
    df = df.drop(columns=['time_str', 'Time_occ_hour'], errors='ignore')
    
    return df

# --------------------------- Feature Engineering ---------------------------
@st.cache_data
def preprocess_for_clustering(_df):
    """Preprocess data for clustering with caching - FIXED VERSION"""
    # CRITICAL: Work with a copy and reset index to ensure alignment
    df = _df.copy().reset_index(drop=True)
    
    # Verify we have required columns before processing
    required_base_cols = ['LAT', 'LON', 'Part 1-2', 'Time of Day', 'Vict Sex']
    missing_cols = [col for col in required_base_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Drop rows with NaN values in required columns BEFORE encoding
    initial_len = len(df)
    df = df.dropna(subset=required_base_cols).reset_index(drop=True)
    
    if len(df) != initial_len:
        print(f"Dropped {initial_len - len(df)} rows with missing values during preprocessing")
    
    # Create dummy variables efficiently with consistent dtypes
    time_dummies = pd.get_dummies(df['Time of Day'], prefix='Time', dtype=np.float64)
    sex_dummies = pd.get_dummies(df['Vict Sex'], prefix='Sex', dtype=np.float64)
    
    # CRITICAL: Ensure all dataframes have the same index before concatenation
    df = df.reset_index(drop=True)
    time_dummies = time_dummies.reset_index(drop=True)
    sex_dummies = sex_dummies.reset_index(drop=True)
    
    # Verify lengths match before concatenation
    if not (len(df) == len(time_dummies) == len(sex_dummies)):
        raise ValueError(f"Length mismatch during encoding: df={len(df)}, time_dummies={len(time_dummies)}, sex_dummies={len(sex_dummies)}")
    
    # Combine dataframes efficiently
    df_encoded = pd.concat([
        df,
        time_dummies,
        sex_dummies
    ], axis=1)
    
    # Drop original categorical columns
    df_encoded = df_encoded.drop(columns=['Time of Day', 'Vict Sex'])
    
    # Get column names for features
    extra_cols = list(time_dummies.columns) + list(sex_dummies.columns)
    
    # Ensure all required columns exist for clustering
    clustering_cols = ['LAT', 'LON', 'Part 1-2'] + extra_cols
    missing_clustering_cols = [col for col in clustering_cols if col not in df_encoded.columns]
    if missing_clustering_cols:
        raise ValueError(f"Missing clustering columns: {missing_clustering_cols}")
    
    # Final check: ensure no NaN values in clustering columns
    df_encoded = df_encoded.dropna(subset=clustering_cols).reset_index(drop=True)
    
    # Final optimization
    df_encoded = optimize_dtypes(df_encoded)
    
    # VERIFICATION: Ensure both original and encoded have same length
    if len(df) != len(df_encoded):
        print(f"WARNING: Length mismatch after encoding - Original: {len(df)}, Encoded: {len(df_encoded)}")
        # Return the encoded dataframe length-matched version of original
        df = df.iloc[:len(df_encoded)].reset_index(drop=True)
    
    return df_encoded, extra_cols

# --------------------------- Additional Utility Functions ---------------------------
@st.cache_data
def get_area_coordinates(_df):
    """Get mean coordinates for each area - cached"""
    return _df.groupby('AREA NAME')[['LAT', 'LON']].mean().to_dict('index')

@st.cache_data
def get_crime_summary(_df):
    """Get summary statistics - cached"""
    summary = {
        'total_crimes': len(_df),
        'unique_areas': _df['AREA NAME'].nunique(),
        'date_range': {
            'start': _df['Date Rptd'].min() if 'Date Rptd' in _df.columns else 'N/A',
            'end': _df['Date Rptd'].max() if 'Date Rptd' in _df.columns else 'N/A'
        },
        'crime_types': _df['Crm Cd Desc'].value_counts().head(10).to_dict() if 'Crm Cd Desc' in _df.columns else {},
        'gender_distribution': _df['Vict Sex'].value_counts().to_dict(),
        'time_distribution': _df['Time of Day'].value_counts().to_dict()
    }
    return summary

def sample_data_for_performance(df, max_points=10000, random_state=42):
    """Sample data for better performance while maintaining representativeness"""
    if len(df) <= max_points:
        return df
    
    # Stratified sampling to maintain cluster distribution if clusters exist
    if 'Cluster' in df.columns:
        # Sample proportionally from each cluster
        sampled_parts = []
        for cluster in df['Cluster'].unique():
            cluster_data = df[df['Cluster'] == cluster]
            n_samples = max(1, int(len(cluster_data) * max_points / len(df)))
            if len(cluster_data) > n_samples:
                sampled_parts.append(cluster_data.sample(n=n_samples, random_state=random_state))
            else:
                sampled_parts.append(cluster_data)
        
        return pd.concat(sampled_parts, ignore_index=True)
    else:
        # Simple random sampling
        return df.sample(n=max_points, random_state=random_state)

# --------------------------- Validation Functions ---------------------------
def validate_data_consistency(original_df, encoded_df):
    """Validate that original and encoded dataframes are consistent"""
    errors = []
    
    # Check lengths
    if len(original_df) != len(encoded_df):
        errors.append(f"Length mismatch: Original={len(original_df)}, Encoded={len(encoded_df)}")
    
    # Check for NaN values in critical columns
    critical_cols = ['LAT', 'LON', 'Part 1-2']
    for col in critical_cols:
        if col in original_df.columns and original_df[col].isna().any():
            errors.append(f"NaN values found in original dataframe column: {col}")
        if col in encoded_df.columns and encoded_df[col].isna().any():
            errors.append(f"NaN values found in encoded dataframe column: {col}")
    
    return errors

def fix_data_alignment(original_df, encoded_df):
    """Fix alignment issues between original and encoded dataframes"""
    # Reset indices
    original_df = original_df.reset_index(drop=True)
    encoded_df = encoded_df.reset_index(drop=True)
    
    # Get minimum length
    min_len = min(len(original_df), len(encoded_df))
    
    # Truncate both to minimum length
    if len(original_df) != len(encoded_df):
        print(f"Fixing alignment: truncating to {min_len} rows")
        original_df = original_df.iloc[:min_len].reset_index(drop=True)
        encoded_df = encoded_df.iloc[:min_len].reset_index(drop=True)
    
    return original_df, encoded_df