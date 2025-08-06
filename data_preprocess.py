import pandas as pd
import numpy as np
import datetime
import streamlit as st
import os
from sklearn.preprocessing import StandardScaler

# --------------------------- Load Data ---------------------------
@st.cache_data
def load_crime_data():
    """Load and preprocess crime data with enhanced error handling and cloud optimization"""
    try:
        # Check if file exists
        file_path = "data/crime_data.parquet"
        if not os.path.exists(file_path):
            st.error(f"❌ Data file not found: {file_path}")
            st.error(f"Current directory: {os.getcwd()}")
            st.error(f"Directory contents: {os.listdir('.')}")
            return pd.DataFrame()
        
        # Check file size (Streamlit Cloud has memory limits) - SILENT CHECK
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        # Removed the warning message for cleaner UI
        
        # Load the parquet file
        df = pd.read_parquet(file_path)
        
        # Cloud optimization: Sample data if too large for cloud deployment - SILENT SAMPLING
        initial_size = len(df)
        if len(df) > 100000:  # Limit for cloud deployment
            # Removed: st.info(f"📊 Sampling data for cloud deployment: {len(df)} → 100000 rows")
            df = df.sample(n=100000, random_state=42)
        elif len(df) > 50000:
            # Removed: st.info(f"📊 Using subset for better performance: {len(df)} → 50000 rows")
            df = df.sample(n=50000, random_state=42)
        
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
            # Removed sidebar info message for cleaner UI
        
        # CLEAN RETURN - No verbose success messages
        return df
        
    except FileNotFoundError:
        st.error(f"❌ Data file not found: {file_path}")
        st.error("Please ensure crime_data.parquet exists in the data/ directory")
        return pd.DataFrame()
    except pd.errors.ParserError as e:
        st.error(f"❌ Error parsing parquet file: {str(e)}")
        st.error("The data file may be corrupted or in wrong format")
        return pd.DataFrame()
    except MemoryError:
        st.error("❌ Not enough memory to load the full dataset")
        st.error("Try reducing the data file size or use a smaller sample")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Unexpected error loading crime data: {str(e)}")
        st.error("Using empty DataFrame as fallback")
        
        # Debug information
        with st.expander("🔧 Debug Information"):
            st.code(f"Error type: {type(e).__name__}")
            st.code(f"Error message: {str(e)}")
            st.code(f"Current directory: {os.getcwd()}")
            if os.path.exists("data"):
                st.code(f"Data directory contents: {os.listdir('data')}")
        
        return pd.DataFrame()

def optimize_dtypes(df):
    """Optimize data types to reduce memory usage with error handling"""
    try:
        # Convert categorical columns
        categorical_cols = ['AREA NAME', 'Crm Cd Desc', 'Vict Sex']
        for col in categorical_cols:
            if col in df.columns:
                try:
                    df[col] = df[col].astype('category')
                except Exception as e:
                    print(f"Warning: Could not convert {col} to category: {e}")
        
        # DTYPE FIX: Use consistent float64 for numeric columns to avoid sklearn errors
        if 'Part 1-2' in df.columns:
            try:
                df['Part 1-2'] = pd.to_numeric(df['Part 1-2'], errors='coerce').astype(np.float64)
            except Exception as e:
                print(f"Warning: Could not convert Part 1-2 to float64: {e}")
                # Fallback: fill with default values
                df['Part 1-2'] = 1.0
        
        # Use float64 for coordinate columns to ensure consistency
        for col in ['LAT', 'LON']:
            if col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype(np.float64)
                except Exception as e:
                    print(f"Warning: Could not convert {col} to float64: {e}")
        
        return df
        
    except Exception as e:
        print(f"Error in optimize_dtypes: {e}")
        return df  # Return original dataframe if optimization fails

def add_time_of_day(df):
    """Add time of day categorization efficiently with error handling"""
    try:
        # Check if TIME OCC column exists
        if 'TIME OCC' not in df.columns:
            print("Warning: TIME OCC column not found, using default time categories")
            df['Time of Day'] = 'Unknown'
            df['Time of Day'] = df['Time of Day'].astype('category')
            return df
        
        # Convert TIME OCC to string and pad with zeros
        df['time_str'] = df['TIME OCC'].astype(str).str.zfill(4)
        
        # Extract hour more efficiently with error handling
        try:
            df['Time_occ_hour'] = df['time_str'].str[:2].astype(int)
        except ValueError:
            print("Warning: Invalid time format detected, using default hour")
            df['Time_occ_hour'] = 12  # Default to noon
        
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
        
    except Exception as e:
        print(f"Error in add_time_of_day: {e}")
        # Fallback: create default time categories
        df['Time of Day'] = 'Unknown'
        df['Time of Day'] = df['Time of Day'].astype('category')
        return df

