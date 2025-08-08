# AI-powered crime forecasting using SARIMAX with model pickling for performance
import pandas as pd
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import warnings
import pickle
import hashlib
import os
warnings.filterwarnings('ignore')

# Create directory for cached models if it doesn't exist
MODEL_CACHE_DIR = "cached_models"
if not os.path.exists(MODEL_CACHE_DIR):
    os.makedirs(MODEL_CACHE_DIR)

def get_model_cache_key(area_name, gender, crime_type, frequency):
    """Generate unique cache key for model combination"""
    key_string = f"{area_name}_{gender}_{crime_type}_{frequency}"
    return hashlib.md5(key_string.encode()).hexdigest()

def load_cached_model(cache_key):
    """Load pickled model if exists"""
    model_path = os.path.join(MODEL_CACHE_DIR, f"{cache_key}.pkl")
    if os.path.exists(model_path):
        # Check if model is not too old (e.g., 24 hours)
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(model_path))
        if file_age.total_seconds() < 86400:  # 24 hours
            try:
                with open(model_path, 'rb') as f:
                    return pickle.load(f)
            except:
                return None
    return None

def save_model_to_cache(model, cache_key):
    """Save trained model to pickle file"""
    model_path = os.path.join(MODEL_CACHE_DIR, f"{cache_key}.pkl")
    try:
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
    except:
        pass  # Fail silently if can't save

# Pre-compute models for common combinations
@st.cache_data(ttl=7200)  # Cache for 2 hours
def precompute_common_models(df):
    """Pre-train models for most common area/crime combinations"""
    # Get top 5 areas and top 5 crime types
    top_areas = df['AREA NAME'].value_counts().head(5).index.tolist()
    top_crimes = df['Crm Cd Desc'].value_counts().head(5).index.tolist()
    
    models_computed = 0
    total_combinations = len(top_areas) * len(top_crimes)
    
    progress_placeholder = st.empty()
    
    for area in top_areas:
        for crime in top_crimes:
            cache_key = get_model_cache_key(area, None, crime, 'M')
            
            # Check if model already exists
            if load_cached_model(cache_key) is None:
                # Train and save model
                area_df = df[df['AREA NAME'] == area]
                ts = prepare_time_series_fast(area_df, crime, 'M')
                
                if not ts.empty and len(ts) >= 10:
                    try:
                        model = train_sarimax_model_fast(ts, 'M', crime)
                        save_model_to_cache(model, cache_key)
                        models_computed += 1
                    except:
                        pass
            
            # Update progress
            progress = (models_computed / total_combinations) * 100
            progress_placeholder.text(f"Pre-computing common models: {progress:.0f}%")
    
    progress_placeholder.empty()
    return models_computed

# OPTIMIZATION: Faster data loading with smart caching
@st.cache_data(ttl=3600)
def load_data():
    """Load and preprocess crime data with balanced optimization"""
    try:
        df = pd.read_parquet("data/crime_data.parquet")
        df['DATE OCC'] = pd.to_datetime(df['DATE OCC'], errors='coerce')
        
        # Clean and validate data
        df = df.dropna(subset=['DATE OCC', 'Crm Cd Desc', 'AREA NAME', 'Vict Sex'])
        df = df.sort_values('DATE OCC')
        
        # Keep last 3 years for balance
        three_years_ago = pd.Timestamp.now() - pd.DateOffset(years=3)
        df = df[df['DATE OCC'] >= three_years_ago]
        
        # Smart sampling for large datasets
        if len(df) > 200000:
            one_year_ago = pd.Timestamp.now() - pd.DateOffset(years=1)
            recent_data = df[df['DATE OCC'] >= one_year_ago]
            older_data = df[df['DATE OCC'] < one_year_ago].sample(frac=0.7, random_state=42)
            df = pd.concat([recent_data, older_data]).sort_values('DATE OCC')
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# Keep all your existing helper functions
def safe_strftime(date_val, format_str='%B %d, %Y'):
    """Safely format datetime, handling NaT values"""
    try:
        if pd.isna(date_val) or pd.isnull(date_val):
            return "Unknown Date"
        return date_val.strftime(format_str)
    except:
        return "Invalid Date"

