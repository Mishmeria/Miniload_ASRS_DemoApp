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
    
    # Define column order and widths - this order will be used for display
    column_widths = {
        'CDATE': 150,
        'ASRS': 60,
        'BARCODE': 90, 
        'CHKTYPE': 90,
        'MSGLOG': 250,
        'MSGTYPE': 90,
        'PLCCODE': 90,
        'X_Distance_mm (D57)': 120,
        'Start_Bank (D130)': 100,
        'Start_Pos_mm (D131)': 120,
        'Start_Level_mm (D133)': 120,
        'End_Bank (D134)': 100,
        'End_Position_mm (D135)': 120,
        'End_Level_mm (D137)': 120,
        'Pallet_ID (D138)': 100,
        'Present_Bay_Arm1 (D140)': 120,
        'Present_Level (D145)': 120,
        'Status_Arm1 (D146)': 100,
        'Status (D147)': 100,
        'Command Machine (D148)': 130,
        'Command_X_Pos (D174)': 120,
    }
    
    # Reorder DataFrame columns based on column_widths order
    ordered_columns = [col for col in column_widths.keys() if col in display_df.columns]
    # Add any remaining columns that aren't in column_widths
    remaining_columns = [col for col in display_df.columns if col not in ordered_columns]
    final_column_order = ordered_columns + remaining_columns
    
    # Reorder the DataFrame
    display_df = display_df[final_column_order]
    
    header_display_names = {
        'CDATE': 'CDATE',
        'ASRS': 'SRM LINE'
    }
    
    # Create header cells with fixed widths and custom names in the new order
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
    
    # Create data rows in the new column order
    data_rows = []
    for idx, (_, row) in enumerate(display_df.iterrows()):
        row_cells = []
        
        # Get row color based on alarm category
        row_color = None
        if 'PLCCODE' in row and row['PLCCODE'] > 100:
            category_color = get_alarm_category_color(row['PLCCODE'])
            if category_color:
                row_color = category_color
        
        # If no alarm category color, use alternating row color
        if not row_color:
            row_color = ft.Colors.with_opacity(0.05, ft.Colors.GREY_800) if idx % 2 == 0 else ft.Colors.WHITE
        
        # Process columns in the display order
        for col in display_df.columns:
            value = row[col]
            width = column_widths.get(col, 120)
            
            if pd.isna(value):
                cell_text = "NULL"
            elif isinstance(value, pd.Timestamp):
                cell_text = value.strftime("%Y-%m-%d %H:%M:%S")
            elif col == 'MSGLOG':
                cell_text = str(value)
            else:
                cell_text = str(value)[:50]
            
            # Add special styling for alarm status columns
            text_color = None
            text_weight = None
            if col == 'PLCCODE' and not pd.isna(value) and int(value) > 100:
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
                    height=60
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
    
    # Calculate total width for horizontal scrolling based on ordered columns
    total_width = sum(column_widths.get(col, 120) for col in display_df.columns)
    
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