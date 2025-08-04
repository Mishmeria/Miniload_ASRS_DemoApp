import flet as ft
import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime, timedelta
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

def get_unique_statuses(filter_type="All"):
    """Get all unique status values from the current dataframe"""
    df = state['df_logs']
    if df is None or len(df) == 0:
        return ["All"]
    
    # Apply line filter but not status filter
    filtered_df = apply_filters(df, state['line_logs'], "All", None, "Logs")
    
    if 'PLCCODE' in filtered_df.columns:
        if filter_type == "Alarm":
            # Filter for status > 100 (alarm statuses)
            alarm_statuses = filtered_df[filtered_df['PLCCODE'] > 100]['PLCCODE'].dropna().unique().tolist()
            return ["All"] + sorted(alarm_statuses)
        else:
            # Get all statuses
            statuses = filtered_df['PLCCODE'].dropna().unique().tolist()
            return ["All"] + sorted(statuses)
    else:
        return ["All"]

def filter_data_by_type(df, filter_type):
    """Filter data based on filter type"""
    if df is None or len(df) == 0:
        return df
    
    if filter_type == "Alarm" and 'PLCCODE' in df.columns:
        return df[df['PLCCODE'] > 100]
    else:
        return df
    
def create_filter_controls(page, table_type=None, show_status=True, show_refresh=True, title=None):

    if 'filter_choice' not in state:
        state['filter_choice'] = "All"
    
    # Initialize time filter states if not present
    if 'start_time' not in state:
        state['start_time'] = "All"
    if 'end_time' not in state:
        state['end_time'] = "All"
    if 'time_filter_active' not in state:
        state['time_filter_active'] = False

    line_filter = state['line_logs']
    status_filter = state['status_logs']
    filter_choice = state['filter_choice']
    status_choices = get_unique_statuses(filter_choice)
    
    # Generate time options for dropdowns (hourly from 08:00 to 18:00 for start, 09:00 to 19:00 for end)
    start_time_options = ["All"] + [f"{hour:02d}:00" for hour in range(8, 19)]
    end_time_options = ["All"] + [f"{hour:02d}:00" for hour in range(9, 20)]
    
    # Date display text
    date_text = f"Selected: {state['selected_date'].strftime('%Y-%m-%d') if state['selected_date'] else 'No date selected'}"
    
    # Left section: LINE and Status filters
    left_controls = []
    
    # LINE dropdown - always show
    left_controls.append(
        create_dropdown(
            "SRM", 
            line_filter, 
            ["All"] + [str(i) for i in range(1, 9)], 
            120, 
            lambda e: on_line_filter_change(e, table_type or "ASRS_Logs", page)
        )
    )
    
    if show_status:
        left_controls.append(
            create_dropdown(
                "MSGTYPE", 
                filter_choice, 
                ["All", "Alarm"],
                120, 
                lambda e: on_filter_choice_change(e, table_type or "ASRS_Logs", page)
            )
        )

    # Status dropdown - conditional
    if show_status:
        left_controls.append(
            create_dropdown(
                'PLCCODE', 
                status_filter, 
                status_choices,
                120, 
                lambda e: on_status_filter_change(e, table_type or "ASRS_Logs", page)
            )
        )
    
    # Center section: Date and Time controls
    center_controls = ft.Column([
        # Single row with DatePicker, TimeStart, TimeEnd, and Apply button
        ft.Row([
            create_button(
                "Select Date", 
                ft.Icons.CALENDAR_TODAY, 
                lambda e: page.open(page.date_picker), 
                bgcolor=ft.Colors.BLUE_100
            ),
            create_dropdown(
                "Start Time", 
                state['start_time'], 
                start_time_options,
                120, 
                lambda e: on_start_time_change(e, page)
            ),
            create_dropdown(
                "End Time", 
                state['end_time'], 
                end_time_options,
                120, 
                lambda e: on_end_time_change(e, page)
            ),
            create_button(
                "Apply Time Filter", 
                ft.Icons.ACCESS_TIME, 
                lambda e: apply_time_filter(e, page),
                bgcolor=ft.Colors.GREEN_100 if state.get('time_filter_active', False) else ft.Colors.GREY_300,
                height=40
            ),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
        
        # Status display showing selected date and time range
        ft.Container(
            content=ft.Text(
                f"{date_text} in range {state['start_time']} to {state['end_time']}" if state.get('time_filter_active', False) else f"{date_text} - Time Filter: OFF",
                size=14, 
                weight=ft.FontWeight.W_500, 
                text_align=ft.TextAlign.CENTER,
                color=ft.Colors.BLUE_700 if state.get('time_filter_active', False) else ft.Colors.GREY_700
            ),
            padding=ft.padding.symmetric(horizontal=15, vertical=8),
            bgcolor=ft.Colors.GREEN_50 if state.get('time_filter_active', False) else ft.Colors.GREY_100, 
            border_radius=6,
            alignment=ft.alignment.center,
            border=ft.border.all(1, ft.Colors.GREEN_300 if state.get('time_filter_active', False) else ft.Colors.GREY_300),
            visible=True  # Always show the status
        )
    ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
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

    right_controls.append(
            create_button(
                "Clear Filter", 
                ft.Icons.CLEAR, 
                lambda e: clear_filter(e, page),
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
    state['line_logs'] = e.control.value
    state['page_logs'] = 0

    from main import update_view
    update_view(page)

def on_filter_choice_change(e, table_type, page):
    # Update the filter choice in state
    state['filter_choice'] = e.control.value
    
    # Reset status filter to "All" when changing filter type
    state['status_logs'] = "All"
    state['page_logs'] = 0
    
    from main import update_view
    update_view(page)

def on_status_filter_change(e, table_type, page):
    state['status_logs'] = e.control.value
    state['page_logs'] = 0
    
    from main import update_view
    update_view(page)

def on_start_time_change(e, page):
    state['start_time'] = e.control.value
    
    # If end time is "All" or start time is after end time, adjust end time
    if state['end_time'] == "All" and state['start_time'] != "All":
        # Set end time to one hour after start time or 19:00 (max)
        start_hour = int(state['start_time'].split(':')[0])
        end_hour = min(start_hour + 1, 19)
        state['end_time'] = f"{end_hour:02d}:00"
    elif state['start_time'] != "All" and state['end_time'] != "All":
        # Check if start time is after end time
        start_hour = int(state['start_time'].split(':')[0])
        end_hour = int(state['end_time'].split(':')[0])
        if start_hour >= end_hour:
            # Adjust end time to be at least one hour after start time
            end_hour = min(start_hour + 1, 19)
            state['end_time'] = f"{end_hour:02d}:00"
    
    # Deactivate time filter when changing selection
    state['time_filter_active'] = False
    
    from main import update_view
    update_view(page)

def on_end_time_change(e, page):
    state['end_time'] = e.control.value
    
    # If start time is "All" or end time is before start time, adjust start time
    if state['start_time'] == "All" and state['end_time'] != "All":
        # Set start time to one hour before end time or 08:00 (min)
        end_hour = int(state['end_time'].split(':')[0])
        start_hour = max(end_hour - 1, 8)
        state['start_time'] = f"{start_hour:02d}:00"
    elif state['start_time'] != "All" and state['end_time'] != "All":
        # Check if end time is before start time
        start_hour = int(state['start_time'].split(':')[0])
        end_hour = int(state['end_time'].split(':')[0])
        if end_hour <= start_hour:
            # Adjust start time to be at least one hour before end time
            start_hour = max(end_hour - 1, 8)
            state['start_time'] = f"{start_hour:02d}:00"
    
    # Deactivate time filter when changing selection
    state['time_filter_active'] = False
    
    from main import update_view
    update_view(page)

def apply_time_filter(e, page):
    # Show loading indicator
    page.splash.visible = True
    page.update()
    
    # Only activate if both start and end times are selected
    if state['start_time'] != "All" and state['end_time'] != "All":
        # Toggle the time filter state
        state['time_filter_active'] = True
        state['page_logs'] = 0
        
        page.snack_bar = ft.SnackBar(
            content=ft.Row([
                ft.Text(f"Time filter applied: {state['start_time']} - {state['end_time']}"),
            ]),
            action="Dismiss",
            on_action=lambda _: None
        )
    else:
        # Notify user that both times need to be selected
        page.snack_bar = ft.SnackBar(
            content=ft.Row([
                ft.Text("Please select both start and end times to apply the filter."),
            ]),
            action="Dismiss",
            on_action=lambda _: None
        )
    
    page.snack_bar.open = True
    
    # Hide loading indicator and update the view
    page.splash.visible = False
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
    
    # new_url = f"?date={date_str}"
    # page.go(new_url)

    page.snack_bar = ft.SnackBar(
        content=ft.Row([
            ft.Text("Date filter applied."),
        ]),
        action="Dismiss",
        on_action=lambda _: None
    )
    page.snack_bar.open = True
    # Reload data from database with the new date filter
    from src.database import load_data #change to src.database for cloud
    load_data(start_date=state['selected_date'], end_date=state['selected_date'] + timedelta(days=1))
    
    # Hide loading indicator and update the view
    page.splash.visible = False
    from main import update_view
    update_view(page)

def clear_filter(e, page):
    # Show loading indicator
    page.splash.visible = True
    page.update()
    
    # Clear all filters
    state['page_logs'] = 0
    state['line_logs'] = "All"
    state['status_logs'] = "All"
    state['filter_choice'] = "All"
    state['start_time'] = "All"
    state['end_time'] = "All"
    state['time_filter_active'] = False
    
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
        state['page_logs'] = 0
        state['line_loops'] = "All"
        state['line_logs'] = "All"
        state['status_loops'] = "All"
        state['status_logs'] = "All"
        state['filter_choice'] = "All"
        state['start_time'] = "All"
        state['end_time'] = "All"
        state['time_filter_active'] = False
        # Note: We don't reset selected_date here to keep the current date filter
        
        from src.database import load_data
        load_data(start_date=state['selected_date'], end_date=state['selected_date'] + timedelta(days=1))
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