import pandas as pd
from datetime import datetime, timedelta
from src.state import state

def apply_filters(df, line_filter, status_filter, date_filter, table_type):
    filtered_df = df.copy()
    
    if line_filter != "All":
        filtered_df = filtered_df[filtered_df['LINE'] == int(line_filter)]
    
    if status_filter and status_filter != "All":
        if table_type == "TaskLoops":
            if status_filter == "Complete":
                filtered_df = filtered_df[filtered_df["Status"] == 1]
            elif status_filter == "Incomplete":
                filtered_df = filtered_df[filtered_df["Status"] == 0]
        else:
            try:
                status_value = float(status_filter)
                filtered_df = filtered_df[filtered_df["Status"] == status_value]
            except ValueError:
                # If status_filter is not a number, try to match it as a string
                filtered_df = filtered_df[filtered_df["Status"].astype(str) == status_filter]
    
    return filtered_df

def get_status_stats(df, line_filter="All", selected_date=None):
    stats_df = df.copy()
    
    if line_filter and line_filter != "All":
        stats_df = stats_df[stats_df['LINE'] == int(line_filter)]
    
    if len(stats_df) == 0:
        return pd.DataFrame(columns=['Status', 'Count', 'Percentage']), 0
    
    status_counts = stats_df['Status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']
    total_count = status_counts['Count'].sum()
    status_counts['Percentage'] = (status_counts['Count'] / total_count * 100).round(2)
    
    return status_counts.sort_values('Count', ascending=False), total_count

def calculate_line_alarm_frequency():
    df = state['df_logs']
    filtered_df = apply_filters(df, state['line_logs'], "All", state['selected_date'], "Logs")
    alarm_df = filtered_df[filtered_df['Status'] > 100].copy()
    
    if len(alarm_df) == 0:
        return pd.DataFrame(columns=['LINE', 'Count'])
        
    if alarm_df['LINE'].dtype == 'object':
        alarm_df['LINE_NUM'] = alarm_df['LINE'].astype(str).str.extract(r'LINE(\d+)', expand=False).astype('Int64')
    else:
        alarm_df['LINE_NUM'] = alarm_df['LINE'].astype('Int64')
        
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