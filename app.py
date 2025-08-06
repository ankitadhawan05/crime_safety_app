import streamlit as st
import pandas as pd
import os
import sys
import traceback

st.set_page_config(page_title="🔧 Debug: Crime Safety App", layout="wide")

st.title("🔧 Debug: Crime Safety Travel Assistant")
st.markdown("**This is a diagnostic version to identify deployment issues**")

# Add current directory to Python path
sys.path.append(os.path.dirname(__file__))

# Create tabs for organized testing
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔧 System Info", "📊 Data Test", "🤖 Model Test", "📦 Import Test", "🚀 Module Test"])

with tab1:
    st.header("🔧 System Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**System Details:**")
        st.code(f"Python version: {sys.version}")
        st.code(f"Current directory: {os.getcwd()}")
        st.code(f"Python path: {sys.path[:3]}...")  # Show first 3 entries
        
    with col2:
        st.write("**Directory Structure:**")
        try:
            files = os.listdir('.')
            st.code(f"Root files: {files}")
            
            if 'data' in files:
                data_files = os.listdir('data')
                st.code(f"Data directory: {data_files}")
            else:
                st.error("❌ No 'data' directory found")
                
            if 'models' in files:
                model_files = os.listdir('models')
                st.code(f"Models directory: {model_files}")
            else:
                st.error("❌ No 'models' directory found")
                
        except Exception as e:
            st.error(f"Error reading directories: {e}")

with tab2:
    st.header("📊 Data Loading Test")
    
    # Test 1: Check if data file exists
    st.subheader("1. File Existence Check")
    data_path = "data/crime_data.parquet"
    
    if os.path.exists(data_path):
        file_size = os.path.getsize(data_path) / (1024 * 1024)
        st.success(f"✅ Data file found: {file_size:.1f} MB")
        
        # Test 2: Try loading a small sample
        st.subheader("2. Sample Data Loading")
        try:
            # Read just the first 1000 rows for testing
            df_sample = pd.read_parquet(data_path)
            if len(df_sample) > 1000:
                df_sample = df_sample.head(1000)
                
            st.success(f"✅ Sample data loaded: {len(df_sample)} rows, {len(df_sample.columns)} columns")
            st.write("**Columns:**", list(df_sample.columns))
            st.write("**Sample data:**")
            st.dataframe(df_sample.head(3))
            
            # Test 3: Check for required columns
            st.subheader("3. Required Columns Check")
            required_cols = ["LAT", "LON", "AREA NAME", "TIME OCC", "Vict Sex", "Part 1-2"]
            missing_cols = [col for col in required_cols if col not in df_sample.columns]
            
            if missing_cols:
                st.error(f"❌ Missing required columns: {missing_cols}")
            else:
                st.success("✅ All required columns present")
                
            # Test 4: Check data quality
            st.subheader("4. Data Quality Check")
            null_counts = df_sample[required_cols].isnull().sum()
            if null_counts.sum() > 0:
                st.warning(f"⚠️ Null values found:\n{null_counts[null_counts > 0]}")
            else:
                st.success("✅ No null values in required columns")
                
        except Exception as e:
            st.error(f"❌ Error loading sample data: {e}")
            st.code(traceback.format_exc())
    else:
        st.error(f"❌ Data file not found: {data_path}")

with tab3:
    st.header("🤖 Model Loading Test")
    
    # Test 1: Check if model file exists
    st.subheader("1. Model File Check")
    model_path = "models/kmeans_model.pkl"
    
    if os.path.exists(model_path):
        file_size = os.path.getsize(model_path) / (1024 * 1024)
        st.success(f"✅ Model file found: {file_size:.1f} MB")
        
        # Test 2: Try loading the model
        st.subheader("2. Model Loading Test")
        try:
            import joblib
            
            model_data = joblib.load(model_path)
            if isinstance(model_data, tuple) and len(model_data) == 2:
                model, scaler = model_data
                st.success("✅ Model and scaler loaded successfully")
                st.write(f"**Model type:** {type(model).__name__}")
                st.write(f"**Scaler type:** {type(scaler).__name__}")
                
                # Check model properties
                if hasattr(model, 'n_clusters'):
                    st.write(f"**Number of clusters:** {model.n_clusters}")
                if hasattr(model, 'cluster_centers_'):
                    st.write(f"**Cluster centers shape:** {model.cluster_centers_.shape}")
                    
            else:
                st.warning("⚠️ Model file format may be incorrect")
                st.write(f"**Loaded object type:** {type(model_data)}")
                
        except ImportError as e:
            st.error(f"❌ Missing required library: {e}")
        except Exception as e:
            st.error(f"❌ Error loading model: {e}")
            st.code(traceback.format_exc())
    else:
        st.error(f"❌ Model file not found: {model_path}")