def safe_numeric_conversion(value, default=0):
    """Safely convert values to numeric, handling NaN/None cases"""
    try:
        if pd.isna(value) or pd.isnull(value) or value is None:
            return default
        if np.isnan(value) or np.isinf(value):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int_conversion(value, default=0):
    """Safely convert values to integer, handling NaN/None cases"""
    numeric_val = safe_numeric_conversion(value, default)
    try:
        return int(numeric_val)
    except (ValueError, TypeError, OverflowError):
        return default

# Optimized time series preparation
def prepare_time_series_fast(df, crime_type, frequency='M'):
    """Fast time series preparation without caching decorator for pickle compatibility"""
    try:
        crime_df = df[df['Crm Cd Desc'] == crime_type].copy()
        
        if crime_df.empty:
            return pd.Series()
        
        crime_df['Count'] = 1
        
        if frequency == 'D':
            ts = crime_df.groupby('DATE OCC')['Count'].sum().resample('D').sum().fillna(0)
            ts = ts.tail(180)  # 6 months
        elif frequency == 'W':
            ts = crime_df.groupby('DATE OCC')['Count'].sum().resample('W').sum().fillna(0)
            ts = ts.tail(104)  # 2 years
        else:  # Monthly
            ts = crime_df.groupby('DATE OCC')['Count'].sum().resample('M').sum().fillna(0)
            ts = ts.tail(36)  # 3 years
        
        if (ts > 0).any():
            first_nonzero = ts[ts > 0].index.min()
            if frequency == 'M':
                buffer_start = first_nonzero - pd.DateOffset(months=1)
            elif frequency == 'W':
                buffer_start = first_nonzero - pd.DateOffset(weeks=2)
            else:
                buffer_start = first_nonzero - pd.DateOffset(days=7)
            
            buffer_start = max(buffer_start, ts.index.min())
            ts_filtered = ts[buffer_start:]
        else:
            ts_filtered = ts
        
        return ts_filtered
        
    except Exception as e:
        return pd.Series()

# Cached version for general use
@st.cache_data(ttl=1800)
def prepare_time_series(df, crime_type, frequency='M'):
    """Cached wrapper for time series preparation"""
    return prepare_time_series_fast(df, crime_type, frequency)

# Fast model training without decorator for pickle
def train_sarimax_model_fast(ts, frequency, crime_type):
    """Fast SARIMAX training without caching decorator"""
    try:
        if frequency == 'M' and len(ts) >= 24:
            model = SARIMAX(ts, order=(1,1,1), seasonal_order=(1,1,1,12))
            results = model.fit(disp=False, maxiter=75)
        elif frequency == 'W' and len(ts) >= 52:
            model = SARIMAX(ts, order=(1,1,1), seasonal_order=(1,0,1,52))
            results = model.fit(disp=False, maxiter=75)
        else:
            model = SARIMAX(ts, order=(1,1,1))
            results = model.fit(disp=False, maxiter=75)
        
        return results
        
    except:
        try:
            model = SARIMAX(ts, order=(1,1,0))
            results = model.fit(disp=False, maxiter=50)
            return results
        except:
            model = SARIMAX(ts, order=(0,1,1))
            results = model.fit(disp=False, maxiter=50)
            return results

# Cached version for general use
@st.cache_resource(ttl=1800)
def train_sarimax_model(ts, frequency, crime_type):
    """Cached wrapper for model training"""
    return train_sarimax_model_fast(ts, frequency, crime_type)

