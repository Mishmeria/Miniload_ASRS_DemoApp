import flet as ft
import pandas as pd
import threading
import time
import sys
import os
from datetime import datetime, timedelta
import numpy as np
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.state import state
from src.filters import apply_filters, get_status_stats
from src.ui_components import create_filter_controls ,filter_data_by_type
from views.Status_Detail import Alarm_status_map, Normal_status_map, ALARM_CATEGORIES, CATEGORY_COLORS

def create_chart_view(page):
    df = state['df_logs']
    line_filter = state['line_logs']
    status_filter = state['status_logs']
    filter_choice = state.get('filter_choice', 'All')
    filtered_df = apply_filters(df, line_filter, status_filter, state['selected_date'], "Logs")
    filtered_df = filter_data_by_type(filtered_df, filter_choice)

    filter_controls = create_filter_controls(
        page=page,
        table_type="ASRS_Logs",
        show_status=True,
        show_refresh=True
    )
    
    # Create status frequency chart
    def create_status_frequency_chart():
        if filtered_df.empty:
            return ft.Text("No data available to display", size=16, color=ft.Colors.GREY_700)
        
        # Count status occurrences
        status_counts = filtered_df['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        status_counts = status_counts.sort_values('Count', ascending=False)
        
        max_count = status_counts['Count'].max()
        chart_height = 470  # Fixed chart area height
        
        # Chart Title
        chart_title = ft.Container(
            content=ft.Text(
                "กราฟการเกิด Status ในแต่ละวัน",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.BLUE_800,
                text_align=ft.TextAlign.CENTER
            ),
            alignment=ft.alignment.center,
            padding=ft.padding.only(bottom=10)
        )
        
        # Create Y-axis labels with fixed intervals (0, 50, 100, 150, 200, etc.)
        # Round max_count up to nearest nice number for better scale
        scale_max = max_count
        if max_count <= 50:
            scale_max = 50
        elif max_count <= 100:
            scale_max = 100
        elif max_count <= 200:
            scale_max = 200
        elif max_count <= 500:
            scale_max = 500
        else:
            # Round up to nearest 100
            scale_max = ((max_count // 100) + 1) * 100
        
        num_y_labels = 6  # Always show 6 labels
        step = scale_max // (num_y_labels - 1)  # Step between labels
        label_spacing = chart_height / (num_y_labels - 1)
        
        y_labels = []
        for i in range(num_y_labels):
            # Calculate value from bottom to top (0 at bottom, scale_max at top)
            value = step * i
            y_labels.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(
                            f"{value}",
                            size=12,
                            color=ft.Colors.GREY_700,
                            text_align=ft.TextAlign.RIGHT
                        ),
                        # Grid line indicator
                        ft.Container(
                            width=3,
                            height=1,
                            bgcolor=ft.Colors.GREY_400,
                            margin=ft.margin.only(left=2)
                        )
                    ], spacing=0),
                    width=55,
                    height=label_spacing if i < num_y_labels - 1 else 0,
                    alignment=ft.alignment.bottom_right,
                    padding=ft.padding.only(right=5)
                )
            )
        
        # Reverse the list so 0 is at bottom, scale_max at top
        y_labels.reverse()
        
        y_axis_column = ft.Column(
            controls=y_labels,
            spacing=0,
            alignment=ft.MainAxisAlignment.START,
        )
        
        # Create bars with x-axis labels combined in single containers
        bar_containers = []
        
        for i, row in status_counts.iterrows():
            status_code = row['Status']
            count = row['Count']
            
            # Color gradient from red (most frequent) to blue (least frequent)
            color_intensity = i / max(1, len(status_counts) - 1)  # 0 to 1 based on position
            hue = color_intensity * 300  # 0 to 300 degrees (red to purple, avoiding full circle)

            # Convert HSV to RGB
            import colorsys
            r, g, b = colorsys.hsv_to_rgb(hue/360, 0.8, 0.9)  # Saturation=0.8, Value=0.9
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
            color = f"#{r:02x}{g:02x}{b:02x}"
                        
            # Get status description for tooltip
            if status_code in Alarm_status_map:
                status_text = Alarm_status_map[status_code]
            elif status_code in Normal_status_map:
                status_text = Normal_status_map[status_code]
            else:
                status_text = f"Status {status_code}"
            
            # Calculate bar height based on the fixed scale
            bar_height = max(5, (count / scale_max) * (chart_height - 40))
            empty_space = chart_height - bar_height - 20  # Space above the bar
            
            # Create combined bar + x-axis label container
            combined_container = ft.Container(
                content=ft.Column([
                    # Chart area part (bars grow from bottom)
                    ft.Container(
                        content=ft.Column([
                            # Empty space at top
                            ft.Container(
                                height=empty_space,
                                width=50,
                            ),
                            # Count label above bar
                            ft.Container(
                                content=ft.Text(
                                    f"{count}",
                                    size=10,
                                    color=ft.Colors.BLACK,
                                    weight=ft.FontWeight.BOLD,
                                    text_align=ft.TextAlign.CENTER
                                ),
                                width=50,
                                height=20,
                                alignment=ft.alignment.center,
                            ),
                            # The bar itself (at bottom)
                            ft.Container(
                                width=50,
                                height=bar_height,
                                bgcolor=color,
                                border_radius=ft.border_radius.only(top_left=3, top_right=3),
                                border=ft.border.all(1, ft.Colors.GREY_400),
                                tooltip=f"{status_text}\nCount: {count}",
                            ),
                        ],
                        spacing=0,
                        alignment=ft.MainAxisAlignment.START,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        height=chart_height,  # Fixed height for chart area
                    ),
                    # X-axis label part (FIXED - was missing!)
                    ft.Container(
                        content=ft.Text(
                            f"{status_code}",
                            size=11,
                            color=ft.Colors.WHITE,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER
                        ),
                        width=50,
                        height=25,
                        alignment=ft.alignment.center,
                        bgcolor=ft.Colors.BLUE_700,
                        border_radius=ft.border_radius.all(3),
                        margin=ft.margin.only(top=3)
                    )
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                width=60,  # Fixed width for consistent spacing
                padding=ft.padding.symmetric(horizontal=3),
            )
            
            bar_containers.append(combined_container)
        
        # Scrollable container with bars and x-axis labels together
        scrollable_chart_row = ft.Row(
            controls=bar_containers,
            spacing=3,
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.START,
        )
        
        # Charts area with background grid and combined bars+labels
        charts_container = ft.Container(
            content=ft.Stack([
                # Background grid lines (horizontal lines at Y-axis label positions)
                ft.Container(
                    content=ft.Column([
                        ft.Container(
                            height=1,
                            bgcolor=ft.Colors.GREY_300,
                            width=None,  # Full width
                            margin=ft.margin.only(bottom=label_spacing - 1) if i < num_y_labels - 1 else ft.margin.all(0)
                        ) for i in range(num_y_labels)
                    ],
                    spacing=0,
                    ),
                    height=chart_height,  # Grid only covers chart area, not labels
                ),
                # Combined bars and x-axis labels (scrollable together)
                ft.Container(
                    content=scrollable_chart_row,
                    alignment=ft.alignment.top_left,
                )
            ]),
            height=chart_height + 60,  # Extra height for x-axis labels
            padding=ft.padding.only(left=5, right=10, top=5, bottom=5),
            border=ft.border.all(1, ft.Colors.GREY_400),
            border_radius=ft.border_radius.all(5),
            bgcolor=ft.Colors.WHITE,
        )
        
        # Main chart row (Y labels + Combined Charts with X-axis)
        main_chart_row = ft.Row([
            y_axis_column,
            ft.Container(
                content=charts_container,
                expand=True,
            )
        ],
        spacing=0,
        alignment=ft.MainAxisAlignment.START,
        )
        
        # Complete chart structure: Title > Main Chart Row (no separate x-axis row needed)
        return ft.Column([
            chart_title,
            main_chart_row,
        ],
        spacing=5,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        )

    chart_content = ft.Container(
        content=ft.Column([
            create_status_frequency_chart(),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        alignment=ft.alignment.center,
        expand=True,
        padding=20,
        bgcolor=ft.Colors.WHITE,
        border_radius=5,
        border=ft.border.all(1, ft.Colors.ORANGE_200)
    )

    return ft.Container(
        content=ft.Column([
            filter_controls,
            chart_content
        ]), 
        padding=5,
        expand=True
    )