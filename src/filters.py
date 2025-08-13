import pandas as pd
from datetime import datetime, timedelta
from src.state import state

def apply_filters(df, line_filter, status_filter, date_filter, table_type):
    filtered_df = df.copy()

    # SRM/LINE
    if line_filter != "All":
        filtered_df = filtered_df[filtered_df['ASRS'] == int(line_filter)]

    # Status / PLCCODE
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
                filtered_df = filtered_df[filtered_df["PLCCODE"].astype(str) == status_filter]

    # NEW: Date-range filter (uses state.selected_date and state.end_date)
    if 'CDATE' in filtered_df.columns:
        if not pd.api.types.is_datetime64_any_dtype(filtered_df['CDATE']):
            filtered_df['CDATE'] = pd.to_datetime(filtered_df['CDATE'], errors='coerce')

        start_date = state.get('selected_date')
        end_date = state.get('end_date') or start_date  # if end is None, single-day
        
        if start_date:
            start_dt = pd.Timestamp(start_date.strftime('%Y-%m-%d'))
            end_excl = pd.Timestamp((end_date + timedelta(days=1)).strftime('%Y-%m-%d')) # type: ignore
            mask = (filtered_df['CDATE'] >= start_dt) & (filtered_df['CDATE'] < end_excl)
            filtered_df = filtered_df[mask]

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

    return status_counts.sort_values('Count', ascending=False), 0 if total_count is None else total_count

def calculate_line_alarm_frequency():
    df = state['df_logs']
    filtered_df = apply_filters(df, state['line_logs'], "All", state['selected_date'], "Logs")
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