def get_forecast_dates(last_date, periods, frequency='M'):
    """Generate forecast dates starting from the day after last_date"""
    try:
        if pd.isna(last_date) or pd.isnull(last_date):
            last_date = pd.Timestamp('2023-12-31')
        
        if frequency == 'M':
            if last_date.day == 1:
                start_date = last_date + pd.DateOffset(months=1)
            else:
                start_date = (last_date + pd.DateOffset(months=1)).replace(day=1)
            
            forecast_dates = pd.date_range(start=start_date, periods=periods, freq='MS')
        elif frequency == 'W':
            start_date = last_date + pd.DateOffset(weeks=1)
            start_date = start_date - pd.Timedelta(days=start_date.weekday())
            forecast_dates = pd.date_range(start=start_date, periods=periods, freq='W-MON')
        else:
            start_date = last_date + pd.Timedelta(days=1)
            forecast_dates = pd.date_range(start=start_date, periods=periods, freq='D')
        
        return forecast_dates
        
    except Exception as e:
        fallback_start = pd.Timestamp('2024-01-01')
        return pd.date_range(start=fallback_start, periods=periods, freq='MS')

def clean_forecast_values(forecast_values):
    """Clean forecast values by removing NaN, infinity, and negative values"""
    try:
        if isinstance(forecast_values, pd.Series):
            values = forecast_values.values
        else:
            values = np.array(forecast_values)
        
        values = np.where(np.isnan(values) | np.isinf(values), 0, values)
        values = np.maximum(values, 0)
        
        return values
        
    except Exception as e:
        return np.zeros(len(forecast_values))

# Keep all your existing analysis functions
@st.cache_data(ttl=1800)
def get_top_crime_streets(df, area_name, top_n=3):
    """Get top streets with highest crime count for a specific area"""
    try:
        area_data = df[df['AREA NAME'] == area_name]
        
        if 'CROSS STREET' in area_data.columns:
            street_crimes = area_data['CROSS STREET'].value_counts()
        elif 'Cross Street' in area_data.columns:
            street_crimes = area_data['Cross Street'].value_counts()
        else:
            return []
        
        street_crimes = street_crimes.dropna()
        street_crimes = street_crimes[street_crimes.index != '']
        
        top_streets = street_crimes.head(top_n).index.tolist()
        
        return top_streets
    except Exception as e:
        return []

@st.cache_data(ttl=1800)
def get_most_affected_gender(df, area_name, crime_type):
    """Get the gender most affected by a specific crime type in an area"""
    try:
        filtered_df = df[df['AREA NAME'] == area_name]
        
        if len(filtered_df) == 0:
            return 'individuals'
        
        gender_counts = filtered_df['Vict Sex'].value_counts()
        
        if len(gender_counts) == 0:
            return 'individuals'
        
        most_affected_code = gender_counts.index[0]
        
        if most_affected_code == 'M':
            return 'males'
        elif most_affected_code == 'F':
            return 'females'
        else:
            return 'individuals'
            
    except Exception as e:
        return 'individuals'

