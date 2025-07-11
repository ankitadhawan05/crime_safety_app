import joblib
import streamlit as st
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import MiniBatchKMeans

def train_and_save_model(df_encoded, features, model_path="models/kmeans_model.pkl"):
    """Train and save clustering model with optimizations"""
    # Verify all features exist
    missing_features = [f for f in features if f not in df_encoded.columns]
    if missing_features:
        raise ValueError(f"Missing features in dataframe: {missing_features}")
    
    # Ensure no NaN values in features
    feature_data = df_encoded[features].copy()
    if feature_data.isna().any().any():
        print("Warning: NaN values found in features, dropping affected rows")
        feature_data = feature_data.dropna()
    
    # DTYPE FIX: Ensure all features are float64 for consistency
    for col in features:
        feature_data[col] = feature_data[col].astype(np.float64)
    
    # Initialize and fit scaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(feature_data)
    
    # Ensure scaled data is float64
    X_scaled = X_scaled.astype(np.float64)

    # Use MiniBatchKMeans for better performance on large datasets
    kmeans = MiniBatchKMeans(
        n_clusters=3, 
        random_state=42, 
        batch_size=1024,  # Increased batch size for better performance
        n_init=3,         # Reduced n_init for faster training
        max_iter=100,     # Limit iterations
        reassignment_ratio=0.01  # Speed up convergence
    )
    
    kmeans.fit(X_scaled)

    # Create models directory if it doesn't exist
    import os
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    # Save both scaler and model as a tuple
    joblib.dump((kmeans, scaler), model_path)
    print(f"Model saved to {model_path}")
    return kmeans, scaler

@st.cache_resource
def load_clustering_model(model_path="models/kmeans_model.pkl"):
    """
    Load the saved MiniBatchKMeans model and scaler from disk.
    Returns a tuple: (kmeans_model, scaler)
    Cached for performance.
    """
    try:
        model_data = joblib.load(model_path)
        if isinstance(model_data, tuple) and len(model_data) == 2:
            model, scaler = model_data
            print(f"Model loaded from {model_path}")
            return model, scaler
        else:
            st.error(f"Invalid model format in {model_path}")
            return None, None
    except FileNotFoundError:
        st.error(f"Model file not found at {model_path}. Please train the model first.")
        return None, None
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        return None, None

@st.cache_data
def predict_clusters(_df_encoded, features, _model, _scaler):
    """
    Predict clusters for given data - cached for performance
    FIXED VERSION with proper error handling
    """
    if _model is None or _scaler is None:
        return None
    
    try:
        # Verify all features exist
        missing_features = [f for f in features if f not in _df_encoded.columns]
        if missing_features:
            st.error(f"Missing features for clustering: {missing_features}")
            return None
        
        # Get feature data and handle NaN values
        feature_data = _df_encoded[features].copy()
        
        # Check for NaN values
        if feature_data.isna().any().any():
            st.warning("NaN values detected in features, this may cause clustering errors")
            feature_data = feature_data.fillna(0)  # Fill NaN with 0 as fallback
        
        # Scale features
        X_scaled = _scaler.transform(feature_data)
        
        # Predict clusters
        clusters = _model.predict(X_scaled)
        
        return clusters
    except Exception as e:
        st.error(f"Error predicting clusters: {str(e)}")
        return None

def predict_clusters_safe(df_encoded, features, model, scaler):
    """
    Safe version of predict_clusters with extensive error handling
    """
    if model is None or scaler is None:
        print("Error: Model or scaler is None")
        return None
    
    try:
        # Ensure dataframe has proper index
        df_encoded = df_encoded.reset_index(drop=True)
        
        # Verify features exist
        missing_features = [f for f in features if f not in df_encoded.columns]
        if missing_features:
            print(f"Missing features: {missing_features}")
            return None
        
        # Extract and validate feature data
        feature_data = df_encoded[features].copy()
        
        # Handle NaN values
        nan_rows = feature_data.isna().any(axis=1)
        if nan_rows.any():
            print(f"Found {nan_rows.sum()} rows with NaN values")
            feature_data = feature_data.fillna(feature_data.mean())
        
        # DTYPE FIX: Ensure all features are float64
        for col in features:
            if not pd.api.types.is_numeric_dtype(feature_data[col]):
                print(f"Non-numeric column detected: {col}")
                feature_data[col] = pd.to_numeric(feature_data[col], errors='coerce')
            feature_data[col] = feature_data[col].astype(np.float64)
        
        # Scale features
        X_scaled = scaler.transform(feature_data)
        
        # Ensure scaled data is float64
        X_scaled = X_scaled.astype(np.float64)
        
        # Predict clusters
        clusters = model.predict(X_scaled)
        
        return clusters
        
    except Exception as e:
        print(f"Error in predict_clusters_safe: {str(e)}")
        return None

