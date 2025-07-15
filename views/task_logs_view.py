import flet as ft
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.state import state
from src.filters import apply_filters
from src.ui_components import create_filter_controls, build_data_table, change_page

def create_data_table_view(page):
    # Get data
    df = state['df_loops']
    current_page = state['page_loops']
    line_filter = state['line_loops']
    status_filter = state['status_loops']
    filtered_df = apply_filters(df, line_filter, status_filter, state['selected_date'], "TaskLoops")

    start_idx = current_page * state['rows_per_page']
    end_idx = start_idx + state['rows_per_page']
    total_pages = max(1, (len(filtered_df) + state['rows_per_page'] - 1) // state['rows_per_page'])
    current_df = filtered_df.iloc[start_idx:end_idx]
    
    # Create filter controls
    filter_controls = create_filter_controls(
        page=page,
        table_type="TaskLogs",
        show_status=True,
        show_refresh=True
    )
    
    # Pagination controls
    pagination_controls = ft.Row([
        ft.ElevatedButton("Previous", icon=ft.Icons.ARROW_BACK, 
                     on_click=lambda e: change_page("TaskLogs", -1, page)),
        ft.Text(f"Page {current_page + 1} of {total_pages} | Showing {start_idx + 1}-{min(end_idx, len(filtered_df))} of {len(filtered_df)}"),
        ft.ElevatedButton("Next", icon=ft.Icons.ARROW_FORWARD, 
                     on_click=lambda e: change_page("TaskLogs", 1, page))
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    
    data_table = build_data_table(current_df)
    
    return ft.Container(
        content=ft.Column([
            filter_controls,
            ft.Container(height=10),
            pagination_controls,
            ft.Container(
                content=ft.Row([
                    ft.Column([data_table], scroll=ft.ScrollMode.AUTO)
                ], scroll=ft.ScrollMode.AUTO),
                expand=True, bgcolor=ft.Colors.WHITE,
                border=ft.border.all(1, ft.Colors.GREY_300)
            )
        ]), padding=10
    )