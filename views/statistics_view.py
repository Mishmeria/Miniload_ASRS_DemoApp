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
from src.charts import create_task_progress_gauge

from views.Status_Detail import Alarm_status_map, Normal_status_map , ALARM_CATEGORIES , CATEGORY_COLORS

# Alarm categories

stats_cache = {'logs_stats': None, 'alarm_df': None, 'before_alarm_df': None, 'filter_state': None}

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
            ft.Container(content=create_pre_alarm_table(before_alarm_df), expand=6),
            ft.Container(content=create_alarm_categories_table(alarm_df), expand=4)
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
        
        # Create the data table first
        data_table = create_data_table(display_df, is_alarm_table=False)
        
        # Wrap it in a scrollable container with fixed height
        content = ft.Column(
            [data_table],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
    
    return create_container_with_header("Pre-Alarm Events Analysis", content, height=480)

def create_alarm_categories_table(alarm_df):
    content = create_alarm_categories_matrix(alarm_df)
    # Adjusted height to fit better on screen
    return create_container_with_header("Alarm Categories by LINE", content, height=480)

def create_alarm_categories_matrix(alarm_df):
    # Adjusted cell width for better fit
    CELL_WIDTH = 90
    
    if len(alarm_df) == 0:
        return ft.Text("No alarm data available", size=14, color=ft.Colors.GREY_700)
    
    all_lines = [f"{i:02d}" for i in range(1, 9)]  # Use "01", "02", ..., "08"
    line_counts = {line: {cat: 0 for cat in ALARM_CATEGORIES} for line in all_lines}
    
    if 'LINE' in alarm_df.columns and 'Status' in alarm_df.columns:
        alarm_df['LINE_STR'] = alarm_df['LINE'].apply(
            lambda x: f"{int(x):02d}" if isinstance(x, (int, float)) else str(x)
        )
        
        for _, row in alarm_df.iterrows():
            line, status = row['LINE_STR'], row['Status']
            if line in line_counts:
                for cat, codes in ALARM_CATEGORIES.items():
                    if status in codes:
                        line_counts[line][cat] += 1
                        break
    
    # Create fixed-width columns with custom containers
    header_cells = []
    
    # LINE header cell
    header_cells.append(
        ft.Container(
            width=CELL_WIDTH,
            height=50,
            alignment=ft.alignment.center,
            content=ft.Text("LINE", weight=ft.FontWeight.BOLD, size=14),
            bgcolor=ft.Colors.BLUE_50,
            border=ft.border.all(1, ft.Colors.GREY_400)
        )
    )
    
    # Category header cells with different background colors based on category
    for cat in ALARM_CATEGORIES:
        # Use a lighter version of the category color for the header background
        header_bg_color = ft.Colors.with_opacity(0.2, CATEGORY_COLORS[cat])
        
        header_cells.append(
            ft.Container(
                width=CELL_WIDTH,
                height=50,
                alignment=ft.alignment.center,
                content=ft.Row([
                    ft.Text(cat, weight=ft.FontWeight.BOLD, size=14, color=CATEGORY_COLORS[cat])
                ], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor=header_bg_color,  # Use category-specific color
                border=ft.border.all(1, ft.Colors.GREY_400)
            )
        )
    
    # Total header cell
    header_cells.append(
        ft.Container(
            width=CELL_WIDTH,
            height=50,
            alignment=ft.alignment.center,
            content=ft.Text("Total", weight=ft.FontWeight.BOLD, size=14),
            bgcolor=ft.Colors.BLUE_50,
            border=ft.border.all(1, ft.Colors.GREY_400)
        )
    )
    
    # Rest of the function remains unchanged
    # Create header row
    header_row = ft.Row(header_cells, spacing=0, tight=True)
    
    # Create data rows
    data_rows = []
    for line in all_lines:
        line_total = sum(line_counts[line].values())
        if line_total == 0 and state['line_logs'] != "All":
            continue
        
        row_cells = []
        
        # LINE cell
        row_cells.append(
            ft.Container(
                width=CELL_WIDTH,
                height=40,
                alignment=ft.alignment.center,
                content=ft.Text(line, size=14, weight=ft.FontWeight.BOLD),
                border=ft.border.all(1, ft.Colors.GREY_300)
            )
        )
        
        # Category cells
        for cat in ALARM_CATEGORIES:
            count = line_counts[line][cat]
            row_cells.append(
                ft.Container(
                    width=CELL_WIDTH,
                    height=40,
                    alignment=ft.alignment.center,
                    content=ft.Text(
                        str(count), 
                        size=14, 
                        weight=ft.FontWeight.BOLD if count > 0 else None, 
                        color=CATEGORY_COLORS[cat] if count > 0 else None
                    ),
                    border=ft.border.all(1, ft.Colors.GREY_300)
                )
            )
        
        # Total cell
        row_cells.append(
            ft.Container(
                width=CELL_WIDTH,
                height=40,
                alignment=ft.alignment.center,
                content=ft.Text(str(line_total), size=14, weight=ft.FontWeight.BOLD),
                border=ft.border.all(1, ft.Colors.GREY_300)
            )
        )
        
        data_rows.append(ft.Row(row_cells, spacing=0, tight=True))
    
    # Create total row
    total_row_cells = []
    
    # "Total" label cell
    total_row_cells.append(
        ft.Container(
            width=CELL_WIDTH,
            height=40,
            alignment=ft.alignment.center,
            content=ft.Text("Total", size=14, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY_800),
            border=ft.border.all(1, ft.Colors.GREY_300)
        )
    )
    
    # Calculate column totals
    column_totals = {cat: sum(line_counts[line][cat] for line in all_lines) for cat in ALARM_CATEGORIES}
    
    # Category total cells
    for cat in ALARM_CATEGORIES:
        total_row_cells.append(
            ft.Container(
                width=CELL_WIDTH,
                height=40,
                alignment=ft.alignment.center,
                content=ft.Text(
                    str(column_totals[cat]), 
                    size=14, 
                    weight=ft.FontWeight.BOLD, 
                    color=CATEGORY_COLORS[cat] if column_totals[cat] > 0 else None
                ),
                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY_800),
                border=ft.border.all(1, ft.Colors.GREY_300)
            )
        )
    
    # Grand total cell
    total_row_cells.append(
        ft.Container(
            width=CELL_WIDTH,
            height=40,
            alignment=ft.alignment.center,
            content=ft.Text(str(sum(column_totals.values())), size=14, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY_800),
            border=ft.border.all(1, ft.Colors.GREY_300)
        )
    )
    
    total_row = ft.Row(total_row_cells, spacing=0, tight=True)
    
    # Combine all rows into a column
    all_rows = [header_row] + data_rows + [total_row]
    table_content = ft.Column(all_rows, spacing=0, tight=True)
    
    # Create a scrollable container for horizontal scrolling if needed
    scrollable_container = ft.Column(
        [table_content],
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )
    
    return scrollable_container

def create_data_table(df, is_alarm_table=False):
    if len(df) == 0:
        return ft.Text("No data available", size=14, color=ft.Colors.GREY_700)
    
    display_df = df.copy()
    
    # Add status descriptions in correct order
    if 'Status' in display_df.columns:
        status_map_to_use = Alarm_status_map if is_alarm_table else Normal_status_map
        display_df['Description'] = display_df['Status'].astype(int).map(
            lambda x: status_map_to_use.get(x, "ไม่ทราบสถานะ")
        )
        # Reorder columns to put StatusDescription after Status
        status_idx = list(display_df.columns).index('Status')
        cols = list(display_df.columns)
        if 'Description' in cols:
            cols.remove('Description')
        cols.insert(status_idx + 1, 'Description')
        display_df = display_df[cols]
    
    if 'Alarm' in display_df.columns:
        display_df['Detail'] = display_df['Alarm'].astype(int).map(
            lambda x: Alarm_status_map.get(x, "ไม่ทราบสถานะ")
        )
        # Reorder columns to put Alarm Description after AlarmStatus
        status_idx = list(display_df.columns).index('Alarm')
        cols = list(display_df.columns)
        if 'Detail' in cols:
            cols.remove('Detail')
        cols.insert(status_idx + 1, 'Detail')
        display_df = display_df[cols]
    
    column_display_names = {
        'PresentLevel': 'Level',
        'PresentBay': 'Bay'
    }
    columns = []
    for col in display_df.columns:
        display_name = column_display_names.get(col, col)  # Use mapping if exists, otherwise use original name
        columns.append(ft.DataColumn(
            ft.Text(display_name, weight=ft.FontWeight.BOLD, size=14), 
            tooltip=col  # Keep original name in tooltip for reference
        ))

    # Function to get alarm category color
    def get_alarm_category_color(alarm_status):
        if pd.isna(alarm_status):
            return None
        try:
            status_code = int(alarm_status)
            for category, codes in ALARM_CATEGORIES.items():
                if status_code in codes:
                    return ft.Colors.with_opacity(0.3, CATEGORY_COLORS[category])
        except:
            pass
        return None
    
    rows = []
    for idx, (_, row) in enumerate(display_df.iterrows()):
        cells = []
        
        # Get row color based on alarm category
        row_color = None
        if 'Alarm' in row:
            category_color = get_alarm_category_color(row['Alarm'])
            if category_color:
                row_color = category_color
        
        # If no alarm category color, use alternating row color
        if not row_color:
            row_color = ft.Colors.with_opacity(0.05, ft.Colors.GREY_800) if idx % 2 == 0 else None
        
        for col, value in row.items():
            if pd.isna(value):
                cell_text = "NULL"
            elif isinstance(value, pd.Timestamp):
                cell_text = value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                cell_text = str(value)[:50]
            
            # Add special styling for alarm status columns
            text_color = None
            text_weight = None
            if col == 'Alarm' and not pd.isna(value):
                try:
                    status_code = int(value)
                    for category, codes in ALARM_CATEGORIES.items():
                        if status_code in codes:
                            text_weight = ft.FontWeight.BOLD
                            text_color = ft.Colors.RED
                            break
                except:
                    pass
            elif col == 'Status' and not pd.isna(value):
                try :
                    status_code = int(value)
                    text_weight = ft.FontWeight.BOLD
                    text_color = ft.Colors.GREEN
                except:
                    pass
            
            cells.append(ft.DataCell(ft.Text(
                cell_text, 
                size=13, 
                color=text_color,
                weight=text_weight
            )))
        
        rows.append(ft.DataRow(
            cells=cells,
            color=row_color
        ))
    
    return ft.DataTable(
        columns=columns, rows=rows,
        border=ft.border.all(1, ft.Colors.GREY_400),
        heading_row_color=ft.Colors.GREY_100,
        heading_row_height=40, data_row_min_height=35,
        horizontal_lines=ft.border.BorderSide(1, ft.Colors.GREY_300),
        vertical_lines=ft.border.BorderSide(1, ft.Colors.GREY_300),
        column_spacing=15, divider_thickness=1
    )