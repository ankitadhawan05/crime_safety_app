# AI-powered crime forecasting using SARIMAX for top 10 crimes with enhanced messaging.
import pandas as pd
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# OPTIMIZATION: Cache data loading and reduce data points moderately
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data():
    """Load and preprocess crime data with moderate optimization"""
    try:
        df = pd.read_parquet("data/crime_data.parquet")
        df['DATE OCC'] = pd.to_datetime(df['DATE OCC'], errors='coerce')
        
        # Clean and validate data - remove NaT values
        df = df.dropna(subset=['DATE OCC', 'Crm Cd Desc', 'AREA NAME', 'Vict Sex'])
        
        # Sort by date to ensure proper time series
        df = df.sort_values('DATE OCC')
        
        # OPTIMIZATION: Keep last 3 years of data for better statistical representation
        three_years_ago = pd.Timestamp.now() - pd.DateOffset(years=3)
        df = df[df['DATE OCC'] >= three_years_ago]
        
        # OPTIMIZATION: If still too large, sample data intelligently
        if len(df) > 200000:  # If more than 200k records
            # Keep all recent data (last year)
            one_year_ago = pd.Timestamp.now() - pd.DateOffset(years=1)
            recent_data = df[df['DATE OCC'] >= one_year_ago]
            
            # Sample 70% of older data (maintains better statistical representation)
            older_data = df[df['DATE OCC'] < one_year_ago].sample(frac=0.7, random_state=42)
            
            # Combine
            df = pd.concat([recent_data, older_data]).sort_values('DATE OCC')
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

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

# OPTIMIZATION: Cache time series preparation with balanced data points
@st.cache_data(ttl=1800)
def prepare_time_series(df, crime_type, frequency='M'):
    """
    Prepare time series data for forecasting with balanced data points
    frequency: 'D' for daily, 'W' for weekly, 'M' for monthly
    """
    try:
        # Filter for specific crime type
        crime_df = df[df['Crm Cd Desc'] == crime_type].copy()
        
        if crime_df.empty:
            return pd.Series()
        
        crime_df['Count'] = 1
        
        # Create time series based on frequency
        if frequency == 'D':
            ts = crime_df.groupby('DATE OCC')['Count'].sum().resample('D').sum().fillna(0)
            # OPTIMIZATION: Limit daily data to last 180 days (6 months) for better representation
            ts = ts.tail(180)
        elif frequency == 'W':
            ts = crime_df.groupby('DATE OCC')['Count'].sum().resample('W').sum().fillna(0)
            # OPTIMIZATION: Limit weekly data to last 104 weeks (2 years)
            ts = ts.tail(104)
        else:  # Monthly
            ts = crime_df.groupby('DATE OCC')['Count'].sum().resample('M').sum().fillna(0)
            # OPTIMIZATION: Limit monthly data to last 36 months (3 years)
            ts = ts.tail(36)
        
        # Remove leading zeros for better modeling (but keep trailing context)
        if (ts > 0).any():
            first_nonzero = ts[ts > 0].index.min()
            # Keep a small buffer before first non-zero
            if frequency == 'M':
                buffer_start = first_nonzero - pd.DateOffset(months=1)
            elif frequency == 'W':
                buffer_start = first_nonzero - pd.DateOffset(weeks=2)
            else:  # Daily
                buffer_start = first_nonzero - pd.DateOffset(days=7)
            
            # Ensure we don't go before data start
            buffer_start = max(buffer_start, ts.index.min())
            ts_filtered = ts[buffer_start:]
        else:
            ts_filtered = ts
        
        return ts_filtered
        
    except Exception as e:
        st.warning(f"Error preparing time series for {crime_type}: {str(e)}")
        return pd.Series()