def get_cluster_centers(model, scaler, feature_names):
    """
    Get cluster centers in original feature space
    """
    if model is None or scaler is None:
        return None
    
    # Get cluster centers in scaled space
    scaled_centers = model.cluster_centers_
    
    # Transform back to original space
    original_centers = scaler.inverse_transform(scaled_centers)
    
    # Create DataFrame for easier interpretation
    centers_df = pd.DataFrame(original_centers, columns=feature_names)
    centers_df.index.name = 'Cluster'
    
    return centers_df

def evaluate_clustering_performance(X_scaled, model):
    """
    Evaluate clustering performance using various metrics
    """
    from sklearn.metrics import silhouette_score, calinski_harabasz_score
    
    if model is None:
        return None
    
    try:
        labels = model.predict(X_scaled)
        
        metrics = {
            'silhouette_score': silhouette_score(X_scaled, labels),
            'calinski_harabasz_score': calinski_harabasz_score(X_scaled, labels),
            'inertia': model.inertia_,
            'n_iter': model.n_iter_
        }
        
        return metrics
    except Exception as e:
        print(f"Error evaluating clustering: {str(e)}")
        return None

# Utility function for batch processing large datasets
def process_large_dataset_in_batches(df, model, scaler, features, batch_size=10000):
    """
    Process large datasets in batches for memory efficiency
    FIXED VERSION with proper index handling
    """
    if len(df) <= batch_size:
        return predict_clusters_safe(df, features, model, scaler)
    
    all_predictions = []
    n_batches = len(df) // batch_size + (1 if len(df) % batch_size != 0 else 0)
    
    # Reset index to ensure proper batch processing
    df = df.reset_index(drop=True)
    
    for i in range(n_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, len(df))
        
        batch_df = df.iloc[start_idx:end_idx].reset_index(drop=True)
        batch_predictions = predict_clusters_safe(batch_df, features, model, scaler)
        
        if batch_predictions is not None:
            all_predictions.extend(batch_predictions)
        else:
            # Handle error case
            all_predictions.extend([0] * len(batch_df))  # Default to cluster 0
            print(f"Error processing batch {i+1}/{n_batches}, using default cluster 0")
    
    return np.array(all_predictions)

# Function to retrain model if needed
def check_and_retrain_model(df_encoded, features, model_path="models/kmeans_model.pkl", force_retrain=False):
    """
    Check if model exists and retrain if necessary
    """
    import os
    
    if force_retrain or not os.path.exists(model_path):
        print("Training new clustering model...")
        return train_and_save_model(df_encoded, features, model_path)
    else:
        print("Loading existing model...")
        return load_clustering_model(model_path)

# Validation functions
def validate_features_for_clustering(df, features):
    """
    Validate that all required features exist and are properly formatted
    """
    errors = []
    
    # Check if all features exist
    missing_features = [f for f in features if f not in df.columns]
    if missing_features:
        errors.append(f"Missing features: {missing_features}")
    
    # Check for NaN values
    existing_features = [f for f in features if f in df.columns]
    for feature in existing_features:
        nan_count = df[feature].isna().sum()
        if nan_count > 0:
            errors.append(f"Feature '{feature}' has {nan_count} NaN values")
    
    # Check data types
    for feature in existing_features:
        if not pd.api.types.is_numeric_dtype(df[feature]):
            errors.append(f"Feature '{feature}' is not numeric: {df[feature].dtype}")
    
    return errors

def prepare_features_for_clustering(df, features):
    """
    Prepare features for clustering by handling common issues
    """
    df_clean = df.copy()
    
    # Ensure all features exist
    missing_features = [f for f in features if f not in df_clean.columns]
    if missing_features:
        raise ValueError(f"Cannot prepare missing features: {missing_features}")
    
    # Handle NaN values
    feature_data = df_clean[features].copy()
    
    # Fill NaN values with column means for numeric columns
    for col in features:
        if feature_data[col].isna().any():
            if pd.api.types.is_numeric_dtype(feature_data[col]):
                feature_data[col] = feature_data[col].fillna(feature_data[col].mean())
            else:
                feature_data[col] = pd.to_numeric(feature_data[col], errors='coerce')
                feature_data[col] = feature_data[col].fillna(feature_data[col].mean())
    
    # Update the original dataframe
    df_clean[features] = feature_data
    
    return df_clean
