# 🛡️ Crime Safety Travel Assistant (AI-Powered)

This application provides intelligent crime hotspot detection, safe route planning, and crime forecasting to help users make informed travel decisions based on historical crime data.

---

## 🚀 Features

✅ **Crime Hotspot Clustering**  
Mini batch KMeans-based clustering with filters for time of day, victim age group, and crime severity.

✅ **AI-Powered Crime Forecasting**  
Forecasts the most frequent crime types monthly using SARIMAX or other optimized models.

✅ **Safe Route Planner**  
Uses Open Source Routing Machine (OSRM) to find the safest route between two areas, avoiding high-crime zones.

✅ **Risk Scoring Engine**  
Quantifies route risk using clustering + historical data.

✅ **Streamlit Dashboard**  
Interactive, modular dashboard with real-time maps, charts, and filters.

## 📁 CRIME_SAFETY_APPV2 Structure
```
├── app.py # Streamlit main entry
├── clustering.py # UI for crime clustering
├── forecast.py # Crime forecasting
├── risk_scoring.py # Route risk calculation
├── ui_safety_route.py # Safe route planning UI
├── utils_maps.py # Map drawing utilities
├── train_clustering_model.py # Clustering model training
├── data_preprocess.py # Feature engineering
├── data/
│ └── crime_data.parquet # Preprocessed crime dataset
├── models/
│ └── crime_model.pkl # Trained clustering or forecast models
├── requirements.txt 
```

---

Author: Ankita Dhawan
Crime Forecasting & Safe Travel Mapping
GitLab: [axd1049](https://git.cs.bham.ac.uk/projects-2024-25/axd1049)