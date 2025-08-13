import pandas as pd
from datetime import datetime, timedelta
from src.state import state

def apply_filters(df, line_filter, status_filter, date_filter, table_type):
    if df is None or not isinstance(df, pd.DataFrame):
        print("Warning: No DataFrame provided to apply_filters, returning empty DataFrame")
        return pd.DataFrame()
    
    filtered_df = df.copy()
    
    if line_filter != "All":
        filtered_df = filtered_df[filtered_df['ASRS'] == int(line_filter)]
    
    if status_filter and status_filter != "All":
        if table_type == "TaskLoops":
            if status_filter == "Complete":
                filtered_df = filtered_df[filtered_df["PLCCODE"] == 1]
            elif status_filter == "Incomplete":
                filtered_df = filtered_df[filtered_df["PLCCODE"] == 0]
        else:
            try:
                status_value = float(status_filter)
                filtered_df = filtered_df[filtered_df["PLCCODE"] == status_value]
            except ValueError:
                # If status_filter is not a number, try to match it as a string
                filtered_df = filtered_df[filtered_df["PLCCODE"].astype(str) == status_filter]
<<<<<<< HEAD

    # NEW: Date-range filter (uses state.start_date and state.end_date)
    if 'CDATE' in filtered_df.columns:
        if not pd.api.types.is_datetime64_any_dtype(filtered_df['CDATE']):
            filtered_df['CDATE'] = pd.to_datetime(filtered_df['CDATE'], errors='coerce')

        start_date = state.get('start_date')
        end_date = state.get('end_date') or start_date  # if end is None, single-day
=======
    
    if state.get('time_filter_active', False) and 'CDATE' in filtered_df.columns:
        start_time = state.get('start_time', "All")
        end_time = state.get('end_time', "All")
>>>>>>> parent of 0f2bd63 (big change for customer await the export excel function)
        
        if start_time != "All" and end_time != "All":
            # Convert CDATE to datetime if it's not already
            if not pd.api.types.is_datetime64_any_dtype(filtered_df['CDATE']):
                filtered_df['CDATE'] = pd.to_datetime(filtered_df['CDATE'], errors='coerce')
            
            # Extract time from datetime and filter
            filtered_df['time_only'] = filtered_df['CDATE'].dt.strftime('%H:%M')
            
            # Convert start and end times to comparable format
            start_hour, start_minute = map(int, start_time.split(':'))
            end_hour, end_minute = map(int, end_time.split(':'))
            
            # Extract hour from CDATE for comparison
            filtered_df['hour'] = filtered_df['CDATE'].dt.hour
            
            # Filter by time range
            # For cases where start_time < end_time (e.g., 08:00-19:00)
            mask = (filtered_df['hour'] >= start_hour) & (filtered_df['hour'] < end_hour)
            
            # Also include exact matches for the end hour (e.g., 19:00)
            # but only if the minute is 00 (since we're using whole hours)
            if end_minute == 0:
                mask = mask | ((filtered_df['hour'] == end_hour) & (filtered_df['CDATE'].dt.minute == 0))
                
            filtered_df = filtered_df[mask]
            
            # Remove temporary columns
            filtered_df = filtered_df.drop(['time_only', 'hour'], axis=1)
    
    return filtered_df

def get_status_stats(df, line_filter="All", selected_date=None):
    stats_df = df.copy()
    
    if line_filter and line_filter != "All":
        stats_df = stats_df[stats_df['ASRS'] == int(line_filter)]
    
    if len(stats_df) == 0:
        return pd.DataFrame(columns=['PLCCODE', 'Count', 'Percentage']), 0
    
    status_counts = stats_df['PLCCODE'].value_counts().reset_index()
    status_counts.columns = ['PLCCODE', 'Count']
    total_count = status_counts['Count'].sum()
    status_counts['Percentage'] = (status_counts['Count'] / total_count * 100).round(2)
    
    return status_counts.sort_values('Count', ascending=False), total_count

def calculate_line_alarm_frequency():
    df = state['df_logs']
    filtered_df = apply_filters(df, state['line_logs'], "All", state['start_date'], "Logs")
    alarm_df = filtered_df[filtered_df['PLCCODE'] > 100].copy()
    
    if len(alarm_df) == 0:
        return pd.DataFrame(columns=['LINE', 'Count'])
        
    if alarm_df['ASRS'].dtype == 'object':
        alarm_df['LINE_NUM'] = alarm_df['ASRS'].astype(str).str.extract(r'LINE(\d+)', expand=False).astype('Int64')
    else:
        alarm_df['LINE_NUM'] = alarm_df['ASRS'].astype('Int64')
        
    alarm_df = alarm_df.dropna(subset=['LINE_NUM'])
    
    if len(alarm_df) == 0:
        return pd.DataFrame(columns=['LINE', 'Count'])
        
    line_counts = alarm_df['LINE_NUM'].value_counts().reset_index()
    line_counts.columns = ['LINE', 'Count']
    line_counts = line_counts.sort_values('LINE')
    
    all_lines = pd.DataFrame({'LINE': range(1, 9)})
    line_alarm_data = pd.merge(all_lines, line_counts, on='LINE', how='left')
    line_alarm_data['Count'] = line_alarm_data['Count'].fillna(0).astype(int)
    line_alarm_data = line_alarm_data[line_alarm_data['Count'] > 0]
    
    return line_alarm_data.sort_values('Count', ascending=False)