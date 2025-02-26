from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Load the CSV file into a DataFrame
csv_filename = "parking_export.csv"
df = pd.read_csv(csv_filename)


@app.get("/data")
def get_data():
    """Endpoint to return the CSV data as JSON."""
    
    print(df.head())  # Add this line to check the DataFrame content
    return df.to_dict(orient="records")

# Run the server with: uvicorn filename:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

