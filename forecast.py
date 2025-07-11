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
    df = pd.read_parquet("data/crime_data.parquet")
    df['DATE OCC'] = pd.to_datetime(df['DATE OCC'], errors='coerce')
    
    # Clean and validate data
    df = df.dropna(subset=['DATE OCC', 'Crm Cd Desc', 'AREA NAME', 'Vict Sex'])
    
    # Sort by date to ensure proper time series
    df = df.sort_values('DATE OCC')
    
    return df

def prepare_time_series(df, crime_type, frequency='M'):
    """
    Prepare time series data for forecasting
    frequency: 'D' for daily, 'W' for weekly, 'M' for monthly
    """
    # Filter for specific crime type
    crime_df = df[df['Crm Cd Desc'] == crime_type].copy()
    crime_df['Count'] = 1
    
    # Create time series based on frequency
    if frequency == 'D':
        ts = crime_df.groupby('DATE OCC')['Count'].sum().resample('D').sum().fillna(0)
    elif frequency == 'W':
        ts = crime_df.groupby('DATE OCC')['Count'].sum().resample('W').sum().fillna(0)
    else:  # Monthly
        ts = crime_df.groupby('DATE OCC')['Count'].sum().resample('M').sum().fillna(0)
    
    # Remove leading and trailing zeros for better modeling
    first_nonzero = ts[ts > 0].index.min() if (ts > 0).any() else ts.index.min()
    last_nonzero = ts[ts > 0].index.max() if (ts > 0).any() else ts.index.max()
    
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
    
    return ts_filtered

def get_forecast_dates(last_date, periods, frequency='M'):
    """Generate forecast dates starting from the day after last_date"""
    
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

def forecast_crime(df, area_name=None, gender=None, top_n=10, months_ahead=6):
    """Enhanced crime forecasting with proper date handling"""
    
    # Display forecast info
    st.write("### 🔮 AI Crime Forecast")
    
    # Get dataset date range
    min_date = df['DATE OCC'].min()
    max_date = df['DATE OCC'].max()
    
    st.info(f"""
    **Dataset Period:** {min_date.strftime('%B %d, %Y')} to {max_date.strftime('%B %d, %Y')}  
    **Forecast starts from:** {(max_date + pd.Timedelta(days=1)).strftime('%B %d, %Y')}
    """)

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
    top_crimes = df['Crm Cd Desc'].value_counts().head(top_n).index.tolist()
    forecasts = {}
    forecast_figures = {}

    progress_bar = st.progress(0)
    
    for i, crime in enumerate(top_crimes):
        try:
            # Prepare time series
            ts = prepare_time_series(df, crime, frequency)
            
            if len(ts) < 10:  # Need minimum data points
                st.warning(f"Insufficient data for {crime} (only {len(ts)} data points)")
                continue
            
            # Fit SARIMAX model
            with st.spinner(f"Forecasting {crime}..."):
                # Auto-detect best parameters or use simple ones
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
                    
                except:
                    # Fallback to simple ARIMA
                    model = SARIMAX(ts, order=(1,1,0))
                    results = model.fit(disp=False, maxiter=50)
                
                # Generate forecast
                forecast_values = results.forecast(steps=periods)
                conf_int = results.get_forecast(steps=periods).conf_int()
                
                # Create forecast dates starting from next period after last data date
                last_data_date = ts.index.max()
                forecast_dates = get_forecast_dates(last_data_date, periods, frequency)
                
                # Ensure non-negative forecasts
                forecast_values = np.maximum(forecast_values, 0)
                conf_int = np.maximum(conf_int, 0)
                
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
                fig.add_trace(go.Scatter(
                    x=forecast_dates,
                    y=conf_int.iloc[:, 1],
                    mode='lines',
                    name='Upper Confidence',
                    line=dict(color='rgba(255,0,0,0.2)', width=0),
                    showlegend=False
                ))
                
                fig.add_trace(go.Scatter(
                    x=forecast_dates,
                    y=conf_int.iloc[:, 0],
                    mode='lines',
                    name='Confidence Interval',
                    line=dict(color='rgba(255,0,0,0.2)', width=0),
                    fill='tonexty',
                    fillcolor='rgba(255,0,0,0.2)'
                ))
                
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
        
        # Summary statistics
        with st.expander("📊 Forecast Summary"):
            summary_data = []
            for crime, forecast in forecasts.items():
                total_forecast = forecast.sum()
                avg_monthly = forecast.mean()
                max_period = forecast.idxmax()
                max_value = forecast.max()
                
                summary_data.append({
                    'Crime Type': crime,
                    'Total Predicted': int(total_forecast),
                    'Average per Period': f"{avg_monthly:.1f}",
                    'Peak Period': max_period.strftime('%Y-%m-%d'),
                    'Peak Value': int(max_value)
                })
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
    
    return forecast_figures

def run_forecast():
    """Main forecast interface"""
    df = load_data()

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