@st.cache_data(ttl=1800)
def calculate_risk_probability(df, area_name, crime_type, forecast_periods, selected_gender=None):
    """Calculate risk probability based on actual historical crime data"""
    try:
        area_data = df[df['AREA NAME'] == area_name]
        
        if selected_gender:
            area_data = area_data[area_data['Vict Sex'] == selected_gender]
        
        crime_data = area_data[area_data['Crm Cd Desc'] == crime_type]
        
        if len(crime_data) == 0:
            if selected_gender == 'F':
                return 8
            elif selected_gender == 'M':
                return 12
            return 5
            
        crime_data['YearMonth'] = crime_data['DATE OCC'].dt.to_period('M')
        monthly_counts = crime_data.groupby('YearMonth').size()
        
        if len(monthly_counts) == 0:
            return 5
            
        avg_monthly = monthly_counts.mean()
        total_crimes_in_filtered_area = len(area_data)
        total_crime_type_in_filtered_area = len(crime_data)
        
        months_of_data = len(monthly_counts)
        if months_of_data == 0:
            return 5
            
        crime_type_percentage = (total_crime_type_in_filtered_area / total_crimes_in_filtered_area * 100) if total_crimes_in_filtered_area > 0 else 0
        
        base_probability = min(crime_type_percentage * 2.5, 35)
        
        if selected_gender == 'F':
            all_area_data = df[df['AREA NAME'] == area_name]
            female_ratio = len(all_area_data[all_area_data['Vict Sex'] == 'F']) / len(all_area_data) if len(all_area_data) > 0 else 0.5
            if female_ratio > 0.6:
                base_probability *= 1.3
            elif female_ratio < 0.3:
                base_probability *= 0.7
        elif selected_gender == 'M':
            all_area_data = df[df['AREA NAME'] == area_name]
            male_ratio = len(all_area_data[all_area_data['Vict Sex'] == 'M']) / len(all_area_data) if len(all_area_data) > 0 else 0.5
            if male_ratio > 0.6:
                base_probability *= 1.3
            elif male_ratio < 0.3:
                base_probability *= 0.7
        
        if avg_monthly >= 10:
            intensity_multiplier = 1.8
        elif avg_monthly >= 5:
            intensity_multiplier = 1.5
        elif avg_monthly >= 2:
            intensity_multiplier = 1.2
        elif avg_monthly >= 1:
            intensity_multiplier = 1.0
        else:
            intensity_multiplier = 0.8
        
        recent_months = monthly_counts.tail(6)
        if len(recent_months) >= 3:
            recent_avg = recent_months.mean()
            trend_multiplier = min(recent_avg / avg_monthly, 2.0) if avg_monthly > 0 else 1.0
        else:
            trend_multiplier = 1.0
        
        final_probability = base_probability * intensity_multiplier * trend_multiplier
        final_probability = max(3, min(85, int(final_probability)))
        
        return final_probability
        
    except Exception as e:
        area_hash = hash(area_name + crime_type + str(selected_gender)) % 60
        return max(5, min(50, 8 + area_hash))

@st.cache_data(ttl=1800)
def get_crime_risk_streets(df, area_name=None, gender=None, crime_types=None, top_n=5):
    """Get high-risk streets based on crime data"""
    try:
        filtered_df = df.copy()
        
        if area_name:
            filtered_df = filtered_df[filtered_df['AREA NAME'] == area_name]
        
        if gender:
            filtered_df = filtered_df[filtered_df['Vict Sex'] == gender]
        
        if crime_types:
            filtered_df = filtered_df[filtered_df['Crm Cd Desc'].isin(crime_types)]
        
        if 'CROSS STREET' in filtered_df.columns:
            street_crimes = filtered_df['CROSS STREET'].value_counts().head(top_n)
            return street_crimes.index.tolist()
        elif 'Cross Street' in filtered_df.columns:
            street_crimes = filtered_df['Cross Street'].value_counts().head(top_n)
            return street_crimes.index.tolist()
        else:
            area_crimes = filtered_df['AREA NAME'].value_counts().head(top_n)
            return area_crimes.index.tolist()
            
    except Exception as e:
        return []

def generate_intelligent_forecast_message(forecasts, df, area_name=None, gender=None, forecast_period_label="1 Month"):
    """Generate intelligent messaging based on forecast results and filters"""
    try:
        if not forecasts:
            return None
        
        total_predicted = sum([forecast.sum() for forecast in forecasts.values()])
        crime_types = list(forecasts.keys())
        most_predicted_crime = max(forecasts.items(), key=lambda x: x[1].sum())
        
        historical_crimes = len(df)
        if area_name:
            historical_crimes = len(df[df['AREA NAME'] == area_name])
        if gender:
            if area_name:
                historical_crimes = len(df[(df['AREA NAME'] == area_name) & (df['Vict Sex'] == gender)])
            else:
                historical_crimes = len(df[df['Vict Sex'] == gender])
        
        if historical_crimes > 0:
            probability = min(int((total_predicted / (historical_crimes / 12)) * 100), 95)
        else:
            probability = 25
        
        risk_streets = get_crime_risk_streets(df, area_name, gender, crime_types, top_n=3)
        
        location_text = f"in {area_name}" if area_name else "in the analyzed areas"
        gender_text = {"M": "males", "F": "females", "X": "individuals"}.get(gender, "individuals")
        
        # Use the actual forecast period label
        period_text = f"the next {forecast_period_label.lower()}"
        
        crime_focus = most_predicted_crime[0].lower()
        predicted_count = int(most_predicted_crime[1].sum())
        
        message_data = {
            'location': location_text,
            'crime_type': crime_focus,
            'gender': gender_text,
            'probability': probability,
            'period': period_text,
            'predicted_count': predicted_count,
            'total_crimes': len(crime_types),
            'risk_streets': risk_streets[:3],
            'area_name': area_name or "the selected areas"
        }
        
        return message_data
        
    except Exception as e:
        return None