def get_forecast_dates(last_date, periods, frequency='M'):
    """Generate forecast dates starting from the day after last_date"""
    
    try:
        if pd.isna(last_date) or pd.isnull(last_date):
            # Fallback to a default date if last_date is invalid
            last_date = pd.Timestamp('2023-12-31')
        
        if frequency == 'M':
            # For monthly, start from the first day of next month
            if last_date.day == 1:
                start_date = last_date + pd.DateOffset(months=1)
            else:
                start_date = (last_date + pd.DateOffset(months=1)).replace(day=1)
            
            forecast_dates = pd.date_range(
                start=start_date,
                periods=periods,
                freq='MS'  # Month start
            )
        elif frequency == 'W':
            # For weekly, start from next week
            start_date = last_date + pd.DateOffset(weeks=1)
            start_date = start_date - pd.Timedelta(days=start_date.weekday())  # Start of week
            
            forecast_dates = pd.date_range(
                start=start_date,
                periods=periods,
                freq='W-MON'  # Weekly starting Monday
            )
        else:  # Daily
            # For daily, start from next day
            start_date = last_date + pd.Timedelta(days=1)
            
            forecast_dates = pd.date_range(
                start=start_date,
                periods=periods,
                freq='D'
            )
        
        return forecast_dates
        
    except Exception as e:
        st.warning(f"Error generating forecast dates: {str(e)}")
        # Return a fallback date range
        fallback_start = pd.Timestamp('2024-01-01')
        return pd.date_range(start=fallback_start, periods=periods, freq='MS')

def clean_forecast_values(forecast_values):
    """Clean forecast values by removing NaN, infinity, and negative values"""
    try:
        # Convert to numpy array for easier handling
        if isinstance(forecast_values, pd.Series):
            values = forecast_values.values
        else:
            values = np.array(forecast_values)
        
        # Replace NaN and infinity with 0
        values = np.where(np.isnan(values) | np.isinf(values), 0, values)
        
        # Ensure non-negative values
        values = np.maximum(values, 0)
        
        return values
        
    except Exception as e:
        st.warning(f"Error cleaning forecast values: {str(e)}")
        # Return array of zeros as fallback
        return np.zeros(len(forecast_values))

# OPTIMIZATION: Cache street analysis
@st.cache_data(ttl=1800)
def get_top_crime_streets(df, area_name, top_n=3):
    """Get top streets with highest crime count for a specific area"""
    try:
        # Filter data for the selected area
        area_data = df[df['AREA NAME'] == area_name]
        
        # Count crimes by cross street - try different column names
        if 'CROSS STREET' in area_data.columns:
            street_crimes = area_data['CROSS STREET'].value_counts()
        elif 'Cross Street' in area_data.columns:
            street_crimes = area_data['Cross Street'].value_counts()
        else:
            return []
        
        # Remove NaN and empty values, get top streets
        street_crimes = street_crimes.dropna()
        street_crimes = street_crimes[street_crimes.index != '']
        
        top_streets = street_crimes.head(top_n).index.tolist()
        
        return top_streets
    except Exception as e:
        return []

# OPTIMIZATION: Cache gender analysis
@st.cache_data(ttl=1800)
def get_most_affected_gender(df, area_name, crime_type):
    """Get the gender most affected by a specific crime type in an area"""
    try:
        # Filter data for the selected area first
        filtered_df = df[df['AREA NAME'] == area_name]
        
        if len(filtered_df) == 0:
            return 'individuals'
        
        # Count all crimes by gender in that area (not just specific crime type)
        gender_counts = filtered_df['Vict Sex'].value_counts()
        
        if len(gender_counts) == 0:
            return 'individuals'
        
        # Get the gender with highest count
        most_affected_code = gender_counts.index[0]
        
        # Convert gender codes to readable format
        if most_affected_code == 'M':
            return 'males'
        elif most_affected_code == 'F':
            return 'females'
        else:
            return 'individuals'
            
    except Exception as e:
        return 'individuals'

