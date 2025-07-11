from data_preprocess import load_crime_data, preprocess_for_clustering
from clustering_engine import train_and_save_model

# Load raw data
df = load_crime_data()

# Transform features
df_proc, features = preprocess_for_clustering(df)

# Train model and save
train_and_save_model(df_proc, features, model_path="models/kmeans_model.pkl")

print("✅ Clustering model trained and saved in 'models/kmeans_model.pkl'")