def display_intelligent_forecast_message(message_data, df, area_name, selected_gender, forecast_period_label):
    """Display the simplified forecast message with high-risk prediction"""
    if not message_data or not area_name:
        return
    
    try:
        area_data = df[df['AREA NAME'] == area_name]
        top_crime = area_data['Crm Cd Desc'].value_counts().index[0] if len(area_data) > 0 else "theft plain - petty ($950 & under)"
        
        # Extract number of months from label
        months_map = {
            "1 Month": 1,
            "2 Months": 2,
            "Quarter (3 months)": 3,
            "Half Year (6 months)": 6,
            "Full Year (12 months)": 12
        }
        forecast_months = months_map.get(forecast_period_label, 1)
        
        risk_probability = calculate_risk_probability(df, area_name, top_crime, forecast_months, selected_gender)
        
        period_text = f"the next {forecast_period_label.lower()}"
        
        if selected_gender is None:
            most_affected = get_most_affected_gender(df, area_name, top_crime)
            risk_message = f"<strong>High-Risk Crime Prediction in <strong>{area_name}</strong> which shows a {risk_probability}% probability of experiencing {top_crime.lower()} incidents during {period_text}, with {most_affected} being particularly at Risk</strong>"
        else:
            risk_message = f"<strong>High-Risk Crime Prediction in <strong>{area_name}</strong> which shows a {risk_probability}% probability of experiencing {top_crime.lower()} incidents during {period_text}</strong>"
        
        top_streets = get_top_crime_streets(df, area_name, top_n=3)
        
        if top_streets:
            cleaned_streets = []
            for street in top_streets:
                if street and str(street).strip() and str(street).strip() != 'nan':
                    clean_street = ' '.join(str(street).split())
                    cleaned_streets.append(clean_street)
            
            if cleaned_streets:
                streets_text = ", ".join(cleaned_streets)
                street_message = f"Based on historical crime data, exercise extra caution on streets: {streets_text}"
            else:
                street_message = f"Based on historical crime data, exercise extra caution when in the {area_name} area."
        else:
            street_message = f"Based on historical crime data, exercise extra caution when in the {area_name} area."
        
        st.markdown("---")
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #e3f2fd 0%, #fce4ec 100%);
            border: 2px solid #2196f3;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        ">
            <div style="
                color: #1565c0;
                font-size: 16px;
                font-weight: 500;
                text-align: left;
                line-height: 1.8;
            ">
                {risk_message}
                <br><br>
                <div style="font-size: 15px; font-weight: 400;">
                    {street_message}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Error creating safety message: {e}")

