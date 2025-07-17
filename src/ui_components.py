import flet as ft
import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.state import state
from src.filters import apply_filters, get_status_stats
from views.Status_Detail import ALARM_CATEGORIES, CATEGORY_COLORS , Alarm_status_map, Normal_status_map

def create_dropdown(label, value, options, width, on_change):
    return ft.Dropdown(
        label=label, value=value,
        options=[ft.dropdown.Option(opt) for opt in options],
        width=width, on_change=on_change
    )

def create_button(text, icon, on_click, bgcolor=None, color=None, height=40):
    style = ft.ButtonStyle(bgcolor=bgcolor) if bgcolor else None
    return ft.ElevatedButton(
        text, icon=icon, on_click=on_click,
        style=style, color=color, height=height
    )

def create_summary_card(title, value, color):
    color_map = {
        "blue": (ft.Colors.BLUE_700, ft.Colors.BLUE_50),
        "green": (ft.Colors.GREEN_700, ft.Colors.GREEN_50),
        "orange": (ft.Colors.ORANGE_700, ft.Colors.ORANGE_50)
    }
    
    text_color, bg_color = color_map.get(color, (ft.Colors.GREY_700, ft.Colors.GREY_50))
    return ft.Container(
        content=ft.Column([
            ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=text_color),
            ft.Text(value, size=24, weight=ft.FontWeight.BOLD)
        ], alignment=ft.MainAxisAlignment.CENTER),
        width=200, height=100, bgcolor=bg_color, border_radius=8, 
        padding=10, alignment=ft.alignment.center
    )

def build_data_table(df):
    if len(df) == 0:
        return ft.Text("No data available", size=14, color=ft.Colors.GREY_700)
    
    display_df = df.copy()
    
    columns = [ft.DataColumn(ft.Text(col, weight=ft.FontWeight.BOLD, size=14), tooltip=col) for col in display_df.columns]
    
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
    
    rows = []
    for idx, (_, row) in enumerate(display_df.iterrows()):
        cells = []
        
        # Get row color based on alarm category
        row_color = None
        if 'Status' in row and row['Status'] > 100:
            category_color = get_alarm_category_color(row['Status'])
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
            if col == 'Status' and not pd.isna(value) and value > 100: # type: ignore
                try:
                    status_code = int(value)
                    for category, codes in ALARM_CATEGORIES.items():
                        if status_code in codes:
                            text_color = CATEGORY_COLORS[category]
                            text_weight = ft.FontWeight.BOLD
                            break
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
    
    return ft.Container(
        content=ft.DataTable(
            columns=columns, rows=rows,
            border=ft.border.all(1, ft.Colors.GREY_400),
            heading_row_color=ft.Colors.GREY_100,
            heading_row_height=40, data_row_min_height=35,
            horizontal_lines=ft.border.BorderSide(1, ft.Colors.GREY_300),
            vertical_lines=ft.border.BorderSide(1, ft.Colors.GREY_300),
            column_spacing=15, divider_thickness=1
        ),
        expand=True
    )

def get_unique_statuses():
    """Get all unique status values from the current dataframe"""
    df = state['df_logs']
    if df is None or len(df) == 0:
        return ["All"]
    
    # Apply line filter but not status filter
    filtered_df = apply_filters(df, state['line_logs'], "All", None, "Logs")
    
    # Get unique status values
    if 'Status' in filtered_df.columns:
        statuses = filtered_df['Status'].dropna().unique().tolist()
        return ["All"] + sorted(statuses)
    else:
        return ["All"]

