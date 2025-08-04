import pandas as pd
import requests
from datetime import datetime, timedelta
from src.state import state
import json
import re

# API Configuration - Connect to VPN Gateway
API_CONFIG = {
    'base_url': 'http://10.0.0.2:6969', # for linux cloud 10.0.0.0 , 127.0.0.1 for local test
    'endpoints': {
        'logs': '/logs', # /logs for local test , /api/logs for cloud , /api/health too
        'health': '/health'
    },
    'timeout': 30,  # seconds
    'headers': {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Client-IP': '10.0.0.1'  # Identify client IP for logging 10.0.0.1 for cloud 127.0.0.1 for local
    }
}

# D Register meanings dictionary
D_REGISTER_MEANINGS = {
    'D174': 'Command_X_Pos (D174)',
    'D57':  'X_Distance_mm (D57) ',
    'D130': 'Start_Bank (D130)',
    'D131': 'Start_Pos_mm (D131)',
    'D133': 'Start_Level_mm (D133)',
    'D134': 'End_Bank (D134)',
    'D135': 'End_Position_mm (D135)',
    'D137': 'End_Level_mm (D137)',
    'D138': 'Pallet_ID (D138)',
    'D140': 'Present_Bay_Arm1 (D140)',
    'D145': 'Present_Level (D145)',
    'D146': 'Status_Arm1 (D146)',
    'D147': 'Status (D147)',
    'D148': 'Command Machine (D148)',
}

def process_monitor_data(df_logs):
    """
    Process MONITORDATA column and add parsed columns to the DataFrame.
    This function ensures all monitor data parsing happens in one place.
    """
    if df_logs.empty:
        print("DataFrame is empty, skipping monitor data processing")
        return df_logs
    
    if 'MONITORDATA' not in df_logs.columns:
        print("MONITORDATA column not found, skipping monitor data processing")
        return df_logs
    
    # Check if there's any data to parse
    has_monitor_data = df_logs['MONITORDATA'].notna().any()
    if not has_monitor_data:
        print("No MONITORDATA to parse, removing empty column")
        return df_logs.drop(columns=['MONITORDATA'])
    
    print("Processing MONITORDATA on client side...")
    
    try:
        # Apply parsing function to each row
        parsed_data = df_logs['MONITORDATA'].apply(parse_monitor_data).tolist()
        monitor_df = pd.DataFrame(parsed_data)
        
        if not monitor_df.empty:
            # Concatenate the parsed monitor data columns
            df_logs = pd.concat([df_logs, monitor_df], axis=1)
            print(f"Successfully added {len(monitor_df.columns)} parsed monitor data columns: {list(monitor_df.columns)}")
        else:
            print("No valid monitor data found after parsing")
        
        # Remove the original MONITORDATA column as it's now parsed
        df_logs = df_logs.drop(columns=['MONITORDATA'])
        
    except Exception as e:
        print(f"Error processing monitor data: {e}")
        print("Keeping original MONITORDATA column due to parsing error")
    
    return df_logs

def parse_monitor_data(monitor_data):
    """Parse the MONITORDATA field and extract D register values."""
    if pd.isna(monitor_data) or not isinstance(monitor_data, str):
        return {}
    
    # Regular expression to extract D register values
    pattern = r'D(\d+)=(\d+)'
    matches = re.findall(pattern, monitor_data)
    
    # Create dictionary of D register values
    d_values = {}
    for register, value in matches:
        d_key = f'D{register}'
        if d_key in D_REGISTER_MEANINGS:
            # Use the meaningful name as the key
            d_values[D_REGISTER_MEANINGS[d_key]] = int(value.strip())
    
    return d_values

