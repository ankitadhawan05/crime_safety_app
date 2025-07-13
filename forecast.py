# AI-powered crime forecasting using SARIMAX for top 10 crimes.
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
import streamlit as st

@st.cache_data

def load_data():
    df = pd.read_parquet("data/crime_data.parquet")
    df['DATE OCC'] = pd.to_datetime(df['DATE OCC'], errors='coerce')
    return df.dropna(subset=['DATE OCC', 'Crm Cd Desc', 'AREA NAME', 'Vict Sex'])

def forecast_crime(df, area_name=None, gender=None, top_n=10, months_ahead=6):
    st.write("### Crime Forecast for Top Crimes")

    # Filter by area
    if area_name:
        df = df[df['AREA NAME'] == area_name]

    # Filter by gender
    if gender:
        df = df[df['Vict Sex'] == gender]

    if df.empty:
        st.warning("No data available for selected filters.")
        return {}

    df['Count'] = 1
    top_crimes = df['Crm Cd Desc'].value_counts().head(top_n).index.tolist()
    forecasts = {}

    for crime in top_crimes:
        crime_df = df[df['Crm Cd Desc'] == crime]
        ts = crime_df.groupby('DATE OCC')['Count'].sum().resample('M').sum().fillna(0)

        try:
            model = SARIMAX(ts, order=(1,1,1), seasonal_order=(1,1,1,12))
            results = model.fit(disp=False)
            forecast = results.forecast(steps=months_ahead)
            forecasts[crime] = forecast
        except Exception as e:
            st.warning(f"Could not forecast for {crime}: {e}")

    return forecasts

def run_forecast():
    df = load_data()

    st.sidebar.header("🔍 Forecast Filters")
    area_options = ["All"] + sorted(df['AREA NAME'].dropna().unique())
    selected_area = st.sidebar.selectbox("Area Name", area_options)
    selected_area = None if selected_area == "All" else selected_area

    gender_options = ["All", "Male", "Female", "Other"]
    gender_input = st.sidebar.selectbox("Gender", gender_options)
    gender_map = {"Male": "M", "Female": "F", "Other": "X"}
    selected_gender = None if gender_input == "All" else gender_map.get(gender_input)

    forecast_period = st.sidebar.selectbox("Forecast Period", ["Week", "Month", "Quarter"])
    months_lookup = {"Week": 1, "Month": 3, "Quarter": 6}
    months_ahead = months_lookup[forecast_period]

    if st.button("🔮 Forecast Crimes"):
        forecasts = forecast_crime(df, selected_area, selected_gender, months_ahead=months_ahead)

        for crime, forecast in forecasts.items():
            st.subheader(f"📌 {crime}")
            st.line_chart(forecast)

        if not forecasts:
            st.info("No forecasts available for the selected filters.")



