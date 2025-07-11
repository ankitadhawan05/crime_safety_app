import pandas as pd

# Load your dataset
df = pd.read_csv("crime_data.csv")

# Save as Parquet
df.to_parquet("data/crime_data.parquet", index=False)
