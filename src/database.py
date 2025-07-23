import pandas as pd
import requests
from datetime import datetime, timedelta
from src.state import state
import json
import os
import random

# Check if we should use mock data (can be set via environment variable)
USE_MOCK_DATA = os.environ.get('USE_MOCK_DATA', 'false').lower() == 'true'

# API Configuration - Connect to VPN Gateway
API_CONFIG = {
    'base_url': os.environ.get('API_URL', 'http://10.0.0.0:6969'),
    'endpoints': {
        'logs': '/logs', 
        'health': '/health'
    },
    'timeout': 30,  # seconds
    'headers': {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Client-IP': os.environ.get('CLIENT_IP', '10.0.0.1')
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

            response.raise_for_status() # type: ignore
            return response.json()  # type: ignore
            
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
        """Fetch logs data from API"""
        params = {}
        
        if date_filter:
            params['start_date'] = date_filter['start_date']
            params['end_date'] = date_filter['end_date']
        
        return self._make_request(API_CONFIG['endpoints']['logs'], params)

def create_mock_data(selected_date=None):
    """Create mock data for demonstration when API is not available"""
    # Create a sample DataFrame with mock data
    mock_data = []
    
    # Use selected date if available, otherwise use current date
    if selected_date is None:
        selected_date = datetime.now()
    
    # Generate random status codes
    status_codes = [100, 200, 300, 400, 500]
    
    # Generate random messages
    messages = [
        "System operational",
        "Task completed successfully",
        "Warning: Low battery",
        "Error: Connection lost",
        "Critical: System failure",
        "Maintenance required",
        "Waiting for input",
        "Processing task",
        "Task queued",
        "System idle"
    ]
    
    # Generate random categories
    categories = ["Normal", "Warning", "Error", "Critical", "Info"]
    
    # Generate mock data entries
    for i in range(100):
        line_number = random.randint(1, 10)
        status_code = random.choice(status_codes)
        timestamp = selected_date - timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
        
        mock_data.append({
            "LINE": line_number,
            "TimeStamp": timestamp.isoformat(),
            "Status": status_code,
            "Message": random.choice(messages),
            "Category": random.choice(categories)
        })
    
    df_logs = pd.DataFrame(mock_data)
    df_logs["LINE"] = df_logs["LINE"].astype("Int64")
    df_logs['TimeStamp'] = pd.to_datetime(df_logs['TimeStamp'])
    
    # Store in state
    state['df_logs'] = df_logs
    print(f"Mock data created with {len(df_logs)} rows")
    return True

def load_data():
    """Load data via API instead of direct database connection"""
    # Initialize state with empty DataFrame if not already present
    if 'df_logs' not in state:
        state['df_logs'] = pd.DataFrame()
    
    # If mock data is enabled, use that instead of real API
    if USE_MOCK_DATA:
        print("Using mock data for demonstration")
        return create_mock_data(state.get('selected_date'))
    
    client = APIClient()
    
    # Check API health first
    if not client.check_health():
        print("API is not accessible. Please check VPN connection and API server.")
        print(f"Attempted to connect to: {API_CONFIG['base_url']}")
        
        # Fall back to mock data if configured
        if os.environ.get('FALLBACK_TO_MOCK', 'false').lower() == 'true':
            print("Falling back to mock data")
            return create_mock_data(state.get('selected_date'))
        
        return False
    
    # Prepare date filter if selected
    date_filter = None
    if 'selected_date' in state and state['selected_date'] is not None:
        selected_date = state['selected_date']
        next_day = selected_date + timedelta(days=1)
        
        date_filter = {
            'start_date': selected_date.strftime('%Y-%m-%d'),
            'end_date': next_day.strftime('%Y-%m-%d')
        }
    
    # Fetch logs data
    logs_data = client.fetch_logs(date_filter)
    
    if logs_data is None:
        print("Failed to fetch logs data from API")
        
        # Fall back to mock data if configured
        if os.environ.get('FALLBACK_TO_MOCK', 'false').lower() == 'true':
            print("Falling back to mock data")
            return create_mock_data(state.get('selected_date'))
        
        return False
    
    # Convert to DataFrame
    try:
        print(f"Received {len(logs_data) if logs_data else 0} log entries from API")

        df_logs = pd.DataFrame(logs_data or [])
        
        if "LINE" not in df_logs.columns:
            df_logs["LINE"] = None
        if "TimeStamp" not in df_logs.columns:
            df_logs["TimeStamp"] = None
        
        # Preprocess data (same as before)
        df_logs["LINE"] = df_logs["LINE"].astype(str)
        mask = df_logs["LINE"].str.contains(r"LINE\d+-MP", na=False)

        if mask.any():
            df_logs.loc[mask, "LINE"] = df_logs.loc[mask, "LINE"].str.extract(r"LINE(\d+)-MP")

        df_logs["LINE"] = pd.to_numeric(df_logs["LINE"], errors="coerce").astype("Int64")
        df_logs['TimeStamp'] = pd.to_datetime(df_logs['TimeStamp'], errors="coerce")
        
        if df_logs.empty:
            print("No data returned from API")
            
            # Fall back to mock data if configured
            if os.environ.get('FALLBACK_TO_MOCK', 'false').lower() == 'true':
                print("Falling back to mock data")
                return create_mock_data(state.get('selected_date'))
            
            return False
        
        # Store in state
        state['df_logs'] = df_logs
        
        # Print info
        date_info = f" for {state['selected_date'].strftime('%Y-%m-%d')}" if 'selected_date' in state and state['selected_date'] else ""
        print(f"Data loaded via API{date_info} | Data Rows: {len(df_logs)}")

        return True
        
    except Exception as e:
        print(f"Error processing API response: {e}")
        
        # Fall back to mock data if configured
        if os.environ.get('FALLBACK_TO_MOCK', 'false').lower() == 'true':
            print("Falling back to mock data")
            return create_mock_data(state.get('selected_date'))
        
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
        result = sock.connect_ex(('10.0.0.0', 8000))
        sock.close()
        return result == 0
    except:
        return False