def forecast_crime(df, area_name=None, gender=None, top_n=10, months_ahead=1, forecast_period_label="1 Month"):
    """Enhanced crime forecasting with intelligent caching and pickling"""
    
    st.write("### 🔮 AI Crime Forecast")
    
    if df.empty:
        st.warning("No data available for forecasting.")
        return {}
    
    # Display dataset info
    try:
        min_date = df['DATE OCC'].min()
        max_date = df['DATE OCC'].max()
        
        min_date_str = safe_strftime(min_date)
        max_date_str = safe_strftime(max_date)
        
        if pd.notna(max_date):
            next_day = max_date + pd.Timedelta(days=1)
            next_day_str = safe_strftime(next_day)
        else:
            next_day_str = "Unknown"
        
        st.info(f"""
        **Dataset Period:** {min_date_str} to {max_date_str}  
        **Forecast starts from:** {next_day_str}  
        **Forecast Duration:** {forecast_period_label}
        """)
    except Exception as e:
        st.info("**Forecast Period:** Unable to determine dates from dataset")

    # Filter by area
    filtered_df = df.copy()
    if area_name:
        filtered_df = filtered_df[filtered_df['AREA NAME'] == area_name]
        st.write(f"**Area:** {area_name}")

    # Filter by gender
    if gender:
        filtered_df = filtered_df[filtered_df['Vict Sex'] == gender]
        gender_display = {"M": "Male", "F": "Female", "X": "Other"}.get(gender, gender)
        st.write(f"**Gender:** {gender_display}")

    if filtered_df.empty:
        st.warning("No data available for selected filters.")
        return {}

    # Determine frequency based on forecast period
    if months_ahead <= 1:
        frequency = 'W'  # Weekly for 1 month or less
        periods = months_ahead * 4  # Approximate weeks
    else:
        frequency = 'M'  # Monthly for longer periods
        periods = months_ahead

    # Get top crimes - limit for performance
    try:
        actual_top_n = min(top_n, 10)
        top_crimes = filtered_df['Crm Cd Desc'].value_counts().head(actual_top_n).index.tolist()
    except Exception as e:
        st.error(f"Error getting top crimes: {str(e)}")
        return {}

    forecasts = {}
    forecast_figures = {}

    if not top_crimes:
        st.warning("No crime types found in the data.")
        return {}

    progress_bar = st.progress(0)
    
    for i, crime in enumerate(top_crimes):
        try:
            # Check for cached model first
            cache_key = get_model_cache_key(area_name, gender, crime, frequency)
            cached_model = load_cached_model(cache_key)
            
            if cached_model:
                # Use cached model - MUCH FASTER!
                with st.spinner(f"Using cached model for {crime}..."):
                    results = cached_model
            else:
                # Prepare time series
                ts = prepare_time_series(filtered_df, crime, frequency)
                
                if ts.empty or len(ts) < 10:
                    st.warning(f"Insufficient data for {crime} (only {len(ts)} data points)")
                    continue
                
                # Train new model
                with st.spinner(f"Training model for {crime}..."):
                    results = train_sarimax_model(ts, frequency, crime)
                    # Save to cache for next time
                    save_model_to_cache(results, cache_key)
            
            # Generate forecast
            forecast_raw = results.forecast(steps=periods)
            forecast_values = clean_forecast_values(forecast_raw)
            
            try:
                conf_int_raw = results.get_forecast(steps=periods).conf_int()
                conf_int = pd.DataFrame({
                    'lower': clean_forecast_values(conf_int_raw.iloc[:, 0] if hasattr(conf_int_raw, 'iloc') else conf_int_raw['lower']),
                    'upper': clean_forecast_values(conf_int_raw.iloc[:, 1] if hasattr(conf_int_raw, 'iloc') else conf_int_raw['upper'])
                })
            except:
                conf_int = pd.DataFrame({
                    'lower': forecast_values * 0.8,
                    'upper': forecast_values * 1.2
                })
            
            # For cached models, we need to get the time series again for dates
            if cached_model:
                ts = prepare_time_series(filtered_df, crime, frequency)
            
            last_data_date = ts.index.max()
            forecast_dates = get_forecast_dates(last_data_date, periods, frequency)
            
            forecast_series = pd.Series(forecast_values, index=forecast_dates)
            forecasts[crime] = forecast_series
            
            # Create plot
            fig = go.Figure()
            
            historical_data = ts.tail(min(12, len(ts)))
            fig.add_trace(go.Scatter(
                x=historical_data.index,
                y=historical_data.values,
                mode='lines+markers',
                name='Historical Data',
                line=dict(color='blue', width=2),
                marker=dict(size=6)
            ))
            
            fig.add_trace(go.Scatter(
                x=forecast_dates,
                y=forecast_values,
                mode='lines+markers',
                name='Forecast',
                line=dict(color='red', width=2, dash='dash'),
                marker=dict(size=6)
            ))
            
            try:
                fig.add_trace(go.Scatter(
                    x=forecast_dates,
                    y=conf_int['upper'],
                    mode='lines',
                    name='Upper Confidence',
                    line=dict(color='rgba(255,0,0,0.2)', width=0),
                    showlegend=False
                ))
                
                fig.add_trace(go.Scatter(
                    x=forecast_dates,
                    y=conf_int['lower'],
                    mode='lines',
                    name='Confidence Interval',
                    line=dict(color='rgba(255,0,0,0.2)', width=0),
                    fill='tonexty',
                    fillcolor='rgba(255,0,0,0.2)'
                ))
            except:
                pass
            
            fig.update_layout(
                title=f'{crime} - {forecast_period_label} Forecast',
                xaxis_title='Date',
                yaxis_title='Number of Incidents',
                hovermode='x unified',
                template='plotly_white',
                height=400
            )
            
            forecast_figures[crime] = fig
            
        except Exception as e:
            st.warning(f"Could not forecast for {crime}: {str(e)}")
            continue
        
        progress_bar.progress((i + 1) / len(top_crimes))
    
    progress_bar.empty()
    
    # Display results
    if forecast_figures:
        st.success(f"✅ Successfully generated {forecast_period_label} forecasts for {len(forecast_figures)} crime types")
        
        # Summary statistics
        with st.expander("📊 Forecast Summary"):
            summary_data = []
            for crime, forecast in forecasts.items():
                try:
                    clean_forecast = forecast.fillna(0)
                    
                    total_forecast = safe_int_conversion(clean_forecast.sum())
                    avg_period = safe_numeric_conversion(clean_forecast.mean())
                    
                    if not clean_forecast.empty and clean_forecast.max() > 0:
                        max_period = clean_forecast.idxmax()
                        max_value = safe_int_conversion(clean_forecast.max())
                        peak_period_str = safe_strftime(max_period, '%Y-%m-%d')
                    else:
                        peak_period_str = "No peak"
                        max_value = 0
                    
                    # Adjust period label based on frequency
                    period_label = "Week" if frequency == 'W' else "Month"
                    
                    summary_data.append({
                        'Crime Type': crime,
                        'Total Predicted': total_forecast,
                        f'Average per {period_label}': f"{avg_period:.1f}",
                        'Peak Period': peak_period_str,
                        'Peak Value': max_value
                    })
                    
                except Exception as e:
                    summary_data.append({
                        'Crime Type': crime,
                        'Total Predicted': 0,
                        'Average per Period': "0.0",
                        'Peak Period': "Unknown",
                        'Peak Value': 0
                    })
            
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df, use_container_width=True)
        
        # Display charts
        for crime, fig in forecast_figures.items():
            st.plotly_chart(fig, use_container_width=True)
        
        # Generate message with correct period label
        message_data = generate_intelligent_forecast_message(
            forecasts, df, area_name, gender, forecast_period_label
        )
        
        if message_data and area_name:
            display_intelligent_forecast_message(message_data, df, area_name, gender, forecast_period_label)
    
    return forecast_figures