class APIClient:
    def __init__(self):
        self.base_url = API_CONFIG['base_url']
        self.timeout = API_CONFIG['timeout']
        self.headers = API_CONFIG['headers']
    
    def _make_request(self, endpoint, params=None, method='GET'):
        """Make API request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(
                    url, 
                    params=params, 
                    headers=self.headers, 
                    timeout=self.timeout
                )

                print(f"Response status: {response.status_code}")
                print(f"Response URL: {response.url}")

                response.raise_for_status()  # Raise an exception for bad status codes
                return response.json()
            
            elif method == 'POST':
                response = requests.post(
                    url, 
                    json=params, 
                    headers=self.headers, 
                    timeout=self.timeout
                )
                
                print(f"Response status: {response.status_code}")
                print(f"Response URL: {response.url}")

                response.raise_for_status()  # Raise an exception for bad status codes
                return response.json()
            
            
            
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            return None
    
    def check_health(self):
        """Check if API is accessible"""
        result = self._make_request(API_CONFIG['endpoints']['health'])
        return result is not None
    
    def fetch_logs(self, date_filter=None):
        """Fetch logs data from API with support for date ranges"""
        params = {}
        
        if date_filter:
            if 'start_date' in date_filter:
                params['start_date'] = date_filter['start_date']
            if 'end_date' in date_filter:
                params['end_date'] = date_filter['end_date']
        
        return self._make_request(API_CONFIG['endpoints']['logs'], params)

def load_data(start_date=None, end_date=None):
    """Load data via API with support for date ranges (matching local_database.py interface)"""
    client = APIClient()
    
    # Check API health first
    if not client.check_health():
        print("API is not accessible. Please check VPN connection and API server.")
        return False
    
    # Prepare date filter based on parameters (matching local_database.py logic)
    date_filter = None
    
    if start_date is not None and end_date is not None:
        # Date range provided as parameters
        date_filter = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
        # Store the date range in state for other components to use
        state['date_range'] = (start_date, end_date)
        print(f"Loading data for date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
    elif 'selected_date' in state and state['selected_date'] is not None:
        # Single date from state
        selected_date = state['selected_date']
        next_day = selected_date + timedelta(days=1)
        
        date_filter = {
            'start_date': selected_date.strftime('%Y-%m-%d'),
            'end_date': next_day.strftime('%Y-%m-%d')
        }
        print(f"Loading data for selected date: {selected_date.strftime('%Y-%m-%d')}")
    
    # Fetch logs data
    logs_data = client.fetch_logs(date_filter)
    
    if logs_data is None:
        print("Failed to fetch logs data from API")
        return False
    
    # Convert to DataFrame and process (matching local_database.py processing)
    try:
        print(f"Received {len(logs_data) if logs_data else 0} log entries from API")

        df_logs = pd.DataFrame(logs_data or [])
        
        if df_logs.empty:
            print("No data returned from API")
            return False
        
        # Ensure required columns exist (matching local_database.py structure)
        required_columns = ['ASRS', 'BARCODE', 'CHKTYPE', 'MSGLOG', 'CDATE', 'MSGTYPE', 'PLCCODE', 'MONITORDATA']
        for col in required_columns:
            if col not in df_logs.columns:
                df_logs[col] = None
        
        # Data type conversions (matching local_database.py)
        if 'ASRS' in df_logs.columns:
            df_logs['ASRS'] = pd.to_numeric(df_logs['ASRS'], errors='coerce').astype('Int64')
        if 'PLCCODE' in df_logs.columns:
            df_logs['PLCCODE'] = pd.to_numeric(df_logs['PLCCODE'], errors='coerce').astype('Int64')
        
        # Convert timestamp (API returns string, convert back to datetime)
        if 'CDATE' in df_logs.columns:
            df_logs['CDATE'] = pd.to_datetime(df_logs['CDATE'], errors="coerce")
        
        # Parse monitor data and add columns (CLIENT-SIDE PROCESSING)
        df_logs = process_monitor_data(df_logs)
        print("Monitor data processing completed")
        
        # Store in state
        state['df_logs'] = df_logs
        
        # Determine date info for logging (matching local_database.py)
        if start_date is not None and end_date is not None:
            date_info = f" for range {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elif 'selected_date' in state and state['selected_date']:
            date_info = f" for {state['selected_date'].strftime('%Y-%m-%d')}"
        else:
            date_info = ""
            
        print(f"Data loaded via API{date_info}. Data Row: {len(df_logs)}")

        return True
        
    except Exception as e:
        print(f"Error processing API response: {e}")
        return False

# Alternative function for manual API calls
def get_api_data(endpoint, params=None):
    """Generic function to make API calls"""
    client = APIClient()
    return client._make_request(endpoint, params)

# Configuration update function
def update_api_config(base_url=None, timeout=None, client_ip=None):
    """Update API configuration"""
    if base_url:
        API_CONFIG['base_url'] = base_url
    if timeout:
        API_CONFIG['timeout'] = timeout
    if client_ip:
        API_CONFIG['headers']['X-Client-IP'] = client_ip

# VPN Connection helper
def test_vpn_connectivity():
    """Test VPN connectivity to API server"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('10.0.0.2', 6969))  # Updated to match API server
        sock.close()
        return result == 0
    except:
        return False

# Convenience function for other files to get processed data
def get_processed_logs_data():
    """
    Get the processed logs data from state.
    If data exists but hasn't been processed, process it.
    Returns the DataFrame with parsed monitor data columns.
    """
    if 'df_logs' not in state or state['df_logs'] is None:
        print("No logs data in state. Call load_data() first.")
        return None
    
    df_logs = state['df_logs'].copy()
    
    # Check if data needs processing (has MONITORDATA column)
    if 'MONITORDATA' in df_logs.columns:
        print("Data needs monitor processing, processing now...")
        df_logs = process_monitor_data(df_logs)
        # Update state with processed data
        state['df_logs'] = df_logs
    
    return df_logs

# Function to force reprocessing of monitor data
def reprocess_monitor_data():
    """
    Force reprocessing of monitor data.
    Useful if parsing logic has been updated.
    """
    if 'df_logs' not in state or state['df_logs'] is None:
        print("No logs data in state to reprocess.")
        return False
    
    # Note: This assumes you have the original data with MONITORDATA
    # If you don't, you'll need to reload from API
    df_logs = state['df_logs'].copy()
    
    if 'MONITORDATA' in df_logs.columns:
        df_logs = process_monitor_data(df_logs)
        state['df_logs'] = df_logs
        print("Monitor data reprocessed successfully")
        return True
    else:
        print("No MONITORDATA column found. Data may already be processed or needs to be reloaded.")
        return False