def create_filter_controls(page, table_type=None, show_status=True, show_refresh=True, title=None):
    """
    Create reusable filter controls for different tabs
    
    Args:
        page: The flet page object
        table_type: "TaskLogs", "ASRS_Logs", "charts", or None for Statistics
        show_status: Whether to show status dropdown
        show_refresh: Whether to show refresh button
        title: Custom title for the controls
    """
    
    # Determine current filters based on table type
    # if table_type == "TaskLogs":
    #     line_filter = state['line_loops']
    #     status_filter = state['status_loops']
    #     status_choices = ["All", "Complete", "Incomplete"]
    if table_type == "ASRS_Logs":
        line_filter = state['line_logs']
        status_filter = state['status_logs']
        status_choices = get_unique_statuses()
    elif table_type == "charts":
        line_filter = state['line_logs']
        status_filter = state['status_logs']
        status_choices = get_unique_statuses()
    else:  # Statistics or other tabs
        line_filter = state['line_logs']
        status_filter = state['status_logs']
        status_choices = ["All", "Alarm", "Work"]
    
    # Date display text
    date_text = f"Selected: {state['selected_date'].strftime('%Y-%m-%d') if state['selected_date'] else 'No date selected'}"
    
    # Left section: LINE and Status filters
    left_controls = []
    
    # LINE dropdown - always show
    left_controls.append(
        create_dropdown(
            "LINE", 
            line_filter, 
            ["All"] + [str(i) for i in range(1, 9)], 
            120, 
            lambda e: on_line_filter_change(e, table_type or "ASRS_Logs", page)
        )
    )
    
    # Status dropdown - conditional
    if show_status:
        left_controls.append(
            create_dropdown(
                "Status", 
                status_filter, 
                status_choices,
                120, 
                lambda e: on_status_filter_change(e, table_type or "ASRS_Logs", page)
            )
        )
    
    # Center section: Date controls
    center_controls = ft.Column([
        ft.Row([
            create_button(
                "Select Date", 
                ft.Icons.CALENDAR_TODAY, 
                lambda e: page.open(page.date_picker), 
                bgcolor=ft.Colors.BLUE_100
            ),
            # create_button(
            #     "Clear Date", 
            #     ft.Icons.CLEAR, 
            #     lambda e: clear_date_filter(e, page), 
            #     bgcolor=ft.Colors.RED_100
            # )
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
        ft.Container(
            content=ft.Text(date_text, size=12, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER),
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            bgcolor=ft.Colors.BLUE_50, 
            border_radius=4,
            alignment=ft.alignment.center
        )
    ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    # Right section: Refresh button
    right_controls = []
    if show_refresh:
        right_controls.append(
            create_button(
                "Refresh Data", 
                ft.Icons.REFRESH, 
                lambda e: refresh_data(e, page),
                bgcolor=ft.Colors.ORANGE_600, 
                color=ft.Colors.WHITE
            )
        )
    
    return ft.Row([
        # Left section
        ft.Container(
            content=ft.Row(left_controls, spacing=15),
            expand=1
        ),
        # Center section
        ft.Container(
            content=center_controls,
            expand=1
        ),
        # Right section
        ft.Container(
            content=ft.Row(right_controls, alignment=ft.MainAxisAlignment.END),
            expand=1
        )
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

# Event handlers
def on_line_filter_change(e, table_type, page):
    # if table_type == "TaskLogs":
    #     state['line_loops'] = e.control.value
    #     state['page_loops'] = 0
    # else:
    state['line_logs'] = e.control.value
    state['page_logs'] = 0

    from main import update_view
    update_view(page)

def on_status_filter_change(e, table_type, page):
    # if table_type == "TaskLogs":
    #     state['status_loops'] = e.control.value
    #     state['page_loops'] = 0
    # else:
    state['status_logs'] = e.control.value
    state['page_logs'] = 0
    
    from main import update_view
    update_view(page)

def on_date_change(e, page):
    # Show loading indicator
    page.splash.visible = True
    page.update()
    
    # Update the selected date in state
    state['selected_date'] = e.control.value
    state['page_loops'] = 0
    state['page_logs'] = 0
    
    date_str = e.control.value.strftime('%Y-%m-%d')
    
    new_url = f"?date={date_str}"
    page.go(new_url)

    from src.Notification import WEBAPP_URL
    full_url = f"{WEBAPP_URL}{new_url}"

    page.snack_bar = ft.SnackBar(
        content=ft.Row([
            ft.Text("Date filter applied. Share this link:"),
            ft.TextButton("Copy URL", on_click=lambda _: page.set_clipboard(full_url))
        ]),
        action="Dismiss",
        on_action=lambda _: None
    )
    page.snack_bar.open = True
    # Reload data from database with the new date filter
    from src.database import load_data
    load_data()
    
    # Hide loading indicator and update the view
    page.splash.visible = False
    from main import update_view
    update_view(page)

def clear_date_filter(e, page):
    # Show loading indicator
    page.splash.visible = True
    page.update()
    
    # Clear the selected date in state
    state['selected_date'] = None
    state['page_loops'] = 0
    state['page_logs'] = 0
    
    # Reload data from database without date filter
    from src.database import load_data
    load_data()
    
    # Hide loading indicator and update the view
    page.splash.visible = False
    from main import update_view
    update_view(page)

def change_page(table_type, direction, page):
    if table_type == "TaskLogs":
        state['page_loops'] = max(0, state['page_loops'] + direction)
    else:
        state['page_logs'] = max(0, state['page_logs'] + direction)
    from main import update_view
    update_view(page)

def refresh_data(e, page):
    page.splash.visible = True
    page.update()
    
    try:
        # Reset state
        state['page_loops'] = 0
        state['page_logs'] = 0
        state['line_loops'] = "All"
        state['line_logs'] = "All"
        state['status_loops'] = "All"
        state['status_logs'] = "All"
        # Note: We don't reset selected_date here to keep the current date filter
        
        from src.database import load_data
        load_data()
        from main import update_view
        update_view(page)
        
        page.splash.visible = False
        page.snack_bar = ft.SnackBar(ft.Text("Data refreshed successfully!"))
        page.snack_bar.open = True
        
    except Exception as ex:
        page.splash.visible = False
        page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"))
        page.snack_bar.open = True
    
    page.update()