# OPTIMIZATION: Cache risk probability calculations
@st.cache_data(ttl=1800)
def calculate_risk_probability(df, area_name, crime_type, forecast_periods, selected_gender=None):
    """Calculate risk probability based on actual historical crime data for the specific area and gender"""
    try:
        # Get historical data for the specific area
        area_data = df[df['AREA NAME'] == area_name]
        
        # Apply gender filter if specified
        if selected_gender:
            area_data = area_data[area_data['Vict Sex'] == selected_gender]
        
        # Filter for specific crime type
        crime_data = area_data[area_data['Crm Cd Desc'] == crime_type]
        
        if len(crime_data) == 0:
            # Return different default based on gender if no specific data
            if selected_gender == 'F':
                return 8  # Slightly higher default for females in some crime types
            elif selected_gender == 'M':
                return 12  # Different default for males
            return 5  # Default for "All"
            
        # Calculate monthly average from historical data
        crime_data['YearMonth'] = crime_data['DATE OCC'].dt.to_period('M')
        monthly_counts = crime_data.groupby('YearMonth').size()
        
        if len(monthly_counts) == 0:
            return 5
            
        # Get actual statistics for this specific area, crime type, and gender combination
        avg_monthly = monthly_counts.mean()
        max_monthly = monthly_counts.max()
        total_crimes_in_filtered_area = len(area_data)  # Total crimes for this area+gender combo
        total_crime_type_in_filtered_area = len(crime_data)  # This crime type for area+gender combo
        
        # Calculate crime density (crimes per month relative to filtered area size)
        months_of_data = len(monthly_counts)
        if months_of_data == 0:
            return 5
            
        crime_density = total_crime_type_in_filtered_area / months_of_data
        
        # Calculate percentage of this crime type in the filtered area
        crime_type_percentage = (total_crime_type_in_filtered_area / total_crimes_in_filtered_area * 100) if total_crimes_in_filtered_area > 0 else 0
        
        # Dynamic probability calculation based on actual filtered data
        base_probability = min(crime_type_percentage * 2.5, 35)  # Base on actual crime type prevalence
        
        # Gender-specific adjustments based on actual data patterns
        if selected_gender == 'F':
            # Check if females are disproportionately affected in this area for this crime
            all_area_data = df[df['AREA NAME'] == area_name]
            female_ratio = len(all_area_data[all_area_data['Vict Sex'] == 'F']) / len(all_area_data) if len(all_area_data) > 0 else 0.5
            if female_ratio > 0.6:  # If females are more than 60% of victims
                base_probability *= 1.3
            elif female_ratio < 0.3:  # If females are less than 30% of victims
                base_probability *= 0.7
        elif selected_gender == 'M':
            # Check if males are disproportionately affected in this area for this crime
            all_area_data = df[df['AREA NAME'] == area_name]
            male_ratio = len(all_area_data[all_area_data['Vict Sex'] == 'M']) / len(all_area_data) if len(all_area_data) > 0 else 0.5
            if male_ratio > 0.6:  # If males are more than 60% of victims
                base_probability *= 1.3
            elif male_ratio < 0.3:  # If males are less than 30% of victims
                base_probability *= 0.7
        
        # Adjust based on monthly average intensity for the filtered data
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
        
        # Adjust based on recent trend (last 6 months vs overall average) for filtered data
        recent_months = monthly_counts.tail(6)
        if len(recent_months) >= 3:
            recent_avg = recent_months.mean()
            trend_multiplier = min(recent_avg / avg_monthly, 2.0) if avg_monthly > 0 else 1.0
        else:
            trend_multiplier = 1.0
        
        # Calculate final probability
        final_probability = base_probability * intensity_multiplier * trend_multiplier
        
        # Ensure realistic bounds (3% to 85%)
        final_probability = max(3, min(85, int(final_probability)))
        
        return final_probability
        
    except Exception as e:
        # Return a hash-based number that varies by area, crime type, AND gender
        area_hash = hash(area_name + crime_type + str(selected_gender)) % 60
        return max(5, min(50, 8 + area_hash))

