import flet as ft
from datetime import datetime, timedelta
from src.state import state
from src.local_database import load_data #for Cloud use src.database
from views.asrs_logs_view import create_data_table_view as create_asrs_logs_view
from views.statistics_view import create_statistics_view
from views.login_view import create_login_view
from views.chart_view import create_chart_view
from src.ui_components import on_date_change
import threading

# Initialize state variables
state['selected_date'] = datetime.now()
state['logged_in'] = False

def update_view(page, tab_name=None):
    if tab_name is None or tab_name == "รายละเอียด":
        page.tabs["รายละเอียด"].content = ft.Container(
            content=create_asrs_logs_view(page), 
            expand=True
        )
    if tab_name is None or tab_name == "สรุป Alarm":
        page.tabs["สรุป Alarm"].content = ft.Container(
            content=create_statistics_view(page), 
            expand=True
        )
    
    if tab_name is None or tab_name == "กราฟ":
        page.tabs["กราฟ"].content = ft.Container(
            content=create_chart_view(page),
            expand=True
        )
    
    page.update()

def load_data_async(page):
    page.splash.visible = True
    page.update()

    load_data()
    
    page.splash.visible = False
    
    current_tab = page.tabs_control.selected_index
    tab_names = ["กราฟ", "สรุป Alarm", "รายละเอียด"] 
    update_view(page, tab_names[current_tab])

def on_tab_change(e, page):
    tab_index = e.control.selected_index
    tab_names = ["กราฟ", "สรุป Alarm", "รายละเอียด"]

    update_view(page, tab_names[tab_index])

def on_route_change(route, page):
    page.views.clear()
    
    if route.route == "/login" or route.route == "/":
        page.views.append(
            ft.View(
                route="/login",
                controls=[create_login_view(page)],
                padding=0,
                bgcolor=ft.Colors.BLUE_GREY_50
            )
        )
    elif route.route == "/main":
        if not state.get('logged_in', False):
            page.go("/login")
            return
        
        tab_chart = ft.Tab(
            text="กราฟ",
            icon=ft.Icon(name=ft.Icons.BAR_CHART, color=ft.Colors.BLUE),
            content=ft.Container(
                content=ft.Text("Loading..."),
                alignment=ft.alignment.center,
                expand=True
            )
        )
        
        tab_summary = ft.Tab(
            text="สรุป Alarm",
            icon=ft.Icon(name=ft.Icons.ANALYTICS, color=ft.Colors.ORANGE),
            content=ft.Container(
                content=ft.Text("Loading..."),
                alignment=ft.alignment.center,
                expand=True
            )
        )
        
        tab_details = ft.Tab(
            text="รายละเอียด", 
            icon=ft.Icon(name=ft.Icons.TABLE_VIEW, color=ft.Colors.GREEN),
            content=ft.Container(
                content=ft.Text("Loading..."),
                alignment=ft.alignment.center,
                expand=True
            )
        )
    
        page.tabs = {"กราฟ": tab_chart, "สรุป Alarm": tab_summary, "รายละเอียด": tab_details}  # type: ignore
    
        tabs_control = ft.Tabs(
            selected_index=0, 
            animation_duration=300,
            tabs=[tab_chart, tab_summary, tab_details], 
            indicator_color=ft.Colors.BLUE_600,
            on_change=lambda e: on_tab_change(e, page),
            expand=True
        )
        page.tabs_control = tabs_control  # type: ignore
        
        def logout(e):
            state['logged_in'] = False
            page.go("/login")
        
        logout_button = ft.IconButton(
            icon=ft.Icons.LOGOUT,
            tooltip="Logout",
            on_click=logout
        )
        
        main_content = ft.Column([
            ft.Container(
                content=tabs_control,
                expand=True,
                border_radius=8,
                bgcolor=ft.Colors.WHITE,
                border=ft.border.all(1, ft.Colors.GREY_300)
            )
        ], expand=True)
        
        page.views.append(
            ft.View(
                route="/main",
                controls=[main_content],
                padding=20
            )
        )

        threading.Thread(target=lambda: load_data_async(page)).start()

    page.update()

def main(page: ft.Page):
    page.title = "ASRS Database Viewer"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # Create loading indicator
    page.splash = ft.ProgressRing(width=100, height=100, stroke_width=5)  # type: ignore
    page.overlay.append(page.splash)  # type: ignore
    page.splash.visible = False  # type: ignore
    
    # Setup date picker
    page.date_picker = ft.DatePicker(  # type: ignore
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2030, 12, 31),
        on_change=lambda e: on_date_change(e, page)
    )
    page.overlay.append(page.date_picker)  # type: ignore
    
    # Set up routing
    page.on_route_change = lambda route: on_route_change(route, page)
    
    # Start with login page
    page.go("/login")
if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER, host="0.0.0.0", port=7777)  # type: ignore