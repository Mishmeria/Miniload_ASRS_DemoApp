import pandas as pd
import requests
from datetime import datetime, timedelta
from src.state import state
import json

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
        required_columns = ['ASRS', 'BARCODE', 'CHKTYPE', 'MSGLOG', 'CDATE', 'MSGTYPE', 'PLCCODE']
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