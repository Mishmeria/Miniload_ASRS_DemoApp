import flet as ft
import sys
import os
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.state import state
from src.filters import apply_filters
from src.ui_components import create_filter_controls, change_page, filter_data_by_type
from views.Status_Detail import ALARM_CATEGORIES, CATEGORY_COLORS

def build_data_table(df):
    if len(df) == 0:
        return ft.Text("No data available", size=14, color=ft.Colors.GREY_700)
    
    display_df = df.copy()
    
    # Function to get alarm category color
    def get_alarm_category_color(status):
        if pd.isna(status):
            return None
        try:
            status_code = int(status)
            for category, codes in ALARM_CATEGORIES.items():
                if status_code in codes:
                    return ft.Colors.with_opacity(0.3, CATEGORY_COLORS[category])
        except:
            pass
        return None
    
    # Define column widths (adjust as needed)
    column_widths = {
            'TimeStamp': 150,
            'LINE': 60,
            'PalletID': 80, 
            'Duration': 80,
            'PresentBay': 60,    
            'Status': 70,
            'Command': 70,  
            'PresentBay': 60,
            'PresentLevel': 60,
            'DistanceX': 100,     
            'DistanceY': 100,
            'PresentBay': 60,
            'AVG_X_Current': 100,
            'AVG_Y_Current': 100,
            'AVG_Z_Current': 100,
            'Max_X_Current': 100,
            'Max_Y_Current': 100,
            'Max_Z_Current': 100,
            'AVG_X_Frequency': 100,
            'AVG_Y_Frequency': 100,
            'AVG_Z_Frequency': 100,
            'Max_X_Frequency': 100,
            'Max_Y_Frequency': 100,
            'Max_Z_Frequency': 100
        }
    
    header_display_names = {
            'TimeStamp': 'TimeStamp',
            'LINE': 'SRM LINE',
            'PalletID': 'PalletID', 
            'Duration': 'ระยะเวลา (ms)', 
            'Status': 'Status',
            'Command': 'CMD',  
            'PresentBay': 'Bay',
            'PresentLevel': 'Level',
            'DistanceX': 'ระยะห่างแกน X (mm)',     
            'DistanceY': 'ระยะห่างแกน Y (mm)',
            'AVG_X_Current': 'กระแสเฉลี่ย X (mA)',
            'AVG_Y_Current': 'กระแสเฉลี่ย Y (mA)',
            'AVG_Z_Current': 'กระแสเฉลี่ย Z (mA)',
            'Max_X_Current': 'กระแสสูงสุด X (mA)',
            'Max_Y_Current': 'กระแสสูงสุด Y (mA)',
            'Max_Z_Current': 'กระแสสูงสุด Z (mA)',
            'AVG_X_Frequency': 'ความถี่เฉลี่ย X (Hz)',
            'AVG_Y_Frequency': 'ความถี่เฉลี่ย Y (Hz)',
            'AVG_Z_Frequency': 'ความถี่เฉลี่ย Z (Hz)',
            'Max_X_Frequency': 'ความถี่สูงสุด X (Hz)',
            'Max_Y_Frequency': 'ความถี่สูงสุด Y (Hz)',
            'Max_Z_Frequency': 'ความถี่สูงสุด Z (Hz)'
        }
    
    # Create header cells with fixed widths and custom names
    header_cells = []
    for col in display_df.columns:
        width = column_widths.get(col, 120)
        display_name = header_display_names.get(col, col)  # Use custom name or original
        
        header_cells.append(
            ft.Container(
                content=ft.Text(
                    display_name, 
                    weight=ft.FontWeight.BOLD, 
                    size=14,
                    text_align=ft.TextAlign.CENTER
                ),
                padding=8,
                alignment=ft.alignment.center,
                bgcolor=ft.Colors.GREY_100,
                border=ft.border.all(1, ft.Colors.GREY_400),
                width=width,
                height=60
            )
        )
    
    header_row = ft.Row(header_cells, spacing=0)
    
    # Create data rows
    data_rows = []
    for idx, (_, row) in enumerate(display_df.iterrows()):
        row_cells = []
        
        # Get row color based on alarm category
        row_color = None
        if 'Status' in row and row['Status'] > 100:
            category_color = get_alarm_category_color(row['Status'])
            if category_color:
                row_color = category_color
        
        # If no alarm category color, use alternating row color
        if not row_color:
            row_color = ft.Colors.with_opacity(0.05, ft.Colors.GREY_800) if idx % 2 == 0 else ft.Colors.WHITE
        
        for col, value in row.items():
            width = column_widths.get(col, 120)
            
            if pd.isna(value):
                cell_text = "NULL"
            elif isinstance(value, pd.Timestamp):
                cell_text = value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                cell_text = str(value)[:50]
            
            # Add special styling for alarm status columns
            text_color = None
            text_weight = None
            if col == 'Status' and not pd.isna(value) and int(value) > 100:
                try:
                    status_code = int(value)
                    for category, codes in ALARM_CATEGORIES.items():
                        if status_code in codes:
                            text_color = CATEGORY_COLORS[category]
                            text_weight = ft.FontWeight.BOLD
                            break
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
                        max_lines=2
                    ),
                    padding=6,
                    alignment=ft.alignment.center,
                    bgcolor=row_color,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    width=width,
                    height=35
                )
            )
        
        data_rows.append(ft.Row(row_cells, spacing=0))
    
    # Create table with frozen header
    table_content = ft.Column([
        # Fixed header
        ft.Container(
            content=header_row,
            padding=0
        ),
        # Scrollable data rows
        ft.Container(
            content=ft.Column(
                data_rows,
                scroll=ft.ScrollMode.ALWAYS,
                spacing=0,
                expand=True
            ),
            expand=True
        )
    ], spacing=0, expand=True)
    
    # Calculate total width for horizontal scrolling
    total_width = sum(column_widths.values())
    
    # Wrap in horizontal scroll container
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=table_content,
                    width=max(total_width, 800),  # Use calculated width or minimum
                )
            ],
            scroll=ft.ScrollMode.ALWAYS,
            expand=True
        ),
        expand=True,
        bgcolor=ft.Colors.WHITE,
        border=ft.border.all(1, ft.Colors.GREY_300)
    )