# --------------------------- Feature Engineering ---------------------------
@st.cache_data
def preprocess_for_clustering(_df):
    """Preprocess data for clustering with caching and enhanced error handling - FIXED VERSION"""
    try:
        # CRITICAL: Work with a copy and reset index to ensure alignment
        df = _df.copy().reset_index(drop=True)
        
        # Check if dataframe is empty
        if df.empty:
            st.error("❌ Cannot preprocess empty dataframe")
            return pd.DataFrame(), []
        
        # Verify we have required columns before processing
        required_base_cols = ['LAT', 'LON', 'Part 1-2', 'Time of Day', 'Vict Sex']
        missing_cols = [col for col in required_base_cols if col not in df.columns]
        if missing_cols:
            st.error(f"❌ Missing required columns for clustering: {missing_cols}")
            # Try to create missing columns with defaults
            for col in missing_cols:
                if col == 'LAT':
                    df['LAT'] = 34.0522  # Default LA latitude
                elif col == 'LON':
                    df['LON'] = -118.2437  # Default LA longitude
                elif col == 'Part 1-2':
                    df['Part 1-2'] = 1.0
                elif col == 'Time of Day':
                    df['Time of Day'] = 'Unknown'
                elif col == 'Vict Sex':
                    df['Vict Sex'] = 'Others'
            st.warning(f"⚠️ Created default values for missing columns: {missing_cols}")
        
        # Drop rows with NaN values in required columns BEFORE encoding
        initial_len = len(df)
        df = df.dropna(subset=required_base_cols).reset_index(drop=True)
        
        if len(df) != initial_len:
            dropped_count = initial_len - len(df)
            print(f"Dropped {dropped_count} rows with missing values during preprocessing")
            # Removed verbose warning message for cleaner UI
        
        if df.empty:
            st.error("❌ No valid data remaining after cleaning")
            return pd.DataFrame(), []
        
        # Create dummy variables efficiently with consistent dtypes and error handling
        try:
            time_dummies = pd.get_dummies(df['Time of Day'], prefix='Time', dtype=np.float64)
        except Exception as e:
            print(f"Error creating time dummies: {e}")
            # Create default time dummy
            time_dummies = pd.DataFrame({'Time_Unknown': [1.0] * len(df)})
        
        try:
            sex_dummies = pd.get_dummies(df['Vict Sex'], prefix='Sex', dtype=np.float64)
        except Exception as e:
            print(f"Error creating sex dummies: {e}")
            # Create default sex dummy
            sex_dummies = pd.DataFrame({'Sex_Others': [1.0] * len(df)})
        
        # CRITICAL: Ensure all dataframes have the same index before concatenation
        df = df.reset_index(drop=True)
        time_dummies = time_dummies.reset_index(drop=True)
        sex_dummies = sex_dummies.reset_index(drop=True)
        
        # Verify lengths match before concatenation
        if not (len(df) == len(time_dummies) == len(sex_dummies)):
            min_len = min(len(df), len(time_dummies), len(sex_dummies))
            st.warning(f"⚠️ Length mismatch during encoding, truncating to {min_len}")
            df = df.iloc[:min_len].reset_index(drop=True)
            time_dummies = time_dummies.iloc[:min_len].reset_index(drop=True)
            sex_dummies = sex_dummies.iloc[:min_len].reset_index(drop=True)
        
        # Combine dataframes efficiently
        try:
            df_encoded = pd.concat([
                df,
                time_dummies,
                sex_dummies
            ], axis=1)
        except Exception as e:
            st.error(f"❌ Error combining dataframes: {e}")
            return pd.DataFrame(), []
        
        # Drop original categorical columns
        df_encoded = df_encoded.drop(columns=['Time of Day', 'Vict Sex'], errors='ignore')
        
        # Get column names for features
        extra_cols = list(time_dummies.columns) + list(sex_dummies.columns)
        
        # Ensure all required columns exist for clustering
        clustering_cols = ['LAT', 'LON', 'Part 1-2'] + extra_cols
        missing_clustering_cols = [col for col in clustering_cols if col not in df_encoded.columns]
        if missing_clustering_cols:
            st.error(f"❌ Missing clustering columns after encoding: {missing_clustering_cols}")
            return pd.DataFrame(), []
        
        # Final check: ensure no NaN values in clustering columns
        df_encoded = df_encoded.dropna(subset=clustering_cols).reset_index(drop=True)
        
        # Final optimization with error handling
        try:
            df_encoded = optimize_dtypes(df_encoded)
        except Exception as e:
            print(f"Warning: Could not optimize dtypes after encoding: {e}")
        
        # VERIFICATION: Ensure both original and encoded have same length
        if len(df) != len(df_encoded):
            print(f"WARNING: Length mismatch after encoding - Original: {len(df)}, Encoded: {len(df_encoded)}")
            # Return the encoded dataframe length-matched version of original
            df = df.iloc[:len(df_encoded)].reset_index(drop=True)
        
        # CLEAN RETURN - No verbose success messages (individual pages will show their own)
        return df_encoded, extra_cols
        
    except Exception as e:
        st.error(f"❌ Error in preprocessing for clustering: {str(e)}")
        
        # Debug information
        with st.expander("🔧 Preprocessing Debug Information"):
            st.code(f"Error type: {type(e).__name__}")
            st.code(f"Error message: {str(e)}")
            if '_df' in locals():
                st.code(f"Input dataframe shape: {_df.shape}")
                st.code(f"Input dataframe columns: {list(_df.columns)}")
        
        return pd.DataFrame(), []

