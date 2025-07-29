import flet as ft
import pandas as pd
import threading
import time
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.state import state
from src.filters import get_status_stats, apply_filters
from src.ui_components import create_filter_controls # type: ignore

from views.Status_Detail import Alarm_status_map, Normal_status_map , ALARM_CATEGORIES , CATEGORY_COLORS

# Alarm categories

stats_cache = {'logs_stats': None, 'alarm_df': None, 'before_alarm_df': None, 'filter_state': None}

def create_task_progress_gauge():
    logs_stats, total = get_status_stats(state['df_logs'], state['line_logs'], state['selected_date'])
    
    if total == 0:
        return ft.Container(
            content=ft.Text("No TaskLogs data available", size=14, color=ft.Colors.GREY_600),
            height=100, alignment=ft.alignment.center,
            bgcolor=ft.Colors.GREY_50, border_radius=8,
            border=ft.border.all(1, ft.Colors.GREY_300)
        )
    
    complete_count = logs_stats[logs_stats["Status"] <= 100]["Count"].sum()
    incomplete_count = logs_stats[logs_stats["Status"] > 100]["Count"].sum()

    complete_percent = (complete_count / total) * 100 if total else 0
    
    header = ft.Row([
        ft.Text(f"📦 TotalLogs: {total} records", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
        ft.Text(f"✅ Working: {complete_count} ({complete_percent:.1f}%)", size=14, color=ft.Colors.GREEN_700),
        ft.Text(f"❌ Alarm : {incomplete_count} ({100-complete_percent:.1f}%)", size=14, color=ft.Colors.RED_700)
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=25)
    
    # Use ProgressBar with custom colors
    progress_bar = ft.ProgressBar(
        value=complete_percent / 100,  # Value between 0 and 1
        bgcolor=ft.Colors.RED_400,     # Background color (red for alarms)
        color=ft.Colors.GREEN_400,     # Progress color (green for working)
        height=20,
        border_radius=10,
    )
    
    return ft.Container(
        content=ft.Column([header, progress_bar, ft.Container(height=6)], spacing=5),
        alignment=ft.alignment.center, padding=10,
        bgcolor=ft.Colors.WHITE, border_radius=8,
        border=ft.border.all(1, ft.Colors.GREY_300)
    )

def create_statistics_view(page):
    filter_controls = create_filter_controls(page=page, table_type=None, show_status=False, show_refresh=True)
    loading_view = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.ProgressRing(width=50, height=50),
                ft.Text("Loading statistics...", size=16)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.center, expand=True
        )
    ])
    
    main_container = ft.Container(
        content=ft.Column([filter_controls, loading_view], scroll=ft.ScrollMode.AUTO),
        padding=15, expand=True
    )
    
    def load_data_async():
        time.sleep(0.1)
        # Create a simple tuple for comparison
        current_filter_state = (str(state['line_logs']), state['selected_date'].strftime("%Y-%m-%d") if hasattr(state['selected_date'], 'strftime') else str(state['selected_date']))
        
        # Safe comparison - check if filter state has changed or if cache is empty
        should_reload = (stats_cache['filter_state'] is None or 
                         stats_cache['filter_state'] != current_filter_state or 
                         stats_cache['logs_stats'] is None)
        
        if should_reload:
            try:
                logs_stats, _ = get_status_stats(state['df_logs'], state['line_logs'], state['selected_date'])
                logs_stats = logs_stats[logs_stats['Status'] > 100] if len(logs_stats) > 0 else logs_stats
                alarm_df, before_alarm_df = process_alarm_data()
                
                stats_cache.update({
                    'logs_stats': logs_stats,
                    'alarm_df': alarm_df,
                    'before_alarm_df': before_alarm_df,
                    'filter_state': current_filter_state
                }) # type: ignore
            except Exception as e:
                print(f"Error loading statistics data: {e}")
                # Fallback to empty DataFrames if there's an error
                stats_cache.update({
                    'logs_stats': pd.DataFrame(),
                    'alarm_df': pd.DataFrame(),
                    'before_alarm_df': pd.DataFrame(),
                    'filter_state': current_filter_state
                }) # type: ignore
        
        try:
            task_gauge = create_task_progress_gauge()
            main_content = create_main_layout(stats_cache['alarm_df'], stats_cache['before_alarm_df'])
            
            main_container.content = ft.Column([filter_controls, task_gauge, main_content], scroll=ft.ScrollMode.AUTO)
            page.update()
        except Exception as e:
            print(f"Error updating statistics view: {e}")
            # Show error message in UI
            error_content = ft.Column([
                filter_controls,
                ft.Container(
                    content=ft.Text(f"Error loading statistics: {str(e)}", 
                                    color=ft.Colors.RED_600, size=16),
                    padding=20,
                    alignment=ft.alignment.center
                )
            ])
            main_container.content = error_content
            page.update()
    
    threading.Thread(target=load_data_async).start()
    return main_container

