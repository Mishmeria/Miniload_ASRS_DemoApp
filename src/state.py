# Global state management

# Global state
state = {
    'page_logs': 0,
    'rows_per_page': 100,
    'line_logs': "All", 
    'status_logs': "All",
    'selected_date': None,
    'df_logs': None,
    'filter_choice': "All"
}

API_CONFIG = {
    'base_url': 'http://127.0.0.1:6969', # for linux cloud 10.0.0.0 , 127.0.0.1 for local test
    'endpoints': {
        'logs': '/logs', # /logs for local test , /api/logs for cloud , /api/health too
        'health': '/health'
    },
    'timeout': 30,  # seconds
    'headers': {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Client-IP': '127.0.0.1'  # Identify client IP for logging 10.0.0.1 for cloud 127.0.0.1 for local
    }
}