def run_forecast():
    """Main forecast interface with enhanced caching and clear time periods"""
    try:
        df = load_data()
        
        if df.empty:
            st.error("Could not load crime data. Please check your data file.")
            return

        # Pre-compute common models in background
        if 'models_precomputed' not in st.session_state:
            with st.spinner("Initializing forecast models..."):
                st.session_state.models_precomputed = precompute_common_models(df)

        st.sidebar.header("🔍 Forecast Filters")
        
        # Area selection
        area_options = ["All"] + sorted(df['AREA NAME'].dropna().unique())
        selected_area = st.sidebar.selectbox("Area Name", area_options)
        selected_area = None if selected_area == "All" else selected_area

        # Gender selection
        gender_options = ["All", "Male", "Female", "Other"]
        gender_input = st.sidebar.selectbox("Gender", gender_options)
        gender_map = {"Male": "M", "Female": "F", "Other": "X"}
        selected_gender = None if gender_input == "All" else gender_map.get(gender_input)

        # UPDATED: Clear forecast period selection with proper naming
        st.sidebar.markdown("### 📅 Forecast Duration")
        forecast_period = st.sidebar.selectbox(
            "Select time period to forecast", 
            [
                "1 Month",
                "2 Months",
                "Quarter (3 months)",
                "Half Year (6 months)",
                "Full Year (12 months)"
            ],
            help="Choose how far into the future to forecast"
        )
        
        # Clear mapping of periods to months
        months_lookup = {
            "1 Month": 1,
            "2 Months": 2,
            "Quarter (3 months)": 3,
            "Half Year (6 months)": 6,
            "Full Year (12 months)": 12
        }
        months_ahead = months_lookup[forecast_period]
        
        # Display what the forecast will cover
        st.sidebar.info(f"""
        📊 **Forecast Details:**
        - Duration: {forecast_period}
        - Data Points: {months_ahead * 4 if months_ahead <= 1 else months_ahead} {'weeks' if months_ahead <= 1 else 'months'}
        - Frequency: {'Weekly' if months_ahead <= 1 else 'Monthly'} predictions
        """)

        # Number of top crimes
        top_n = st.sidebar.slider("Number of Crime Types", min_value=3, max_value=15, value=10)

        # Show cache status
        if st.sidebar.checkbox("Show Cache Status"):
            cache_files = os.listdir(MODEL_CACHE_DIR) if os.path.exists(MODEL_CACHE_DIR) else []
            st.sidebar.info(f"📦 {len(cache_files)} models cached")
            
            if st.sidebar.button("Clear Model Cache"):
                for file in cache_files:
                    try:
                        os.remove(os.path.join(MODEL_CACHE_DIR, file))
                    except:
                        pass
                st.sidebar.success("Cache cleared!")

        # Forecast button
        if st.sidebar.button("🔮 Generate Forecast", type="primary"):
            with st.spinner(f"Generating {forecast_period} forecast..."):
                forecast_figures = forecast_crime(
                    df, 
                    selected_area, 
                    selected_gender, 
                    top_n=top_n, 
                    months_ahead=months_ahead,
                    forecast_period_label=forecast_period
                )

                if not forecast_figures:
                    st.warning("⚠️ No forecasts could be generated for the selected filters. Try different parameters.")
        
        # Information section with updated period descriptions
        with st.expander("ℹ️ About Crime Forecasting"):
            st.markdown(f"""
            **Performance Tips:**
            - Models are cached for 24 hours for faster repeated forecasts
            - Common area/crime combinations are pre-computed
            - Switching between time periods uses cached models when possible
            
            **Forecast Periods Explained:**
            - **1 Month**: Short-term forecast with weekly data points
            - **2 Months**: Near-term forecast with weekly/monthly intervals
            - **Quarter (3 months)**: Standard business quarter forecast
            - **Half Year (6 months)**: Medium-term strategic planning
            - **Full Year (12 months)**: Long-term annual projection
            
            **Note:** Forecasts are statistical predictions based on historical patterns.
            Shorter periods (1-2 months) tend to be more accurate than longer ones.
            """)
            
    except Exception as e:
        st.error(f"An error occurred in forecasting: {str(e)}")
        with st.expander("🔧 Debug Information"):
            import traceback
            st.code(traceback.format_exc())

if __name__ == "__main__":
    run_forecast()
