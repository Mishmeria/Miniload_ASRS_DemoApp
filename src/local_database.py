import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta
from src.state import state

# Configuration
DB_CONFIG = {
    'server': '191.20.110.47',
    'database': 'Dan_Database',
    'username': 'dan',
    'password': '1234',
    'driver': 'ODBC Driver 17 for SQL Server'
}

def get_connection_string():
    return f"mssql+pyodbc://{DB_CONFIG['username']}:{DB_CONFIG['password']}@{DB_CONFIG['server']}/{DB_CONFIG['database']}?driver={DB_CONFIG['driver'].replace(' ', '+')}"

def load_data():
    engine = create_engine(get_connection_string())
    
    # Check if a date filter is selected
    date_filter = ""
    date_params = {}
    
    if 'selected_date' in state and state['selected_date'] is not None:
        selected_date = state['selected_date']
        next_day = selected_date + timedelta(days=1)
        
        # Format dates for SQL query
        start_date = selected_date.strftime('%Y-%m-%d')
        end_date = next_day.strftime('%Y-%m-%d')
        
        logs_date_filter = f"WHERE [TimeStamp] >= '{start_date}' AND [TimeStamp] < '{end_date}'"
    else:
        logs_date_filter = ""
    
    
    logs_query = f"""
        SELECT [TimeStamp],[LINE],[PalletID],[Duration],[Status],[Command],
               [PresentBay],[PresentLevel],[DistanceX],[DistanceY],
               [AVG_X_Current],[AVG_Y_Current],[AVG_Z_Current],
               [Max_X_Current],[Max_Y_Current],[Max_Z_Current],
               [AVG_X_Frequency],[AVG_Y_Frequency],[AVG_Z_Frequency],
               [Max_X_Frequency],[Max_Y_Frequency],[Max_Z_Frequency]
        FROM [Dan_Database].[dbo].[ASRS_Logs]
        {logs_date_filter}
        ORDER BY TimeStamp DESC
    """
    
    #df_loops = pd.read_sql(loop_query, engine)
    df_logs = pd.read_sql(logs_query, engine)
    
    # Preprocess
    df_logs["LINE"] = df_logs["LINE"].str.extract(r"LINE(\d+)-MP").astype("Int64")
    #df_loops.rename(columns={"TimeStart": "TimeStamp"}, inplace=True)
    #df_loops['TimeStamp'] = pd.to_datetime(df_loops['TimeStamp'])
    df_logs['TimeStamp'] = pd.to_datetime(df_logs['TimeStamp'])
    
    #state['df_loops'] = df_loops
    state['df_logs'] = df_logs
    
    date_info = f" for {state['selected_date'].strftime('%Y-%m-%d')}" if 'selected_date' in state and state['selected_date'] else ""
    print(f"Data loaded{date_info} Data Row : {len(df_logs)}") #| Loops: {len(df_loops)} | Logs: