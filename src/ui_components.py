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
    df = state['df_logs']
    if df is None or len(df) == 0:
        return ["All"]
    filtered_df = apply_filters(df, state['line_logs'], "All", None, "Logs")
    if 'PLCCODE' in filtered_df.columns:
        if filter_type == "Alarm":
            alarm_statuses = filtered_df[filtered_df['PLCCODE'] > 100]['PLCCODE'].dropna().unique().tolist()
            return ["All"] + sorted(alarm_statuses)
        else:
            statuses = filtered_df['PLCCODE'].dropna().unique().tolist()
            return ["All"] + sorted(statuses)
    else:
        return ["All"]

def filter_data_by_type(df, filter_type):
    if df is None or len(df) == 0:
        return df
    if filter_type == "Alarm" and 'PLCCODE' in df.columns:
        return df[df['PLCCODE'] > 100]
    else:
        return df

# ---------- New helpers for date "chips" ----------
def _date_chip(label: str, value: datetime | None, on_tap):
    txt = value.strftime('%Y-%m-%d') if value else 'Select'
    return ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.CALENDAR_MONTH, size=18),
            ft.Text(f"{label}: {txt}", size=14, weight=ft.FontWeight.W_500),
        ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=ft.Colors.BLUE_50,
        border=ft.border.all(1, ft.Colors.BLUE_200),
        border_radius=8,
        on_click=on_tap
    )

def create_filter_controls(page, show_status=True):
    if 'filter_choice' not in state:
        state['filter_choice'] = "All"
    if 'end_date' not in state:
        state['end_date'] = None  # defaults to single-day until user picks end date

    line_filter = state['line_logs']
    status_filter = state['status_logs']
    filter_choice = state['filter_choice']
    status_choices = get_unique_statuses(filter_choice)

    # Left section
    left_controls = []
    left_controls.append(
        create_dropdown(
            "SRM",
            line_filter,
            ["All"] + [str(i) for i in range(1, 9)],
            120,
            lambda e: on_line_filter_change(e, page)
        )
    )
    if show_status:
        left_controls.append(
            create_dropdown(
                "MSGTYPE",
                filter_choice,
                ["All", "Alarm"],
                120,
                lambda e: on_filter_choice_change(e, page)
            )
        )
        left_controls.append(
            create_dropdown(
                'PLCCODE',
                status_filter,
                status_choices,
                120,
                lambda e: on_status_filter_change(e, page)
            )
        )

    # Center section: clickable chips + Apply (no extra text underneath)
    center_controls = ft.Row([
        _date_chip("Start", state.get('selected_date'), lambda e: page.open(page.date_picker)),
        _date_chip("End", state.get('end_date'), lambda e: page.open(page.end_date_picker)),
        create_button(
            "ค้นหา",
            ft.Icons.SEARCH,
            lambda e: apply_date_range(e, page),
            bgcolor=ft.Colors.ORANGE_500,
            color=ft.Colors.WHITE,
            height=40
        ),
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=12)

    # Right section
    right_controls = []
    
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
        ft.Container(content=ft.Row(left_controls, spacing=15), expand=1 ,padding=5),
        ft.Container(content=center_controls, expand=1, alignment=ft.alignment.center,padding=5),
        ft.Container(content=ft.Row(right_controls, alignment=ft.MainAxisAlignment.END),padding=5, expand=1),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

# ---------- Events ----------
def on_line_filter_change(e, page):
    state['line_logs'] = e.control.value
    state['page_logs'] = 0
    from main import update_view
    update_view(page)

def on_filter_choice_change(e, page):
    state['filter_choice'] = e.control.value
    state['status_logs'] = "All"
    state['page_logs'] = 0
    from main import update_view
    update_view(page)

def on_status_filter_change(e, page):
    state['status_logs'] = e.control.value
    state['page_logs'] = 0
    from main import update_view
    update_view(page)

def on_date_change(e, page):
    # Only store; don't load yet (Apply button will load)
    state['selected_date'] = e.control.value
    state['page_loops'] = 0
    state['page_logs'] = 0
    # If end_date is empty, default to same day for UI clarity
    if not state.get('end_date'):
        state['end_date'] = state['selected_date']
    from main import update_view
    update_view(page)

def on_end_date_change(e, page):
    # Only store; don't load yet (Apply button will load)
    state['end_date'] = e.control.value
    state['page_loops'] = 0
    state['page_logs'] = 0
    # If start not set yet, mirror it
    if not state.get('selected_date'):
        state['selected_date'] = state['end_date']
    from main import update_view
    update_view(page)

def apply_date_range(e, page):
    page.splash.visible = True
    page.update()
    try:
        from src.database import load_data
        start = state.get('selected_date')
        end = state.get('end_date') or start
        if not start:
            # no start date chosen; just hide splash and bail
            page.splash.visible = False
            page.snack_bar = ft.SnackBar(ft.Text("Please select a start date."))
            page.snack_bar.open = True
            page.update()
            return
        # load [start, end + 1d)
        load_data(start_date=start, end_date=end + timedelta(days=1))  # type: ignore
        state['page_logs'] = 0
        from main import update_view
        update_view(page)
        page.snack_bar = ft.SnackBar(ft.Text(f"Applied: {start:%Y-%m-%d} → {(end):%Y-%m-%d}"))
        page.snack_bar.open = True
    except Exception as ex:
        page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"))
        page.snack_bar.open = True
    finally:
        page.splash.visible = False
        page.update()

def clear_filter(e, page):
    page.splash.visible = True
    page.update()
    state['page_logs'] = 0
    state['line_logs'] = "All"
    state['status_logs'] = "All"
    state['filter_choice'] = "All"
    # Keep selected_date; clear end_date so it becomes single-day again
    state['end_date'] = None
    from main import update_view
    update_view(page)
    page.splash.visible = False
    page.update()

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
        state['page_logs'] = 0
        state['line_loops'] = "All"
        state['line_logs'] = "All"
        state['status_loops'] = "All"
        state['status_logs'] = "All"
        state['filter_choice'] = "All"
        from src.database import load_data
        start = state.get('selected_date')
        if start:
            end = state.get('end_date') or start
            load_data(start_date=start, end_date=end + timedelta(days=1))
        from main import update_view
        update_view(page)
        page.snack_bar = ft.SnackBar(ft.Text("Data refreshed."))
        page.snack_bar.open = True
    except Exception as ex:
        page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"))
        page.snack_bar.open = True
    finally:
        page.splash.visible = False
        page.update()
