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
from src.ui_components import create_filter_controls
from views.Status_Detail import Alarm_status_map, Normal_status_map, ALARM_CATEGORIES, CATEGORY_COLORS

# Cache for chart data to avoid recalculating
chart_cache = {
    'alarm_data': None,
    'time_series_data': None,
    'filter_state': None
}

def create_chart_view(page):
    filter_controls = create_filter_controls(page=page, table_type=None, show_status=False, show_refresh=True)
    
    loading_view = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.ProgressRing(width=50, height=50),
                ft.Text("Loading chart data...", size=16)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.center, 
            expand=True
        )
    ])
    
    main_container = ft.Container(
        content=ft.Column([filter_controls, loading_view], scroll=ft.ScrollMode.AUTO),
        padding=15, 
        expand=True
    )
    
    def load_data_async():
        time.sleep(0.1)
        # Create a simple tuple for comparison to check if we need to reload data
        current_filter_state = (str(state['line_logs']), state['selected_date'].strftime("%Y-%m-%d") if hasattr(state['selected_date'], 'strftime') else str(state['selected_date']))
        
        # Check if we need to reload data
        should_reload = (chart_cache['filter_state'] is None or 
                         chart_cache['filter_state'] != current_filter_state or 
                         chart_cache['alarm_data'] is None)
        
        if should_reload:
            try:
                # Process data for charts
                alarm_data, time_series_data = process_chart_data()
                
                chart_cache.update({
                    'alarm_data': alarm_data,
                    'time_series_data': time_series_data,
                    'filter_state': current_filter_state
                })
            except Exception as e:
                print(f"Error loading chart data: {e}")
                # Fallback to empty data if there's an error
                chart_cache.update({
                    'alarm_data': {},
                    'time_series_data': {},
                    'filter_state': current_filter_state
                })
        
        try:
            # Create the charts
            task_gauge = create_task_progress_gauge()
            charts_content = create_charts_layout(
                chart_cache['alarm_data'], 
                chart_cache['time_series_data']
            )
            
            # Update the UI
            main_container.content = ft.Column([
                filter_controls, 
                task_gauge, 
                charts_content
            ], scroll=ft.ScrollMode.AUTO)
            
            page.update()
        except Exception as e:
            print(f"Error updating chart view: {e}")
            # Show error message in UI
            error_content = ft.Column([
                filter_controls,
                ft.Container(
                    content=ft.Text(f"Error loading charts: {str(e)}", 
                                    color=ft.Colors.RED_600, size=16),
                    padding=20,
                    alignment=ft.alignment.center
                )
            ])
            main_container.content = error_content
            page.update()
    
    threading.Thread(target=load_data_async).start()
    return main_container

def create_task_progress_gauge():
    """Create a progress gauge showing task completion status"""
    logs_stats, total = get_status_stats(state['df_logs'], state['line_logs'], state['selected_date'])
    
    if total == 0:
        return ft.Container(
            content=ft.Text("No data available for selected filters", size=14, color=ft.Colors.GREY_600),
            height=100, alignment=ft.alignment.center,
            bgcolor=ft.Colors.GREY_50, border_radius=8,
            border=ft.border.all(1, ft.Colors.GREY_300)
        )
    
    complete_count = logs_stats[logs_stats["Status"] <= 100]["Count"].sum()
    incomplete_count = logs_stats[logs_stats["Status"] > 100]["Count"].sum()

    complete_percent = (complete_count / total) * 100 if total else 0
    
    header = ft.Row([
        ft.Text(f"📊 Total Records: {total}", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
        ft.Text(f"✅ Normal: {complete_count} ({complete_percent:.1f}%)", size=14, color=ft.Colors.GREEN_700),
        ft.Text(f"❌ Alarm: {incomplete_count} ({100-complete_percent:.1f}%)", size=14, color=ft.Colors.RED_700)
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=25)
    
    # Use ProgressBar with custom colors
    progress_bar = ft.ProgressBar(
        value=complete_percent / 100,  # Value between 0 and 1
        bgcolor=ft.Colors.RED_400,     # Background color (red for alarms)
        color=ft.Colors.GREEN_400,     # Progress color (green for working)
        height=20,
        border_radius=10,
    )
    
    return ft.Container(
        content=ft.Column([header, progress_bar, ft.Container(height=6)], spacing=5),
        alignment=ft.alignment.center, padding=10,
        bgcolor=ft.Colors.WHITE, border_radius=5,
        border=ft.border.all(1, ft.Colors.GREY_300)
    )

def process_chart_data():
    """Process the ASRS log data for use in charts"""
    df = state['df_logs']
    if df is None or len(df) == 0:
        return {}, {}
    
    # Apply filters based on current state
    filtered_df = apply_filters(df, state['line_logs'], "All", state['selected_date'], "ASRS_Logs")
    
    # Prepare alarm data by line and status
    alarm_data = {}
    
    # Count alarms by line
    if 'LINE' in filtered_df.columns and 'Status' in filtered_df.columns:
        # Convert LINE to string format
        filtered_df['LINE_STR'] = filtered_df['LINE'].apply(
            lambda x: f"{int(x):02d}" if isinstance(x, (int, float)) else str(x)
        )
        
        # Count normal vs alarm states by line
        line_status = {}
        for line in range(1, 9):
            line_str = f"{line:02d}"
            line_df = filtered_df[filtered_df['LINE_STR'] == line_str]
            
            normal_count = len(line_df[line_df['Status'] < 100])
            alarm_count = len(line_df[line_df['Status'] >= 100])
            
            line_status[f"SRM{line_str}"] = {
                'normal': normal_count,
                'alarm': alarm_count,
                'total': normal_count + alarm_count
            }
        
        alarm_data['line_status'] = line_status
        
        # Count by alarm type
        alarm_counts = {}
        alarm_df = filtered_df[filtered_df['Status'] >= 100]
        
        if len(alarm_df) > 0:
            status_counts = alarm_df['Status'].value_counts().to_dict()
            
            for status, count in status_counts.items():
                description = Alarm_status_map.get(status, "Unknown")
                alarm_counts[status] = {
                    'count': count,
                    'description': description
                }
            
            alarm_data['alarm_counts'] = alarm_counts
    
    # Prepare time series data
    time_series_data = {}
    
    if 'TimeStamp' in filtered_df.columns and 'Status' in filtered_df.columns:
        # Make sure TimeStamp is datetime
        if not pd.api.types.is_datetime64_any_dtype(filtered_df['TimeStamp']):
            filtered_df['TimeStamp'] = pd.to_datetime(filtered_df['TimeStamp'], errors='coerce')
        
        # Group by hour
        filtered_df['hour'] = filtered_df['TimeStamp'].dt.floor('H')
        
        # Count events by hour and status type (normal vs alarm)
        hourly_counts = filtered_df.groupby