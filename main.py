import flet as ft
from datetime import datetime, timedelta
from src.state import state
from src.database import load_data
#from views.task_logs_view import create_data_table_view as create_task_logs_view
from views.asrs_logs_view import create_data_table_view as create_asrs_logs_view
from views.statistics_view import create_statistics_view
#from views.prediction_view import create_prediction_view
from src.ui_components import on_date_change
import threading

state['selected_date'] = datetime.now()

def parse_query_string(route):
    """Parse query string parameters from route"""
    query_params = {}
    if '?' in route:
        query_string = route.split('?', 1)[1]
        params = query_string.split('&')
        for param in params:
            if '=' in param:
                key, value = param.split('=', 1)
                query_params[key] = value
    return query_params

def handle_url_params(page):
    """Handle URL parameters and set filters accordingly"""
    if not page.route:
        return
        
    query_params = parse_query_string(page.route)
    
    # Handle date parameter
    if 'date' in query_params:
        try:
            date_str = query_params['date']
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            state['selected_date'] = date_obj
            
            # Update date picker to reflect the URL parameter
            if hasattr(page, 'date_picker'):
                page.date_picker.value = date_obj
                
            # Show notification that filter was applied from URL
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Date filter applied from URL: {date_str}"),
                action="OK",
                on_action=lambda _: None
            )
            page.snack_bar.open = True
            page.update()
        except ValueError:
            print(f"Invalid date format in URL: {query_params['date']}")
    
    # Handle other parameters as needed (line, status, etc.)
    if 'line' in query_params:
        line_value = query_params['line']
        if line_value in ["All"] + [str(i) for i in range(1, 9)]:
            state['line_logs'] = line_value
            state['line_loops'] = line_value
    
    if 'status' in query_params:
        status_value = query_params['status']
        state['status_logs'] = status_value
        state['status_loops'] = status_value

def on_route_change(route, page):
    """Handle route changes"""
    handle_url_params(page)

def update_view(page, tab_name=None):
    """Update specific tab or all tab contents when filters change"""
    # if tab_name is None or tab_name == "TaskLogs":
    # # Update TaskLogs tab
    #     page.tabs["TaskLogs"].content = ft.Container(
    #         content=create_task_logs_view(page), 
    #         expand=True
    #     )
    
    if tab_name is None or tab_name == "ASRS_Logs":
    # Update ASRS_Logs tab
        page.tabs["ASRS_Logs"].content = ft.Container(
            content=create_asrs_logs_view(page), 
            expand=True
        )
    
    if tab_name is None or tab_name == "Statistics":
    # Update Statistics tab 
        page.tabs["Statistics"].content = ft.Container(
            content=create_statistics_view(page), 
            expand=True
        )
    
    # if tab_name is None or tab_name == "Predictions":
    # # Update Predictions tab with the new charts
    #     page.tabs["Predictions"].content = ft.Container(
    #         content=create_prediction_view(page), 
    #         expand=True
    #     )

    page.update()

def load_data_async(page):
    """Load data asynchronously and update UI when done"""
    # Show loading indicator
    page.splash.visible = True
    page.update()
    
    # Load data
    load_data()
    
    # Hide loading indicator and update initial view
    page.splash.visible = False
    
    # Initialize only the first tab content to speed up initial loading
    current_tab = page.tabs_control.selected_index
    tab_names = ["ASRS_Logs", "Statistics"] #"Predictions"]"TaskLogs", 
    update_view(page, tab_names[current_tab])

def on_tab_change(e, page):
    """Load tab content only when tab is selected"""
    tab_index = e.control.selected_index
    tab_names = ["ASRS_Logs", "Statistics"] # "Predictions"]"TaskLogs", 
    
    # Only update the selected tab
    update_view(page, tab_names[tab_index])

def main(page: ft.Page):
    page.title = "ASRS Database Viewer"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1600  # type: ignore
    page.window_height = 900  # type: ignore
    page.padding = 20
    
    page.on_route_change = lambda route: on_route_change(route, page)
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
    
    # Create empty placeholder tabs initially
    # tab1 = ft.Tab(
    #     text="TaskLogs",
    #     icon=ft.Icon(name=ft.Icons.TABLE_CHART, color=ft.Colors.ORANGE),
    #     content=ft.Container(
    #         content=ft.ProgressRing(width=40, height=40),
    #         alignment=ft.alignment.center,
    #         expand=True
    #     )
    # )
    
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

    # tab4 = ft.Tab(
    #     text="Time Series",
    #     icon=ft.Icon(name=ft.Icons.TIMELINE, color=ft.Colors.BLUE),
    #     content=ft.Container(
    #         content=ft.Text("Loading..."),
    #         alignment=ft.alignment.center,
    #         expand=True
    #     )
    # )
    
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

    handle_url_params(page)
    # Load data asynchronously after UI is rendered
    threading.Thread(target=lambda: load_data_async(page)).start()

if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER, host="0.0.0.0", port=6969) # type: ignore