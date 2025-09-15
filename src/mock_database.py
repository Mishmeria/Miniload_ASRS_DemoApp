import pandas as pd
import random
from datetime import datetime, timedelta
import re
from src.state import state

# Dictionary mapping D registers to their meanings (copied from database.py)
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

# Mock data constants
ASRS_VALUES = [1, 2, 3]
BARCODE_VALUES = ["PALLET001", "PALLET002", "PALLET003", "PALLET004", "PALLET005"]
CHKTYPE_VALUES = ["IN", "OUT", "CHECK"]
MSGTYPE_VALUES = ["INFO", "ERROR", "WARNING", "ALARM"]

# PLC code values - both normal (< 100) and alarm (> 100) cases
NORMAL_PLCCODE_VALUES = [1, 2, 5, 10, 20, 30, 50, 80, 90]  # Normal operation codes
ALARM_PLCCODE_VALUES = [101, 102, 103, 104, 105]           # Alarm codes

STATUS_VALUES = ["NORMAL", "ALARM", "FAULT", "MAINTENANCE", "IDLE"]

# Message logs for different scenarios
NORMAL_MSGLOG_VALUES = [
    "System started normally",
    "Pallet retrieved successfully",
    "Pallet stored successfully",
    "Routine maintenance check passed",
    "System operating within normal parameters",
    "Inventory check completed",
    "Position calibration successful",
    "Normal operation cycle completed",
    "System idle - awaiting command"
]

ALARM_MSGLOG_VALUES = [
    "Alarm: Motor overheating",
    "Error: Position sensor failure",
    "Warning: Low battery",
    "Maintenance required",
    "Fault: Communication error",
    "System shutdown",
    "Alarm: Obstacle detected",
    "Error: Pallet misalignment",
    "Warning: Approaching operational limits",
    "Fault: Drive system error"
]

def generate_monitor_data():
    """Generate random MONITORDATA field with D register values."""
    monitor_data = ""
    for register in D_REGISTER_MEANINGS.keys():
        register_num = register.replace('D', '')
        value = random.randint(0, 10000)
        monitor_data += f"{register}={value} "
    return monitor_data

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

def generate_mock_data(start_date, end_date, num_records=None):
    """Generate mock ASRS log data for the given date range."""
    date_range = (end_date - start_date).days
    if date_range <= 0:
        date_range = 1  # Ensure at least 1 day range
    
    # Calculate number of records based on date range
    if num_records is None:
        # Generate approximately 200 records per day
        num_records = date_range * 200
    
    print(f"Generating {num_records} records for date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    data = []
    for _ in range(num_records):
        # Generate a random date within the range
        random_days = random.random() * date_range
        random_hours = random.random() * 24
        random_minutes = random.random() * 60
        random_seconds = random.random() * 60
        
        cdate = start_date + timedelta(
            days=random_days,
            hours=random_hours,
            minutes=random_minutes,
            seconds=random_seconds
        )
        
        monitor_data = generate_monitor_data()
        
        # Decide if this record is a normal operation or an alarm (70% normal, 30% alarm)
        is_normal = random.random() < 0.7
        
        if is_normal:
            plccode = random.choice(NORMAL_PLCCODE_VALUES)
            msglog = random.choice(NORMAL_MSGLOG_VALUES)
            msgtype = random.choice(["INFO", "NORMAL"])
        else:
            plccode = random.choice(ALARM_PLCCODE_VALUES)
            msglog = random.choice(ALARM_MSGLOG_VALUES)
            msgtype = random.choice(["ERROR", "WARNING", "ALARM"])
        
        record = {
            'ASRS': random.choice(ASRS_VALUES),
            'BARCODE': random.choice(BARCODE_VALUES),
            'CHKTYPE': random.choice(CHKTYPE_VALUES),
            'MSGLOG': msglog,
            'CDATE': cdate,
            'MSGTYPE': msgtype,
            'PLCCODE': plccode,
            'MONITORDATA': monitor_data,
        }
        data.append(record)
    
    # Sort by date
    data.sort(key=lambda x: x['CDATE'], reverse=True)
    
    return data

def load_data(start_date=None, end_date=None):
    """Mock implementation of load_data function."""
    try:
        # Determine date filter based on parameters
        if start_date is not None and end_date is not None:
            # Store the date range in state for other components to use
            state['date_range'] = (start_date, end_date)
            print(f"Loading mock data for date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
        elif 'selected_date' in state and state['selected_date'] is not None:
            start_date = state['selected_date']
            end_date = state.get('end_date') or (start_date + timedelta(days=1))
            print(f"Using state dates: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
        else:
            start_date = datetime.now() - timedelta(days=7)
            end_date = datetime.now()
            print(f"Using default dates: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Generate mock data specifically for this date range
        # Adjust end_date to include the full day
        end_date_inclusive = end_date
        if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
            end_date_inclusive = end_date + timedelta(days=1) - timedelta(seconds=1)
            
        mock_data = generate_mock_data(start_date, end_date_inclusive)
        df_logs = pd.DataFrame(mock_data)
        
        # Parse the monitor data
        parsed_data = []
        for monitor_data in df_logs['MONITORDATA']:
            parsed_data.append(parse_monitor_data(monitor_data))
        
        # Convert parsed data to DataFrame
        monitor_df = pd.DataFrame(parsed_data)
        
        # Ensure all columns from D_REGISTER_MEANINGS exist in monitor_df
        for register_name in D_REGISTER_MEANINGS.values():
            if register_name not in monitor_df.columns:
                monitor_df[register_name] = pd.NA
        
        # Combine the DataFrames
        if not monitor_df.empty:
            # Make sure all numeric columns are actually numeric
            for col in monitor_df.columns:
                monitor_df[col] = pd.to_numeric(monitor_df[col], errors='coerce')
            
            df_logs = pd.concat([df_logs, monitor_df], axis=1)
        
        # Ensure ASRS and PLCCODE are numeric
        df_logs['ASRS'] = pd.to_numeric(df_logs['ASRS'], errors='coerce')
        df_logs['PLCCODE'] = pd.to_numeric(df_logs['PLCCODE'], errors='coerce')
        
        # Drop MONITORDATA as it's no longer needed
        if 'MONITORDATA' in df_logs.columns:
            df_logs = df_logs.drop(columns=['MONITORDATA'])
        
        # Initialize pagination state if not already set
        if 'page_logs' not in state:
            state['page_logs'] = 0
        if 'rows_per_page' not in state:
            state['rows_per_page'] = 20
        if 'line_logs' not in state:
            state['line_logs'] = 'All'
        if 'status_logs' not in state:
            state['status_logs'] = 'All'
        
        state['df_logs'] = df_logs
        
        # Determine date info for logging
        if start_date is not None and end_date is not None:
            date_info = f" for range {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elif 'selected_date' in state and state['selected_date']:
            date_info = f" for {state['selected_date'].strftime('%Y-%m-%d')}"
        else:
            date_info = ""
            
        print(f"Mock data loaded{date_info}. Data Row: {len(df_logs)}")
        
        return True
    except Exception as e:
        print(f"Error loading mock data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False