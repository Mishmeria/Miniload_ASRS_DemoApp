import flet as ft
from datetime import datetime, timedelta
from src.state import state
from src.database import load_data
from views.asrs_logs_view import create_data_table_view as create_asrs_logs_view
from views.statistics_view import create_statistics_view
from src.ui_components import on_date_change
import threading

state['selected_date'] = datetime.now()

def update_view(page, tab_name=None):
    if tab_name is None or tab_name == "ASRS_Logs":
        page.tabs["ASRS_Logs"].content = ft.Container(
            content=create_asrs_logs_view(page), 
            expand=True
        )
    
    if tab_name is None or tab_name == "Statistics":
        page.tabs["Statistics"].content = ft.Container(
            content=create_statistics_view(page), 
            expand=True
        )
    
    page.update()

def load_data_async(page):
    page.splash.visible = True
    page.update()
    
    load_data()
    
    page.splash.visible = False
    
    current_tab = page.tabs_control.selected_index
    tab_names = ["ASRS_Logs", "Statistics"] 
    update_view(page, tab_names[current_tab])

def on_tab_change(e, page):
    tab_index = e.control.selected_index
    tab_names = ["ASRS_Logs", "Statistics"]

    update_view(page, tab_names[tab_index])

def main(page: ft.Page):
    page.title = "ASRS Database Viewer"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20

    # Create loading indicator
    page.splash = ft.ProgressRing(width=100, height=100, stroke_width=5) # type: ignore
    page.overlay.append(page.splash) # type: ignore
    page.splash.visible = False # type: ignore
    
    # Setup date picker
    page.date_picker = ft.DatePicker(  # type: ignore
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2030, 12, 31),
        on_change=lambda e: on_date_change(e, page)
        )
    page.overlay.append(page.date_picker)  # type: ignore
    
    
    tab2 = ft.Tab(
        text="ASRS_Logs", 
        icon=ft.Icon(name=ft.Icons.MEMORY, color=ft.Colors.ORANGE),
        content=ft.Container(
            content=ft.Text("Loading..."),
            alignment=ft.alignment.center,
            expand=True
        )
    )
    
    tab3 = ft.Tab(
        text="Statistics",
        icon=ft.Icon(name=ft.Icons.ANALYTICS, color=ft.Colors.ORANGE),
        content=ft.Container(
            content=ft.Text("Loading..."),
            alignment=ft.alignment.center,
            expand=True
        )
    )
    
    # Store tabs for updates
    page.tabs = {"ASRS_Logs": tab2, "Statistics": tab3} # "Predictions": tab4} "TaskLogs": tab1,   # type: ignore
    
    # Create tabs control with lazy loading
    tabs_control = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[tab2, tab3], #tab1 , tab4
        indicator_color=ft.Colors.ORANGE_600,
        on_change=lambda e: on_tab_change(e, page),
        expand=True
    )
    page.tabs_control = tabs_control # type: ignore
    
    # Main layout
    main_content = ft.Column([
        ft.Container(
            content=tabs_control,
            expand=True,
            border_radius=8,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_300)
        )
    ], expand=True)
    
    page.add(main_content)

    # Load data asynchronously after UI is rendered
    threading.Thread(target=lambda: load_data_async(page)).start()

if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER, host="0.0.0.0", port=9999) # type: ignore