# --------------------------- Additional Utility Functions ---------------------------
@st.cache_data
def get_area_coordinates(_df):
    """Get mean coordinates for each area - cached with error handling"""
    try:
        if _df.empty or 'AREA NAME' not in _df.columns:
            return {}
        
        result = _df.groupby('AREA NAME')[['LAT', 'LON']].mean().to_dict('index')
        return result
    except Exception as e:
        print(f"Error getting area coordinates: {e}")
        return {}

@st.cache_data
def get_crime_summary(_df):
    """Get summary statistics - cached with error handling"""
    try:
        if _df.empty:
            return {
                'total_crimes': 0,
                'unique_areas': 0,
                'date_range': {'start': 'N/A', 'end': 'N/A'},
                'crime_types': {},
                'gender_distribution': {},
                'time_distribution': {}
            }
        
        summary = {
            'total_crimes': len(_df),
            'unique_areas': _df['AREA NAME'].nunique() if 'AREA NAME' in _df.columns else 0,
            'date_range': {
                'start': _df['Date Rptd'].min() if 'Date Rptd' in _df.columns else 'N/A',
                'end': _df['Date Rptd'].max() if 'Date Rptd' in _df.columns else 'N/A'
            },
            'crime_types': _df['Crm Cd Desc'].value_counts().head(10).to_dict() if 'Crm Cd Desc' in _df.columns else {},
            'gender_distribution': _df['Vict Sex'].value_counts().to_dict() if 'Vict Sex' in _df.columns else {},
            'time_distribution': _df['Time of Day'].value_counts().to_dict() if 'Time of Day' in _df.columns else {}
        }
        return summary
    except Exception as e:
        print(f"Error generating crime summary: {e}")
        return {
            'total_crimes': 0,
            'unique_areas': 0,
            'date_range': {'start': 'N/A', 'end': 'N/A'},
            'crime_types': {},
            'gender_distribution': {},
            'time_distribution': {}
        }

def sample_data_for_performance(df, max_points=10000, random_state=42):
    """Sample data for better performance while maintaining representativeness with error handling"""
    try:
        if df.empty:
            return df
        
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
    except Exception as e:
        print(f"Error sampling data: {e}")
        return df  # Return original if sampling fails

# --------------------------- Validation Functions ---------------------------
def validate_data_consistency(original_df, encoded_df):
    """Validate that original and encoded dataframes are consistent with error handling"""
    try:
        errors = []
        
        if original_df.empty or encoded_df.empty:
            errors.append("One or both dataframes are empty")
            return errors
        
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
    except Exception as e:
        return [f"Error during validation: {e}"]

def fix_data_alignment(original_df, encoded_df):
    """Fix alignment issues between original and encoded dataframes with error handling"""
    try:
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
    except Exception as e:
        print(f"Error fixing data alignment: {e}")
        return original_df, encoded_df  # Return originals if fix fails

# --------------------------- Memory Management Functions ---------------------------
def check_memory_usage():
    """Check current memory usage with error handling"""
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # Removed sidebar message for cleaner UI
        return memory_mb
    except ImportError:
        print("psutil not available, cannot check memory usage")
        return None
    except Exception as e:
        print(f"Error checking memory usage: {e}")
        return None

def cleanup_large_objects():
    """Force garbage collection to free memory"""
    try:
        import gc
        gc.collect()
        print("Memory cleanup completed")
    except Exception as e:
        print(f"Error during memory cleanup: {e}")