# Rest of the file remains unchanged
def process_alarm_data():
    df = state['df_logs']
    if df is None or len(df) == 0:
        return pd.DataFrame(), pd.DataFrame()
    
    filtered_df = apply_filters(df, state['line_logs'], "All", state['selected_date'], "ASRS_Logs")
    alarm_df = filtered_df[filtered_df['Status'] > 100] if 'Status' in filtered_df.columns else pd.DataFrame()
    
    if len(alarm_df) == 0:
        return alarm_df, pd.DataFrame()
    
    alarm_df = alarm_df.sort_values('TimeStamp', ascending=False)
    before_alarm_rows = []
    sorted_df = filtered_df.sort_values('TimeStamp')
    
    for _, alarm_row in alarm_df.iterrows():
        line_value = alarm_row['LINE']
        alarm_time = alarm_row['TimeStamp']
        previous_rows = sorted_df[
            (sorted_df['LINE'] == line_value) & 
            (sorted_df['TimeStamp'] < alarm_time) &
            (sorted_df['Status'] < 100)
        ]
        
        if len(previous_rows) > 0:
            previous_row = previous_rows.iloc[-1]
            previous_row = previous_row.copy()
            previous_row['Alarm'] = alarm_row['Status']
            previous_row['AlarmTime'] = alarm_row['TimeStamp']
            
            if isinstance(previous_row['TimeStamp'], pd.Timestamp) and isinstance(alarm_row['TimeStamp'], pd.Timestamp):
                duration_seconds = (alarm_row['TimeStamp'] - previous_row['TimeStamp']).total_seconds()
                previous_row['Duration'] = f"{int(duration_seconds)}s"
            else:
                previous_row['Duration'] = "Unknown"
            
            before_alarm_rows.append(previous_row)
    
    if before_alarm_rows:
        before_alarm_df = pd.DataFrame(before_alarm_rows)
        before_alarm_df = before_alarm_df.sort_values('TimeStamp', ascending=False)
    else:
        before_alarm_df = pd.DataFrame()
    
    return alarm_df, before_alarm_df

def create_main_layout(alarm_df, before_alarm_df):
    return ft.Container(
        content=ft.Row([
            ft.Container(content=create_pre_alarm_table(before_alarm_df), expand=16),
            ft.Container(content=create_alarm_frequency_table(alarm_df), expand=4)
        ], spacing=15),
        margin=ft.margin.only(top=10, bottom=15)
    )

def create_container_with_header(title, content, height=600):
    return ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                padding=10, bgcolor=ft.Colors.BLUE_100,
                border_radius=ft.border_radius.only(top_left=8, top_right=8)
            ),
            ft.Container(
                content=content, padding=10, expand=True, bgcolor=ft.Colors.WHITE,
                border_radius=ft.border_radius.only(bottom_left=8, bottom_right=8)
            )
        ], spacing=0, tight=True),
        height=height, expand=True, border_radius=10, bgcolor=ft.Colors.BLUE_50,
        border=ft.border.all(1, ft.Colors.BLUE_200),
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=5, color=ft.Colors.with_opacity(0.3, ft.Colors.GREY_800), offset=ft.Offset(0, 2))
    )