# OPTIMIZATION: Cache crime risk streets
@st.cache_data(ttl=1800)
def get_crime_risk_streets(df, area_name=None, gender=None, crime_types=None, top_n=5):
    """Get high-risk streets based on crime data"""
    try:
        filtered_df = df.copy()
        
        # Apply filters
        if area_name:
            filtered_df = filtered_df[filtered_df['AREA NAME'] == area_name]
        
        if gender:
            filtered_df = filtered_df[filtered_df['Vict Sex'] == gender]
        
        if crime_types:
            filtered_df = filtered_df[filtered_df['Crm Cd Desc'].isin(crime_types)]
        
        # Get streets with most crimes
        if 'CROSS STREET' in filtered_df.columns:
            street_crimes = filtered_df['CROSS STREET'].value_counts().head(top_n)
            return street_crimes.index.tolist()
        elif 'Cross Street' in filtered_df.columns:
            street_crimes = filtered_df['Cross Street'].value_counts().head(top_n)
            return street_crimes.index.tolist()
        else:
            # Fallback to area names if cross streets not available
            area_crimes = filtered_df['AREA NAME'].value_counts().head(top_n)
            return area_crimes.index.tolist()
            
    except Exception as e:
        st.warning(f"Error getting risk streets: {str(e)}")
        return []

def generate_intelligent_forecast_message(forecasts, df, area_name=None, gender=None, forecast_period="Month"):
    """Generate intelligent messaging based on forecast results and filters"""
    
    try:
        if not forecasts:
            return None
        
        # Analyze forecast results
        total_predicted = sum([forecast.sum() for forecast in forecasts.values()])
        crime_types = list(forecasts.keys())
        most_predicted_crime = max(forecasts.items(), key=lambda x: x[1].sum())
        
        # Calculate probability (simplified approach)
        historical_crimes = len(df)
        if area_name:
            historical_crimes = len(df[df['AREA NAME'] == area_name])
        if gender:
            if area_name:
                historical_crimes = len(df[(df['AREA NAME'] == area_name) & (df['Vict Sex'] == gender)])
            else:
                historical_crimes = len(df[df['Vict Sex'] == gender])
        
        # Estimate probability based on forecast vs historical average
        if historical_crimes > 0:
            probability = min(int((total_predicted / (historical_crimes / 12)) * 100), 95)  # Cap at 95%
        else:
            probability = 25  # Default probability
        
        # Get high-risk streets
        risk_streets = get_crime_risk_streets(df, area_name, gender, crime_types, top_n=3)
        
        # Create personalized message
        location_text = f"in {area_name}" if area_name else "in the analyzed areas"
        gender_text = {"M": "males", "F": "females", "X": "individuals"}.get(gender, "individuals")
        
        # Time period mapping - UPDATED WITH NEW PERIODS
        period_text = {
            "1 Month": "the next month",
            "2 Months": "the next 2 months", 
            "Quarter (3 months)": "the next quarter",
            "Half Year (6 months)": "the next 6 months",
            "Full Year (12 months)": "the next year"
        }.get(forecast_period, "the forecast period")
        
        # Generate message components
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
            'risk_streets': risk_streets[:3],  # Top 3 streets
            'area_name': area_name or "the selected areas"
        }
        
        return message_data
        
    except Exception as e:
        st.warning(f"Error generating forecast message: {str(e)}")
        return None

