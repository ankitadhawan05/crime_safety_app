# AI-powered crime forecasting using SARIMAX for top 10 crimes.
import pandas as pd
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

@st.cache_data
def load_data():
    """Load and preprocess crime data"""
    try:
        df = pd.read_parquet("data/crime_data.parquet")
        df['DATE OCC'] = pd.to_datetime(df['DATE OCC'], errors='coerce')
        
        # Clean and validate data - remove NaT values
        df = df.dropna(subset=['DATE OCC', 'Crm Cd Desc', 'AREA NAME', 'Vict Sex'])
        
        # Sort by date to ensure proper time series
        df = df.sort_values('DATE OCC')
        
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

def prepare_time_series(df, crime_type, frequency='M'):
    """
    Prepare time series data for forecasting
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
        elif frequency == 'W':
            ts = crime_df.groupby('DATE OCC')['Count'].sum().resample('W').sum().fillna(0)
        else:  # Monthly
            ts = crime_df.groupby('DATE OCC')['Count'].sum().resample('M').sum().fillna(0)
        
        # Remove leading and trailing zeros for better modeling
        if (ts > 0).any():
            first_nonzero = ts[ts > 0].index.min()
            last_nonzero = ts[ts > 0].index.max()
            
            # Keep some context around the non-zero period
            if frequency == 'M':
                start_date = first_nonzero - pd.DateOffset(months=3)
                end_date = last_nonzero + pd.DateOffset(months=1)
            elif frequency == 'W':
                start_date = first_nonzero - pd.DateOffset(weeks=4)
                end_date = last_nonzero + pd.DateOffset(weeks=1)
            else:  # Daily
                start_date = first_nonzero - pd.DateOffset(days=30)
                end_date = last_nonzero + pd.DateOffset(days=7)
            
            # Ensure we don't go beyond actual data range
            start_date = max(start_date, ts.index.min())
            end_date = min(end_date, ts.index.max())
            
            ts_filtered = ts[start_date:end_date]
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

def forecast_crime(df, area_name=None, gender=None, top_n=10, months_ahead=6):
    """Enhanced crime forecasting with proper date handling and NaN management"""
    
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
    if area_name:
        df = df[df['AREA NAME'] == area_name]
        st.write(f"**Area:** {area_name}")

    # Filter by gender
    if gender:
        df = df[df['Vict Sex'] == gender]
        gender_display = {"M": "Male", "F": "Female", "X": "Other"}.get(gender, gender)
        st.write(f"**Gender:** {gender_display}")

    if df.empty:
        st.warning("No data available for selected filters.")
        return {}

    # Determine frequency based on forecast period
    frequency_map = {1: 'W', 3: 'M', 6: 'M'}  # Week, Month, Quarter
    frequency = frequency_map.get(months_ahead, 'M')
    
    # Adjust periods based on frequency
    if frequency == 'W':
        periods = months_ahead * 4  # Approximate weeks in months
    else:
        periods = months_ahead

    # Get top crimes
    try:
        top_crimes = df['Crm Cd Desc'].value_counts().head(top_n).index.tolist()
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
            # Prepare time series
            ts = prepare_time_series(df, crime, frequency)
            
            if ts.empty or len(ts) < 10:  # Need minimum data points
                st.warning(f"Insufficient data for {crime} (only {len(ts)} data points)")
                continue
            
            # Fit SARIMAX model
            with st.spinner(f"Forecasting {crime}..."):
                try:
                    # Try seasonal model first
                    if frequency == 'M' and len(ts) >= 24:  # Need at least 2 years for seasonal
                        model = SARIMAX(ts, order=(1,1,1), seasonal_order=(1,1,1,12))
                    elif frequency == 'W' and len(ts) >= 52:  # Need at least 1 year for seasonal
                        model = SARIMAX(ts, order=(1,1,1), seasonal_order=(1,1,1,52))
                    else:
                        # Non-seasonal model
                        model = SARIMAX(ts, order=(1,1,1))
                    
                    results = model.fit(disp=False, maxiter=100)
                    
                except Exception as model_error:
                    # Fallback to simple ARIMA
                    st.warning(f"Using simplified model for {crime}: {str(model_error)}")
                    model = SARIMAX(ts, order=(1,1,0))
                    results = model.fit(disp=False, maxiter=50)
                
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

        # Forecast period
        forecast_period = st.sidebar.selectbox(
            "Forecast Period", 
            ["Week", "Month", "Quarter"],
            help="Week=4 weeks, Month=3 months, Quarter=6 months"
        )
        months_lookup = {"Week": 1, "Month": 3, "Quarter": 6}
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

                # Display forecast charts
                if forecast_figures:
                    for crime, fig in forecast_figures.items():
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("⚠️ No forecasts could be generated for the selected filters. Try different parameters.")
        
        # Information section
        with st.expander("ℹ️ About Crime Forecasting"):
            st.markdown("""
            **How it works:**
            - Uses SARIMAX (Seasonal AutoRegressive Integrated Moving Average with eXogenous regressors) models
            - Analyzes historical crime patterns to predict future trends
            - Accounts for seasonality in crime data
            - Provides confidence intervals for predictions
            
            **Forecast starts from:** The day after the last date in the dataset
            
            **Interpretation:**
            - 🔵 Blue line: Historical crime data
            - 🔴 Red dashed line: Predicted future crimes
            - 🔴 Red shaded area: Confidence interval (uncertainty range)
            
            **Note:** Forecasts are statistical predictions based on historical patterns and should be used as guidance alongside other crime prevention strategies.
            """)
            
    except Exception as e:
        st.error(f"An error occurred in forecasting: {str(e)}")
        with st.expander("🔧 Debug Information"):
            import traceback
            st.code(traceback.format_exc())