def create_pre_alarm_table(before_alarm_df):
    if len(before_alarm_df) == 0:
        content = ft.Text("No Pre-Alarm Data Found", text_align=ft.TextAlign.CENTER, size=16, color=ft.Colors.BLUE_300)
    else:
        display_cols = ['LINE', 'PalletID', 'PresentLevel', 'PresentBay', 'AlarmTime', 'Alarm', 'Detail', 'TimeStamp', 'Status', 'Description', 'Duration']
        
        # Add missing columns with N/A values
        for col in ['PalletID', 'PresentLevel', 'PresentBay']:
            if col not in before_alarm_df.columns:
                before_alarm_df[col] = "N/A"

        available_cols = [col for col in display_cols if col in before_alarm_df.columns]
        display_df = before_alarm_df[available_cols].copy()
        
        if 'Alarm' in display_df.columns:
            display_df['Detail'] = display_df['Alarm'].astype(int).map(
                lambda x: Alarm_status_map.get(x, "ไม่ทราบสถานะ")
            )
            alarm_idx = list(display_df.columns).index('Alarm')
            cols = list(display_df.columns)
            if 'Detail' in cols:
                cols.remove('Detail')
            cols.insert(alarm_idx + 1, 'Detail')
            display_df = display_df[cols]
        
        if 'Status' in display_df.columns:
            display_df['Description'] = display_df['Status'].astype(int).map(
                lambda x: Normal_status_map.get(x, "ไม่ทราบสถานะ")
            )
            status_idx = list(display_df.columns).index('Status')
            cols = list(display_df.columns)
            if 'Description' in cols:
                cols.remove('Description')
            cols.insert(status_idx + 1, 'Description')
            display_df = display_df[cols]

        column_display_names = {
            'PresentLevel': 'Level',
            'PresentBay': 'Bay'
        }
        
        header_cells = []
        for col in display_df.columns:
            display_name = column_display_names.get(col, col)
            header_cells.append(
                ft.Container(
                    content=ft.Text(display_name, weight=ft.FontWeight.BOLD, size=14),
                    padding=8,
                    alignment=ft.alignment.center,
                    bgcolor=ft.Colors.GREY_100,
                    border=ft.border.all(1, ft.Colors.GREY_400),
                    width=200 if col in ['Detail', 'Description','AlarmTime', 'TimeStamp'] else 80,
                    height=45
                )
            )
        
        header_row = ft.Row(header_cells, spacing=0)
        
        # Create data rows
        data_rows = []
        for idx, (_, row_data) in enumerate(display_df.iterrows()):
            row_cells = []
            
            # Determine row background color
            row_color = ft.Colors.with_opacity(0.05, ft.Colors.GREY_800) if idx % 2 == 0 else ft.Colors.WHITE
            
            # Special color for alarm rows
            if 'Alarm' in row_data:
                try:
                    alarm_status = int(row_data['Alarm'])
                    for category, codes in ALARM_CATEGORIES.items():
                        if alarm_status in codes:
                            row_color = ft.Colors.with_opacity(0.3, CATEGORY_COLORS[category])
                            break
                except:
                    pass
            
            for col in display_df.columns:
                value = row_data[col]
                
                # Format the value
                if pd.isna(value):
                    cell_text = "NULL"
                elif isinstance(value, pd.Timestamp):
                    cell_text = value.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    cell_text = str(value)
                
                # Determine text color and weight
                text_color = None
                text_weight = None
                
                if col == 'Alarm':
                    text_color = ft.Colors.RED
                    text_weight = ft.FontWeight.BOLD
                elif col == 'Status':
                    try:
                        status_val = int(value)
                        if status_val < 100:
                            text_color = ft.Colors.GREEN
                            text_weight = ft.FontWeight.BOLD
                    except:
                        pass
                
                row_cells.append(
                    ft.Container(
                        content=ft.Text(
                            cell_text, 
                            size=13,
                            color=text_color,
                            weight=text_weight,
                            text_align=ft.TextAlign.CENTER,
                            overflow=ft.TextOverflow.FADE
                        ),
                        padding=8,
                        alignment=ft.alignment.center,
                        bgcolor=row_color,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        width=200 if col in ['Detail', 'Description','AlarmTime', 'TimeStamp'] else 80,
                        height=60
                    )
                )
            
            data_rows.append(ft.Row(row_cells, spacing=0))
        
        sticky_header = ft.Container(
            content=header_row,
            bgcolor=ft.Colors.GREY_100,
            padding=0
        )
        content = ft.Column([
            sticky_header,
            ft.Column(
                data_rows,
                spacing=0,
                expand=True
            )
        ], 
        scroll=ft.ScrollMode.ALWAYS,
        spacing=0,
        expand=True
        )
    
    return create_container_with_header("เหตุการ์ณก่อนเกิด Alarm", content, height=480)