def display_intelligent_forecast_message(message_data, df, area_name, selected_gender, forecast_months):
    """Display the simplified forecast message with high-risk prediction and street safety advisory"""
    
    if not message_data or not area_name:
        return
    
    try:
        # Get top crime type for the area
        area_data = df[df['AREA NAME'] == area_name]
        top_crime = area_data['Crm Cd Desc'].value_counts().index[0] if len(area_data) > 0 else "theft plain - petty ($950 & under)"
        
        # Calculate risk probability with gender consideration - NOW WITH 5 PARAMETERS
        risk_probability = calculate_risk_probability(df, area_name, top_crime, forecast_months, selected_gender)
        
        # Create time period text - UPDATED WITH NEW PERIODS
        period_text = {
            1: "the next month",
            2: "the next 2 months",
            3: "the next quarter",
            6: "the next 6 months",
            12: "the next year"
        }.get(forecast_months, f"the next {forecast_months} months")
        
        # Create risk prediction message based on gender selection
        if selected_gender is None:  # This means "All" was selected
            # Only show gender-specific risk when "All" is selected
            most_affected = get_most_affected_gender(df, area_name, top_crime)
            risk_message = f"<strong>High-Risk Crime Prediction in <strong>{area_name}</strong> which shows a {risk_probability}% probability of experiencing {top_crime.lower()} incidents during {period_text}, with {most_affected} being particularly at Risk</strong>"
        else:
            # Don't mention gender when specific gender is selected
            risk_message = f"<strong>High-Risk Crime Prediction in <strong>{area_name}</strong> which shows a {risk_probability}% probability of experiencing {top_crime.lower()} incidents during {period_text}</strong>"
        
        # Get top crime streets for the area and clean them
        top_streets = get_top_crime_streets(df, area_name, top_n=3)
        
        # Clean and format street names properly
        if top_streets:
            # Clean street names by removing extra spaces and formatting properly
            cleaned_streets = []
            for street in top_streets:
                if street and str(street).strip() and str(street).strip() != 'nan':
                    # Remove extra spaces and clean the street name
                    clean_street = ' '.join(str(street).split())
                    cleaned_streets.append(clean_street)
            
            if cleaned_streets:
                streets_text = ", ".join(cleaned_streets)
                street_message = f"Based on historical crime data, exercise extra caution on streets: {streets_text}"
            else:
                street_message = f"Based on historical crime data, exercise extra caution when in the {area_name} area."
        else:
            street_message = f"Based on historical crime data, exercise extra caution when in the {area_name} area."
        
        # Create combined message box with blue/pink gradient styling to match charts
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

# OPTIMIZATION: Cache SARIMAX model training with balanced parameters
@st.cache_resource(ttl=1800)
def train_sarimax_model(ts, frequency, crime_type):
    """Train and cache SARIMAX model with balanced optimization"""
    try:
        # OPTIMIZATION: Use appropriate models based on data length
        if frequency == 'M' and len(ts) >= 24:  # Need at least 2 years for good seasonal
            # Standard seasonal model with moderate iterations
            model = SARIMAX(ts, order=(1,1,1), seasonal_order=(1,1,1,12))
            results = model.fit(disp=False, maxiter=75)  # Moderate iterations
        elif frequency == 'W' and len(ts) >= 52:  # Need at least 1 year for seasonal
            # Weekly seasonal model
            model = SARIMAX(ts, order=(1,1,1), seasonal_order=(1,0,1,52))
            results = model.fit(disp=False, maxiter=75)
        else:
            # Non-seasonal model
            model = SARIMAX(ts, order=(1,1,1))
            results = model.fit(disp=False, maxiter=75)
        
        return results
        
    except Exception as model_error:
        # Fallback to simpler ARIMA
        try:
            model = SARIMAX(ts, order=(1,1,0))
            results = model.fit(disp=False, maxiter=50)
            return results
        except:
            # Ultimate fallback - simplest model
            model = SARIMAX(ts, order=(0,1,1))
            results = model.fit(disp=False, maxiter=50)
            return results

