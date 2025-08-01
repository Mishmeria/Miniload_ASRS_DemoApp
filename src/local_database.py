import pandas as pd
import re
from sqlalchemy import create_engine
from datetime import datetime, timedelta
from src.state import state

# Configuration
DB_CONFIG = {
    'server': '191.20.80.101\\WMS',
    'database': 'WCSLOG',
    'username': 'sa',
    'password': 'amwteam',
    'driver': 'ODBC Driver 17 for SQL Server'
}

def get_connection_string():
    return f"mssql+pyodbc://{DB_CONFIG['username']}:{DB_CONFIG['password']}@{DB_CONFIG['server']}/{DB_CONFIG['database']}?driver={DB_CONFIG['driver'].replace(' ', '+')}&TrustServerCertificate=yes"

# Dictionary mapping D registers to their meanings
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

def load_data():
    try:
        engine = create_engine(get_connection_string())
        
        date_filter = ""
        
        if 'selected_date' in state and state['selected_date'] is not None:
            selected_date = state['selected_date']
            next_day = selected_date + timedelta(days=1)
            
            # Format dates for SQL query
            start_date = selected_date.strftime('%Y-%m-%d')
            end_date = next_day.strftime('%Y-%m-%d')
            
            logs_date_filter = f"WHERE [CDATE] >= '{start_date}' AND [CDATE] < '{end_date}'"
        else:
            logs_date_filter = ""
        
        logs_query = f"""
            SELECT [ASRS],[BARCODE],[CHKTYPE],[MSGLOG],[CDATE],[MSGTYPE],[PLCCODE],[MONITORDATA]
            FROM [WCSLOG].[dbo].[LogMnpAsrs]
            {logs_date_filter}
            ORDER BY CDATE DESC
        """
        
        df_logs = pd.read_sql(logs_query, engine)
        
        # Basic data cleaning
        df_logs['ASRS'] = df_logs['ASRS'].str.strip().astype(int, errors='ignore')
        df_logs['PLCCODE'] = df_logs['PLCCODE'].str.strip().astype(int, errors='ignore')
        df_logs['CDATE'] = pd.to_datetime(df_logs['CDATE'])
        
        parsed_data = df_logs['MONITORDATA'].apply(parse_monitor_data).tolist()
        monitor_df = pd.DataFrame(parsed_data)
        
        if not monitor_df.empty:
            df_logs = pd.concat([df_logs, monitor_df], axis=1)
        
        if 'MONITORDATA' in df_logs.columns:
            df_logs = df_logs.drop(columns=['MONITORDATA'])
        
        state['df_logs'] = df_logs
        
        date_info = f" for {state['selected_date'].strftime('%Y-%m-%d')}" if 'selected_date' in state and state['selected_date'] else ""
        print(f"Data loaded{date_info} Data Row: {len(df_logs)}")
        
        return True
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return False