# Renamed function and simplified to just show alarm frequency by line
def create_alarm_frequency_table(alarm_df):
    content = create_alarm_frequency_summary(alarm_df)
    return create_container_with_header("สรุปความถี่การเกิด Alarm", content, height=480)

# New function to create a simplified alarm frequency summary
def create_alarm_frequency_summary(alarm_df):
    CELL_WIDTH = 120
    
    if len(alarm_df) == 0:
        return ft.Text("No alarm data available", size=14, color=ft.Colors.GREY_700)
    
    # Prepare data - count alarms by line
    all_lines = [f"{i:02d}" for i in range(1, 9)]
    srm_lines = {line: f"SRM{line}" for line in all_lines}
    
    line_counts = {line: 0 for line in all_lines}
    status_counts = {}
    
    if 'LINE' in alarm_df.columns and 'Status' in alarm_df.columns:
        alarm_df['LINE_STR'] = alarm_df['LINE'].apply(
            lambda x: f"{int(x):02d}" if isinstance(x, (int, float)) else str(x)
        )
        
        # Count alarms by line
        for _, row in alarm_df.iterrows():
            line, status = row['LINE_STR'], row['Status']
            if line in line_counts:
                line_counts[line] += 1
            
            # Also count by status code for the status breakdown table
            if status not in status_counts:
                status_counts[status] = {'count': 0, 'description': Alarm_status_map.get(status, "Unknown")}
            status_counts[status]['count'] += 1
    
    # Create header for line frequency table
    header_cells = [
        ft.Container(
            width=CELL_WIDTH,
            height=50,
            alignment=ft.alignment.center,
            content=ft.Text("LINE", weight=ft.FontWeight.BOLD, size=14),
            bgcolor=ft.Colors.BLUE_50,
            border=ft.border.all(1, ft.Colors.GREY_400)
        ),
        ft.Container(
            width=CELL_WIDTH,
            height=50,
            alignment=ft.alignment.center,
            content=ft.Text("Alarm Count", weight=ft.FontWeight.BOLD, size=14),
            bgcolor=ft.Colors.BLUE_50,
            border=ft.border.all(1, ft.Colors.GREY_400)
        ),
        ft.Container(
            width=CELL_WIDTH,
            height=50,
            alignment=ft.alignment.center,
            content=ft.Text("Percentage", weight=ft.FontWeight.BOLD, size=14),
            bgcolor=ft.Colors.BLUE_50,
            border=ft.border.all(1, ft.Colors.GREY_400)
        )
    ]
    
    header_row = ft.Row(header_cells, spacing=0, tight=True)
    
    # Create data rows for line frequency
    data_rows = []
    total_alarms = sum(line_counts.values())
    
    for line in all_lines:
        count = line_counts[line]
        if count == 0 and state['line_logs'] != "All":
            continue
            
        percentage = (count / total_alarms * 100) if total_alarms > 0 else 0
        
        row_cells = [
            ft.Container(
                width=CELL_WIDTH,
                height=40,
                alignment=ft.alignment.center,
                content=ft.Text(srm_lines[line], size=14, weight=ft.FontWeight.BOLD),
                border=ft.border.all(1, ft.Colors.GREY_300)
            ),
            ft.Container(
                width=CELL_WIDTH,
                height=40,
                alignment=ft.alignment.center,
                content=ft.Text(
                    str(count), 
                    size=14,
                    weight=ft.FontWeight.BOLD if count > 0 else None,
                    color=ft.Colors.RED if count > 0 else None
                ),
                border=ft.border.all(1, ft.Colors.GREY_300)
            ),
            ft.Container(
                width=CELL_WIDTH,
                height=40,
                alignment=ft.alignment.center,
                content=ft.Text(
                    f"{percentage:.1f}%", 
                    size=14,
                    weight=ft.FontWeight.BOLD if count > 0 else None
                ),
                border=ft.border.all(1, ft.Colors.GREY_300)
            )
        ]
        
        data_rows.append(ft.Row(row_cells, spacing=0, tight=True))
    
    # Create total row
    total_row_cells = [
        ft.Container(
            width=CELL_WIDTH,
            height=40,
            alignment=ft.alignment.center,
            content=ft.Text("Total", size=14, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY_800),
            border=ft.border.all(1, ft.Colors.GREY_300)
        ),
        ft.Container(
            width=CELL_WIDTH,
            height=40,
            alignment=ft.alignment.center,
            content=ft.Text(str(total_alarms), size=14, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY_800),
            border=ft.border.all(1, ft.Colors.GREY_300)
        ),
        ft.Container(
            width=CELL_WIDTH,
            height=40,
            alignment=ft.alignment.center,
            content=ft.Text("100.0%", size=14, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY_800),
            border=ft.border.all(1, ft.Colors.GREY_300)
        )
    ]
    
    total_row = ft.Row(total_row_cells, spacing=0, tight=True)
    
    # Create status breakdown table header
    status_header_cells = [
        ft.Container(
            width=80,
            height=40,
            alignment=ft.alignment.center,
            content=ft.Text("Status", weight=ft.FontWeight.BOLD, size=14),
            bgcolor=ft.Colors.BLUE_50,
            border=ft.border.all(1, ft.Colors.GREY_400)
        ),
        ft.Container(
            width=80,
            height=40,
            alignment=ft.alignment.center,
            content=ft.Text("Count", weight=ft.FontWeight.BOLD, size=14),
            bgcolor=ft.Colors.BLUE_50,
            border=ft.border.all(1, ft.Colors.GREY_400)
        ),
        ft.Container(
            width=200,
            height=40,
            alignment=ft.alignment.center,
            content=ft.Text("Description", weight=ft.FontWeight.BOLD, size=14),
            bgcolor=ft.Colors.BLUE_50,
            border=ft.border.all(1, ft.Colors.GREY_400)
        )
    ]
    
    status_header_row = ft.Row(status_header_cells, spacing=0, tight=True)
    
    # Create status data rows
    status_data_rows = []
    sorted_statuses = sorted(status_counts.items(), key=lambda x: x[1]['count'], reverse=True)
    
    for status, data in sorted_statuses:
        status_row_cells = [
            ft.Container(
                width=80,
                height=35,
                alignment=ft.alignment.center,
                content=ft.Text(str(status), size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
                border=ft.border.all(1, ft.Colors.GREY_300)
            ),
            ft.Container(
                width=80,
                height=35,
                alignment=ft.alignment.center,
                content=ft.Text(str(data['count']), size=14),
                border=ft.border.all(1, ft.Colors.GREY_300)
            ),
            ft.Container(
                width=200,
                height=35,
                alignment=ft.alignment.center,
                content=ft.Text(data['description'], size=13, text_align=ft.TextAlign.CENTER),
                border=ft.border.all(1, ft.Colors.GREY_300)
            )
        ]
        
        status_data_rows.append(ft.Row(status_row_cells, spacing=0, tight=True))
    
    # Combine all rows into columns
    line_frequency_table = ft.Column([header_row] + data_rows + [total_row], spacing=0, tight=True)
    status_breakdown_table = ft.Column([status_header_row] + status_data_rows, spacing=0, tight=True)
    
    # Add titles for each section
    line_frequency_section = ft.Column([
        ft.Container(
            content=ft.Text("จำนวนการเกิด Alarm แยกตาม Line", size=16, weight=ft.FontWeight.BOLD),
            margin=ft.margin.only(bottom=10)
        ),
        line_frequency_table,
        ft.Container(height=20)  # Spacer
    ])
    
    status_breakdown_section = ft.Column([
        ft.Container(
            content=ft.Text("รายละเอียด Alarm Status", size=16, weight=ft.FontWeight.BOLD),
            margin=ft.margin.only(bottom=10)
        ),
        status_breakdown_table
    ])
    
    # Combine both tables into a single column
    combined_content = ft.Column(
        [line_frequency_section, status_breakdown_section],
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )
    
    return combined_content