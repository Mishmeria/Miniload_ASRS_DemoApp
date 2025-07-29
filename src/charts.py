import flet as ft
import pandas as pd
from src.state import state
from src.filters import get_status_stats, calculate_line_alarm_frequency

def create_status_chart(status_stats, chart_height=180):
    if len(status_stats) == 0:
        return ft.Container(
            content=ft.Text("No data available", size=12, color=ft.Colors.GREY_600),
            height=chart_height, alignment=ft.alignment.center,
            bgcolor=ft.Colors.WHITE, border_radius=6,
            border=ft.border.all(1, ft.Colors.GREY_300), expand=True
        )
    
    max_count = status_stats['Count'].max()
    chart_bars = []
    
    for _, row in status_stats.iterrows():
        bar_height = max(15, (row['Count'] / max_count) * (chart_height - 50))
        bar_width = 40
        
        bar_container = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Stack([
                        ft.Container(
                            width=bar_width, height=bar_height,
                            bgcolor=ft.Colors.ORANGE_400, border_radius=4
                        ),
                        ft.Container(
                            content=ft.Text(
                                int(row['Count']), size=10, color=ft.Colors.WHITE, # type: ignore
                                weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER
                            ),
                            width=bar_width, height=bar_height,
                            alignment=ft.alignment.center
                        )
                    ]),
                    tooltip=f"Status {row['Status']}: {row['Count']} ({row['Percentage']}%)"
                ),
                ft.Text(int(row['Status']), size=9, text_align=ft.TextAlign.CENTER) # type: ignore
            ], expand=True, alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=3)
        )
        chart_bars.append(bar_container)
    
    return ft.Container(
        content=ft.Row(
            chart_bars, alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            scroll=ft.ScrollMode.AUTO, expand=True
        ),
        height=chart_height, padding=8, border_radius=6,
        bgcolor=ft.Colors.WHITE, border=ft.border.all(1, ft.Colors.GREY_300),
        expand=True
    )

def create_status_table(status_stats):
    if len(status_stats) == 0:
        return ft.Container(
            content=ft.Text("No data available", size=12, color=ft.Colors.GREY_600),
            height=180, alignment=ft.alignment.center,
            bgcolor=ft.Colors.WHITE, border_radius=6,
            border=ft.border.all(1, ft.Colors.GREY_300), expand=True
        )
    
    headers = ft.Row([
        ft.Container(ft.Text("Status", weight=ft.FontWeight.BOLD, size=12), 
                    width=80, alignment=ft.alignment.center),
        ft.Container(ft.Text("Count", weight=ft.FontWeight.BOLD, size=12), 
                    width=80, alignment=ft.alignment.center),
    ], spacing=5)
    
    table_rows = []
    for _, row in status_stats.iterrows():
        table_row = ft.Row([
            ft.Container(ft.Text(int(row['Status']), size=11), # type: ignore
                        width=80, alignment=ft.alignment.center),
            ft.Container(ft.Text(int(row['Count']), size=11), # type: ignore
                        width=80, alignment=ft.alignment.center),
        ], expand=True, spacing=5)
        table_rows.append(table_row)
    
    return ft.Container(
        content=ft.Column([
            headers,
            ft.Divider(height=1, color=ft.Colors.GREY_400),
            ft.Column(table_rows, spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        ]),
        height=180, padding=10, border_radius=6,
        bgcolor=ft.Colors.WHITE, border=ft.border.all(1, ft.Colors.GREY_300),
        expand=True
    )

def create_line_frequency_table(logs_stats: pd.DataFrame):
    line_alarm_data = calculate_line_alarm_frequency()
    if len(line_alarm_data) == 0:
        return ft.Container(
            content=ft.Text("No alarm data available", size=12, color=ft.Colors.GREY_600),
            height=180, alignment=ft.alignment.center, bgcolor=ft.Colors.WHITE, border_radius=6, border=ft.border.all(1, ft.Colors.GREY_300), expand=True
        )
    
    headers = ft.Row([
        ft.Container(ft.Text("LINE", weight=ft.FontWeight.BOLD, size=12), width=80, alignment=ft.alignment.center),
        ft.Container(ft.Text("Alarms", weight=ft.FontWeight.BOLD, size=12), width=80, alignment=ft.alignment.center),
        ft.Container(ft.Text("%", weight=ft.FontWeight.BOLD, size=12), width=60, alignment=ft.alignment.center),
    ], spacing=5)
    table_rows = []
    total_alarms = line_alarm_data['Count'].sum()
    for _, row in line_alarm_data.iterrows():
        line_name = f"LINE{row['LINE']:02d}"
        alarm_count = int(row['Count'])
        percentage = (alarm_count / total_alarms * 100) if total_alarms > 0 else 0
        if percentage >= 20:
            text_color = ft.Colors.RED_700
        elif percentage >= 10:
            text_color = ft.Colors.ORANGE_700
        else:
            text_color = ft.Colors.GREEN_700
        table_row = ft.Row([
            ft.Container(ft.Text(line_name, size=11, color=text_color), width=80, alignment=ft.alignment.center),
            ft.Container(ft.Text(alarm_count, size=11, color=text_color), width=80, alignment=ft.alignment.center)  # type: ignore
        ], spacing=5)
        table_rows.append(table_row)
    table_content = ft.Column([
        headers,
        ft.Divider(height=1, color=ft.Colors.GREY_400),
        ft.Column(table_rows, spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
    ])
    return ft.Container(
        content=table_content,
        height=180,
        padding=10,
        border_radius=6,
        bgcolor=ft.Colors.WHITE,
        border=ft.border.all(1, ft.Colors.GREY_300),
        expand=True
    )