with tab4:
    st.header("📦 Import Test")
    
    # Test basic imports first
    st.subheader("1. Basic Package Imports")
    
    packages = [
        ('numpy', 'np'),
        ('pandas', 'pd'), 
        ('sklearn', None),
        ('joblib', None),
        ('folium', None),
        ('plotly', None),
        ('geopandas', 'gpd'),
        ('streamlit_folium', None)
    ]
    
    for package, alias in packages:
        try:
            if alias:
                exec(f"import {package} as {alias}")
            else:
                exec(f"import {package}")
            st.success(f"✅ {package}")
        except ImportError as e:
            st.error(f"❌ {package}: {e}")
        except Exception as e:
            st.warning(f"⚠️ {package}: {e}")

with tab5:
    st.header("🚀 Module Import Test")
    
    # Test your custom modules
    st.subheader("1. Custom Module Imports")
    
    modules_to_test = [
        'data_preprocess',
        'clustering_engine', 
        'clustering',
        'forecast',
        'free_api_utils',
        'crime_alerts'
    ]
    
    module_status = {}
    
    for module_name in modules_to_test:
        try:
            module = __import__(module_name)
            st.success(f"✅ {module_name} imported successfully")
            module_status[module_name] = "success"
            
            # Try to get module attributes
            attrs = [attr for attr in dir(module) if not attr.startswith('_')]
            if attrs:
                st.write(f"   **Functions:** {attrs[:5]}")  # Show first 5 functions
                
        except ImportError as e:
            st.error(f"❌ {module_name}: Import Error - {e}")
            module_status[module_name] = f"import_error: {e}"
        except Exception as e:
            st.error(f"❌ {module_name}: Other Error - {e}")
            module_status[module_name] = f"other_error: {e}"
    
    # Test specific functions if modules loaded successfully
    st.subheader("2. Function Test")
    
    if module_status.get('data_preprocess') == "success":
        try:
            from data_preprocess import load_crime_data
            st.success("✅ load_crime_data function imported")
            
            # Try calling the function
            with st.spinner("Testing data loading..."):
                df = load_crime_data()
                if not df.empty:
                    st.success(f"✅ Data loaded successfully: {len(df)} rows")
                else:
                    st.warning("⚠️ Empty dataframe returned")
        except Exception as e:
            st.error(f"❌ Error testing load_crime_data: {e}")
            st.code(traceback.format_exc())
    
    if module_status.get('clustering_engine') == "success":
        try:
            from clustering_engine import load_clustering_model
            st.success("✅ load_clustering_model function imported")
            
            # Try calling the function
            model, scaler = load_clustering_model()
            if model is not None and scaler is not None:
                st.success("✅ Clustering model loaded successfully")
            else:
                st.warning("⚠️ Model loading returned None")
        except Exception as e:
            st.error(f"❌ Error testing load_clustering_model: {e}")
            st.code(traceback.format_exc())

# Memory check at the end
st.markdown("---")
st.subheader("💾 Memory Status")

try:
    import psutil
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    st.info(f"Current memory usage: {memory_mb:.1f} MB")
    
    if memory_mb > 500:  # Streamlit Cloud free tier limit
        st.warning("⚠️ High memory usage detected - may cause deployment issues")
    else:
        st.success("✅ Memory usage within normal limits")
        
except ImportError:
    st.info("psutil not available - cannot check memory usage")
except Exception as e:
    st.warning(f"Could not check memory: {e}")

# Final status summary
st.markdown("---")
st.subheader("📋 Deployment Readiness Summary")

col1, col2 = st.columns(2)

with col1:
    st.write("**✅ Working Components:**")
    if os.path.exists("data/crime_data.parquet"):
        st.write("- Data file exists")
    if os.path.exists("models/kmeans_model.pkl"):
        st.write("- Model file exists")
    
    working_modules = [k for k, v in module_status.items() if v == "success"]
    for module in working_modules:
        st.write(f"- {module} module")

with col2:
    st.write("**❌ Issues Found:**")
    if not os.path.exists("data/crime_data.parquet"):
        st.write("- Missing data file")
    if not os.path.exists("models/kmeans_model.pkl"):
        st.write("- Missing model file")
        
    failed_modules = [k for k, v in module_status.items() if v != "success"]
    for module in failed_modules:
        st.write(f"- {module} module: {module_status[module]}")

st.markdown("**🎯 Next Steps:** Fix the issues shown above, then restore your original app.py")
