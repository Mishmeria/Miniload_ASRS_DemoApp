# New file: src/api_client.py
import requests
import pandas as pd
from io import StringIO
from src.state import state

API_BASE_URL = "https://your-api-domain.com/api"  # Change to your actual API endpoint

def load_data():
    """Load data via API instead of direct database connection"""
    # Check if a date filter is selected
    date_params = {}
    
    if 'selected_date' in state and state['selected_date'] is not None:
        date_params['date'] = state['selected_date'].strftime('%Y-%m-%d')
    
    # Make API request
    response = requests.get(
        f"{API_BASE_URL}/asrs_logs", 
        params=date_params,
        headers={"Authorization": "Bearer YOUR_API_KEY"}  # Use environment variable
    )
    
    if response.status_code == 200:
        # Convert JSON response to DataFrame
        df_logs = pd.DataFrame(response.json()['data'])
        
        # Preprocess
        df_logs["LINE"] = df_logs["LINE"].str.extract(r"LINE(\d+)-MP").astype("Int64")
        df_logs['TimeStamp'] = pd.to_datetime(df_logs['TimeStamp'])
        
        state['df_logs'] = df_logs
        
        date_info = f" for {state['selected_date'].strftime('%Y-%m-%d')}" if 'selected_date' in state and state['selected_date'] else ""
        print(f"Data loaded{date_info} | Data Rows: {len(df_logs)}")
    else:
        print(f"API Error: {response.status_code} - {response.text}")
        # Handle error appropriately