def create_data_table_view(page):
    # Get data
    df = state['df_logs']
    current_page = state['page_logs']
    line_filter = state['line_logs']
    status_filter = state['status_logs']
    filter_choice = state.get('filter_choice', 'All')
    filtered_df = apply_filters(df, line_filter, status_filter, state['selected_date'], "Logs")
    filtered_df = filter_data_by_type(filtered_df, filter_choice)
    
    start_idx = current_page * state['rows_per_page']
    end_idx = start_idx + state['rows_per_page']
    total_pages = max(1, (len(filtered_df) + state['rows_per_page'] - 1) // state['rows_per_page'])
    current_df = filtered_df.iloc[start_idx:end_idx]
    
    # Create filter controls
    filter_controls = create_filter_controls(
        page=page,
        table_type="ASRS_Logs",
        show_status=True,
        show_refresh=True
    )
    
    # Pagination controls
    pagination_controls = ft.Row([
        ft.ElevatedButton("Previous", icon=ft.Icons.ARROW_BACK, 
                     on_click=lambda e: change_page("ASRS_Logs", -1, page)),
        ft.Text(f"Page {current_page + 1} of {total_pages} | Showing {start_idx + 1}-{min(end_idx, len(filtered_df))} of {len(filtered_df)}"),
        ft.ElevatedButton("Next", icon=ft.Icons.ARROW_FORWARD, 
                     on_click=lambda e: change_page("ASRS_Logs", 1, page))
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    
    data_table = build_data_table(current_df)
    
    return ft.Container(
        content=ft.Column([
            filter_controls,
            ft.Container(height=10),
            pagination_controls,
            ft.Container(height=10),  # Add some spacing
            # Direct table container without nested scrolling
            data_table
        ]), 
        padding=10,
        expand=True
    )