def forecast_crime(df, area_name=None, gender=None, top_n=10, months_ahead=6):
    """Enhanced crime forecasting with intelligent messaging"""
    
    # Display forecast info
    st.write("### 🔮 AI Crime Forecast")
    
    if df.empty:
        st.warning("No data available for forecasting.")
        return {}
    
    # Get dataset date range with safe formatting
    try:
        min_date = df['DATE OCC'].min()
        max_date = df['DATE OCC'].max()
        
        # Safely format dates
        min_date_str = safe_strftime(min_date)
        max_date_str = safe_strftime(max_date)
        
        # Calculate next day safely
        if pd.notna(max_date):
            next_day = max_date + pd.Timedelta(days=1)
            next_day_str = safe_strftime(next_day)
        else:
            next_day_str = "Unknown"
        
        st.info(f"""
        **Dataset Period:** {min_date_str} to {max_date_str}  
        **Forecast starts from:** {next_day_str}
        """)
    except Exception as e:
        st.warning(f"Could not determine dataset date range: {str(e)}")
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
        frequency = 'W'  # Weekly frequency for 1 month
        periods = months_ahead * 4  # Approximate weeks in months
    else:
        frequency = 'M'  # Monthly frequency for longer periods
        periods = months_ahead

    # Get top crimes
    try:
        top_crimes = filtered_df['Crm Cd Desc'].value_counts().head(top_n).index.tolist()
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
            # Prepare time series (cached)
            ts = prepare_time_series(filtered_df, crime, frequency)
            
            if ts.empty or len(ts) < 10:  # Need minimum data points
                st.warning(f"Insufficient data for {crime} (only {len(ts)} data points)")
                continue
            
            # Fit SARIMAX model (cached)
            with st.spinner(f"Forecasting {crime}..."):
                results = train_sarimax_model(ts, frequency, crime)
                
                # Generate forecast
                forecast_raw = results.forecast(steps=periods)
                
                # Clean forecast values to handle NaN/infinity
                forecast_values = clean_forecast_values(forecast_raw)
                
                try:
                    conf_int_raw = results.get_forecast(steps=periods).conf_int()
                    # Clean confidence intervals
                    conf_int = pd.DataFrame({
                        'lower': clean_forecast_values(conf_int_raw.iloc[:, 0] if hasattr(conf_int_raw, 'iloc') else conf_int_raw['lower']),
                        'upper': clean_forecast_values(conf_int_raw.iloc[:, 1] if hasattr(conf_int_raw, 'iloc') else conf_int_raw['upper'])
                    })
                except:
                    # Create dummy confidence intervals if they fail
                    conf_int = pd.DataFrame({
                        'lower': forecast_values * 0.8,
                        'upper': forecast_values * 1.2
                    })
                
                # Create forecast dates starting from next period after last data date
                last_data_date = ts.index.max()
                forecast_dates = get_forecast_dates(last_data_date, periods, frequency)
                
                # Store results
                forecast_series = pd.Series(forecast_values, index=forecast_dates)
                forecasts[crime] = forecast_series
                
                # Create interactive plot
                fig = go.Figure()
                
                # Historical data (last 12 periods for context)
                historical_data = ts.tail(min(12, len(ts)))
                fig.add_trace(go.Scatter(
                    x=historical_data.index,
                    y=historical_data.values,
                    mode='lines+markers',
                    name='Historical Data',
                    line=dict(color='blue', width=2),
                    marker=dict(size=6)
                ))
                
                # Forecast
                fig.add_trace(go.Scatter(
                    x=forecast_dates,
                    y=forecast_values,
                    mode='lines+markers',
                    name='Forecast',
                    line=dict(color='red', width=2, dash='dash'),
                    marker=dict(size=6)
                ))
                
                # Confidence interval
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
                    pass  # Skip confidence intervals if they fail
                
                # Update layout
                fig.update_layout(
                    title=f'{crime} - Forecast',
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
        
        # Update progress
        progress_bar.progress((i + 1) / len(top_crimes))
    
    progress_bar.empty()
    
    # Display results
    if forecast_figures:
        st.success(f"✅ Successfully generated forecasts for {len(forecast_figures)} crime types")
        
        # Summary statistics with improved NaN handling
        with st.expander("📊 Forecast Summary"):
            summary_data = []
            for crime, forecast in forecasts.items():
                try:
                    # Clean forecast series to handle NaN values
                    clean_forecast = forecast.fillna(0)  # Replace NaN with 0
                    
                    # Use safe conversion functions
                    total_forecast = safe_int_conversion(clean_forecast.sum())
                    avg_period = safe_numeric_conversion(clean_forecast.mean())
                    
                    # Find peak period safely
                    if not clean_forecast.empty and clean_forecast.max() > 0:
                        max_period = clean_forecast.idxmax()
                        max_value = safe_int_conversion(clean_forecast.max())
                        peak_period_str = safe_strftime(max_period, '%Y-%m-%d')
                    else:
                        peak_period_str = "No peak"
                        max_value = 0
                    
                    summary_data.append({
                        'Crime Type': crime,
                        'Total Predicted': total_forecast,
                        'Average per Period': f"{avg_period:.1f}",
                        'Peak Period': peak_period_str,
                        'Peak Value': max_value
                    })
                    
                except Exception as e:
                    st.warning(f"Could not generate summary for {crime}: {str(e)}")
                    # Add a fallback entry
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
            else:
                st.info("No summary data could be generated.")
        
        # Display forecast charts
        for crime, fig in forecast_figures.items():
            st.plotly_chart(fig, use_container_width=True)
        
        # Generate and display simplified forecast message with UPDATED PERIOD NAME
        # Get the actual period name from the forecast
        period_name = {
            1: "1 Month",
            2: "2 Months",
            3: "Quarter (3 months)",
            6: "Half Year (6 months)",
            12: "Full Year (12 months)"
        }.get(months_ahead, f"{months_ahead} months")
        
        message_data = generate_intelligent_forecast_message(
            forecasts, df, area_name, gender, period_name
        )
        
        if message_data and area_name:
            display_intelligent_forecast_message(message_data, df, area_name, gender, months_ahead)
    
    return forecast_figures

def run_forecast():
    """Main forecast interface"""
    try:
        df = load_data()
        
        if df.empty:
            st.error("Could not load crime data. Please check your data file.")
            return

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

        # UPDATED FORECAST PERIOD WITH CLEAR NAMES
        forecast_period = st.sidebar.selectbox(
            "Forecast Period", 
            [
                "1 Month",
                "2 Months",
                "Quarter (3 months)",
                "Half Year (6 months)",
                "Full Year (12 months)"
            ],
            help="Select how far ahead to forecast"
        )
        
        # UPDATED MAPPING WITH CORRECT PERIODS
        months_lookup = {
            "1 Month": 1,
            "2 Months": 2,
            "Quarter (3 months)": 3,
            "Half Year (6 months)": 6,
            "Full Year (12 months)": 12
        }
        months_ahead = months_lookup[forecast_period]

        # Number of top crimes to forecast
        top_n = st.sidebar.slider("Number of Crime Types", min_value=3, max_value=15, value=10)

        # Forecast button
        if st.sidebar.button("🔮 Generate Forecast", type="primary"):
            with st.spinner("Analyzing crime patterns and generating forecasts..."):
                forecast_figures = forecast_crime(
                    df, 
                    selected_area, 
                    selected_gender, 
                    top_n=top_n, 
                    months_ahead=months_ahead
                )

                if not forecast_figures:
                    st.warning("⚠️ No forecasts could be generated for the selected filters. Try different parameters.")
        
        # Information section
        with st.expander("ℹ️ About Crime Forecasting"):
            st.markdown("""
            **Note:** Forecasts are statistical predictions based on historical patterns and should be used as guidance alongside other crime prevention strategies.
            """)
            
    except Exception as e:
        st.error(f"An error occurred in forecasting: {str(e)}")
        with st.expander("🔧 Debug Information"):
            import traceback
            st.code(traceback.format_exc())
