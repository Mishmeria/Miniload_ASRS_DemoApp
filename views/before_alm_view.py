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
table_height = 500
cells_width = 180
else_width = 70

# Add pagination state to the cache
stats_cache = {'logs_stats': None, 'alarm_df': None, 'before_alarm_df': None, 'filter_state': None, 'current_page': 0}
rows_per_page = 10  # Number of rows to display per page

def create_task_progress_gauge():
    logs_stats, total = get_status_stats(state['df_logs'], state['line_logs'], state['selected_date'])
    
    if total == 0:
        return ft.Container(
            content=ft.Text("No TaskLogs data available", size=14, color=ft.Colors.GREY_600),
            height=100, alignment=ft.alignment.center,
            bgcolor=ft.Colors.GREY_50, border_radius=8,
            border=ft.border.all(1, ft.Colors.GREY_300)
        )
    
    complete_count = logs_stats[logs_stats["PLCCODE"] <= 100]["Count"].sum()
    incomplete_count = logs_stats[logs_stats["PLCCODE"] > 100]["Count"].sum()

    complete_percent = (complete_count / total) * 100 if total else 0
    
    header = ft.Row([
        ft.Text(f"Logs ทั้งหมด : {total} records", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
        ft.Text(f"Status ปกติ : {complete_count} ครั้ง (คิดเป็น {complete_percent:.1f}% ของวัน)", size=14, color=ft.Colors.GREEN_700),
        ft.Text(f"เกิด Alarm : {incomplete_count} ครั้ง (คิดเป็น {100-complete_percent:.1f}% ของวัน)", size=14, color=ft.Colors.RED_700)
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
        bgcolor=ft.Colors.WHITE, border_radius=5,
        border=ft.border.all(1, ft.Colors.GREY_300)
    )

def create_before_alarm_view(page):
    filter_controls = create_filter_controls(page=page, show_status=False)
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
                logs_stats = logs_stats[logs_stats['PLCCODE'] > 100] if len(logs_stats) > 0 else logs_stats
                alarm_df, before_alarm_df = process_alarm_data()
                
                stats_cache.update({
                    'logs_stats': logs_stats,
                    'alarm_df': alarm_df,
                    'before_alarm_df': before_alarm_df,
                    'filter_state': current_filter_state,
                    'current_page': 0  # Reset to first page when data changes
                }) # type: ignore
            except Exception as e:
                print(f"Error loading statistics data: {e}")
                # Fallback to empty DataFrames if there's an error
                stats_cache.update({
                    'logs_stats': pd.DataFrame(),
                    'alarm_df': pd.DataFrame(),
                    'before_alarm_df': pd.DataFrame(),
                    'filter_state': current_filter_state,
                    'current_page': 0
                }) # type: ignore
        
        try:
            task_gauge = create_task_progress_gauge()
            # Modified to only show the pre-alarm table with pagination
            main_content = create_pre_alarm_table(stats_cache['before_alarm_df'], page)
            
            main_container.content = ft.Column([filter_controls, task_gauge, main_content], expand=True)
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
    
    filtered_df = apply_filters(df, state['line_logs'], "All")
    alarm_df = filtered_df[filtered_df['PLCCODE'] > 100] if 'PLCCODE' in filtered_df.columns else pd.DataFrame()
    
    if len(alarm_df) == 0:
        return alarm_df, pd.DataFrame()
    
    alarm_df = alarm_df.sort_values('CDATE', ascending=False)
    before_alarm_rows = []
    sorted_df = filtered_df.sort_values('CDATE')
    
    for _, alarm_row in alarm_df.iterrows():
        line_value = alarm_row['ASRS']
        alarm_time = alarm_row['CDATE']
        previous_rows = sorted_df[
            (sorted_df['ASRS'] == line_value) & 
            (sorted_df['CDATE'] < alarm_time) &
            (sorted_df['PLCCODE'] < 100)
        ]
        
        if len(previous_rows) > 0:
            previous_row = previous_rows.iloc[-1]
            previous_row = previous_row.copy()
            previous_row['Alarm'] = alarm_row['PLCCODE']
            previous_row['AlarmTime'] = alarm_row['CDATE']
            
            if isinstance(previous_row['CDATE'], pd.Timestamp) and isinstance(alarm_row['CDATE'], pd.Timestamp):
                duration_seconds = (alarm_row['CDATE'] - previous_row['CDATE']).total_seconds()
                previous_row['Duration'] = f"{int(duration_seconds)}"
            else:
                previous_row['Duration'] = "Unknown"
            
            before_alarm_rows.append(previous_row)
    
    if before_alarm_rows:
        before_alarm_df = pd.DataFrame(before_alarm_rows)
        before_alarm_df = before_alarm_df.sort_values('CDATE', ascending=False)
    else:
        before_alarm_df = pd.DataFrame()
    
    return alarm_df, before_alarm_df

def create_container_with_header(title, content, height):
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

# Function to handle page change
def on_page_change(e, page):
    stats_cache['current_page'] = int(e.control.value)
    page.update()
    
    # Reload the table with the new page
    task_gauge = create_task_progress_gauge()
    filter_controls = create_filter_controls(page=page, show_status=False)
    main_content = create_pre_alarm_table(stats_cache['before_alarm_df'], page)
    
    # Find the main container and update it
    for control in page.controls:
        if isinstance(control, ft.Tabs):
            for tab in control.tabs:
                if tab.text == "ก่อนเกิด Alarm":
                    tab.content = ft.Column([filter_controls, task_gauge, main_content], expand=True)
                    break
    page.update()

def create_pre_alarm_table(before_alarm_df, page):
    if len(before_alarm_df) == 0:
        content = ft.Text("No Pre-Alarm Data Found", text_align=ft.TextAlign.CENTER, size=16, color=ft.Colors.BLUE_300)
        return create_container_with_header("เหตุการ์ณก่อนเกิด Alarm", content, table_height)
    
    # Make a copy to avoid modifying the original DataFrame
    display_df = before_alarm_df.copy()
    
    # Add missing columns with N/A values FIRST
    for col in ['BARCODE', 'Present_Level (D145)', 'Present_Bay_Arm1 (D140)']:
        if col not in display_df.columns:
            display_df[col] = "N/A"
    
    # Add Detail column for Alarm status
    if 'Alarm' in display_df.columns:
        display_df['Detail'] = display_df['Alarm'].astype(int).map(
            lambda x: Alarm_status_map.get(x, "ไม่ทราบสถานะ")
        )
    
    # Add Description column for Status
    if 'PLCCODE' in display_df.columns:
        display_df['Description'] = display_df['PLCCODE'].astype(int).map(
            lambda x: Normal_status_map.get(x, "ไม่ทราบสถานะ")
        )
    
    # Define the desired column order
    desired_cols = ['ASRS', 'BARCODE', 'Present_Level (D145)', 'Present_Bay_Arm1 (D140)', 'AlarmTime', 'Alarm', 'Detail', 'CDATE', 'PLCCODE', 'Description', 'Duration']
    
    # Only include columns that exist in the DataFrame
    available_cols = [col for col in desired_cols if col in display_df.columns]
    
    # Select only the available columns in the desired order
    display_df = display_df[available_cols]
    
    # Calculate total pages and implement pagination
    total_rows = len(display_df)
    total_pages = max(1, (total_rows + rows_per_page - 1) // rows_per_page)
    current_page = stats_cache['current_page']
    
    # Ensure current page is valid
    current_page = min(current_page, total_pages - 1)
    current_page = max(0, current_page)
    stats_cache['current_page'] = current_page
    
    # Calculate start and end indices for the current page
    start_idx = current_page * rows_per_page
    end_idx = min(start_idx + rows_per_page, total_rows)
    
    # Get the subset of data for the current page
    page_df = display_df.iloc[start_idx:end_idx]
    
    # Create page dropdown options
    page_options = [
        ft.dropdown.Option(key=str(i), text=f"{i+1}")
        for i in range(total_pages)
    ]
    
    # Create page dropdown
    page_dropdown = ft.Dropdown(
        options=page_options,
        value=str(current_page),
        width=100,
        on_change=lambda e: on_page_change(e, page),
    )
    
    # Create pagination controls
    pagination_controls = ft.Row(
        [
            ft.Row([
                ft.Text("หน้าที่: ", size=16),
                page_dropdown,
                ft.Text(f" แสดงข้อมูลแถวที่ {start_idx + 1} ถึงแถวที่ {end_idx} จากทั้งหมด {total_rows} แถว", size=16),
            ])
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )
    
    # INCREASED column widths to make table wider
    column_widths = {
        'ASRS': 80,
        'BARCODE': 120,
        'Present_Level (D145)': 80, 
        'Present_Bay_Arm1 (D140)': 80,   
        'AlarmTime': 180,    
        'Alarm': 100,
        'Detail': 300,       
        'CDATE': 180,  
        'PLCCODE': 100,
        'Description': 250,  
        'Duration': 150      
    }
    
    # Calculate total table width
    total_width = sum(column_widths.get(col, 100) for col in page_df.columns)
    
    # Column display names mapping
    column_display_names = {
        'BARCODE': 'BARCODE',
        'Present_Level (D145)': 'Level',
        'Present_Bay_Arm1 (D140)': 'Bay',
        'AlarmTime': 'เวลาที่เกิด Alarm',
        'CDATE': 'เวลาของ Status ล่าสุดก่อนเกิด Alarm',
        'Duration': 'ระยะเวลาก่อนเกิด Alarm (วินาที)' 
    }
    
    # Create header cells
    header_cells = []
    for col in page_df.columns:
        display_name = column_display_names.get(col, col)
        width = column_widths.get(col, 100)
        
        header_cells.append(
            ft.Container(
                content=ft.Text(
                    display_name, 
                    weight=ft.FontWeight.BOLD, 
                    size=13,
                    text_align=ft.TextAlign.CENTER
                ),
                padding=8,
                alignment=ft.alignment.center,
                bgcolor=ft.Colors.GREY_100,
                border=ft.border.all(1, ft.Colors.GREY_400),
                width=width,
                height=80
            )
        )
    
    # Create data rows
    data_rows = []
    for idx, (_, row_data) in enumerate(page_df.iterrows()):
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
        
        for col in page_df.columns:
            value = row_data[col]
            width = column_widths.get(col, 100)
            
            # Format the value
            if pd.isna(value):
                cell_text = "NULL"
            elif isinstance(value, pd.Timestamp):
                cell_text = value.strftime("%m-%d %H:%M:%S")
            else:
                cell_text = str(value)
            
            # Determine text color and weight
            text_color = None
            text_weight = None
            font_size = 12
            
            if col == 'Alarm':
                text_color = ft.Colors.RED
                text_weight = ft.FontWeight.BOLD
            elif col == 'PLCCODE':
                try:
                    status_val = int(value)
                    if status_val < 100:
                        text_color = ft.Colors.GREEN
                        text_weight = ft.FontWeight.BOLD
                except:
                    pass
            elif col == 'Duration':
                text_color = ft.Colors.BLUE_700
                text_weight = ft.FontWeight.BOLD
            
            row_cells.append(
                ft.Container(
                    content=ft.Text(
                        cell_text, 
                        size=font_size,
                        color=text_color,
                        weight=text_weight,
                        text_align=ft.TextAlign.CENTER,
                        max_lines=2,
                        selectable=True
                    ),
                    padding=6,
                    alignment=ft.alignment.center,
                    bgcolor=row_color,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    width=width,
                    height=40
                )
            )
        
        data_rows.append(ft.Row(row_cells, spacing=0))
    
    # Create the table structure with proper scrolling
    # Fixed header row
    header_row = ft.Row(header_cells, spacing=0)
    
    # Scrollable data rows
    data_container = ft.Container(
        content=ft.Column(
            data_rows,
            spacing=0,
        ),
        width=total_width,  # Set explicit width for the data container
    )
    
    # Main table content with vertical scroll for data
    table_content = ft.Column([
        # Fixed header (no scroll)
        ft.Container(
            content=header_row,
            width=total_width,  # Match the data width
        ),
        # Scrollable data area with fixed height
        ft.Container(
            content=ft.Column([
                data_container
            ], scroll=ft.ScrollMode.AUTO),
            height=400,  # Fixed height to enable vertical scrolling
            width=total_width,
        )
    ], spacing=0)
    
    # Wrap everything in horizontal scroll if table is wider than container
    table_with_scroll = ft.Container(
        content=ft.Row([
            table_content
        ], scroll=ft.ScrollMode.AUTO),  # Enable horizontal scroll
        expand=True,
    )
    
    # Combine pagination controls with the table
    content = ft.Column([
        pagination_controls,
        table_with_scroll
    ])
    
    return create_container_with_header("เหตุการ์ณก่อนเกิด Alarm", content, table_height)