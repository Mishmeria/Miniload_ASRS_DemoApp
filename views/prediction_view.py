import flet as ft
import pandas as pd
import matplotlib
# Set the backend to Agg (non-interactive) before importing pyplot
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import base64
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime, timedelta
from src.ui_components import create_filter_controls
from src.state import state
from src.filters import apply_filters

def create_matplotlib_chart(title, avg_data, max_data=None, sd_data=None, timestamps=None, color='blue', height=300):
    """
    Create a chart using matplotlib and convert to base64 image
    
    Args:
        title: Chart title
        avg_data: List of average values
        max_data: List of maximum values (optional)
        sd_data: List of standard deviation values (optional)
        timestamps: List of timestamp values for x-axis
        color: Chart color (matplotlib color name)
        height: Chart height
    """
    # No longer filtering out zero values - keeping all data points
    
    if not avg_data or len(avg_data) == 0:
        return ft.Container(
            content=ft.Text("No data available", size=12, color=ft.Colors.GREY_600),
            height=height, alignment=ft.alignment.center,
            bgcolor=ft.Colors.WHITE, border_radius=6,
            border=ft.border.all(1, ft.Colors.GREY_300), expand=True
        )
    
    # Use only the last 100 points if there are more than 100
    display_avg_data = avg_data
    
    # Create x-axis values (timestamps or indices)
    if timestamps and len(timestamps) > 0:
        display_timestamps = timestamps[-100:] if len(timestamps) > 100 else timestamps
        # Make sure lengths match
        min_length = min(len(display_avg_data), len(display_timestamps))
        display_avg_data = display_avg_data[:min_length]
        display_timestamps = display_timestamps[:min_length]
        x_values = display_timestamps
    else:
        x_values = list(range(len(display_avg_data)))
        
    # Create the matplotlib figure
    fig = plt.figure(figsize=(8, 4), dpi=100)
    
    # Plot average data
    plt.plot(x_values, display_avg_data, color=color, linewidth=2, marker='o', markersize=3, label='Average')
    
    # Plot max data if provided
    if max_data and len(max_data) > 0:
        # No longer filtering out zero values
        display_max_data = max_data[-100:] if len(max_data) > 100 else max_data
        # Make sure the lengths match
        min_length = min(len(display_avg_data), len(display_max_data), len(x_values))
        display_avg_data = display_avg_data[:min_length]
        display_max_data = display_max_data[:min_length]
        x_values_trimmed = x_values[:min_length] if isinstance(x_values, list) else x_values
        
        # Plot max data with a darker shade of the same color
        darker_color = darken_color(color)
        plt.plot(x_values_trimmed, display_max_data, color=darker_color, linewidth=2, linestyle='--', 
                marker='^', markersize=3, label='Maximum')
    
    # Plot standard deviation data if provided
    if sd_data and len(sd_data) > 0:
        # No longer filtering out zero values
        display_sd_data = sd_data[-100:] if len(sd_data) > 100 else sd_data
        # Make sure the lengths match
        min_length = min(len(display_avg_data), len(display_sd_data), len(x_values))
        display_avg_data = display_avg_data[:min_length]
        display_sd_data = display_sd_data[:min_length]
        x_values_trimmed = x_values[:min_length] if isinstance(x_values, list) else x_values
        
        # Plot SD data with a lighter shade of the same color
        lighter_color = lighten_color(color)
        plt.plot(x_values_trimmed, display_sd_data, color=lighter_color, linewidth=2, linestyle=':', 
                marker='s', markersize=3, label='Std Dev')
    
    plt.title(title, fontsize=14, fontweight='bold')
    
    # Format x-axis with timestamps as HH:MM
    if timestamps and len(timestamps) > 0:
        plt.xlabel('Time', fontsize=10)
        plt.gcf().autofmt_xdate()
        
        # Set the time format to HH:MM
        time_fmt = mdates.DateFormatter('%H:%M')
        plt.gca().xaxis.set_major_formatter(time_fmt)
        
        # Rotate the labels for better readability
        plt.xticks(rotation=45)
        
        # Set fixed x-axis range from 08:00 to 18:00
        if len(display_timestamps) > 0:
            # Get the date from the first timestamp
            base_date = display_timestamps[0].replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = base_date + timedelta(hours=8)  # 08:00
            end_time = base_date + timedelta(hours=18)   # 18:00
            plt.xlim(start_time, end_time)
            
            # Create evenly spaced ticks between 08:00 and 18:00
            hours = [base_date + timedelta(hours=h) for h in range(8, 19, 2)]
            plt.xticks(hours)
    else:
        plt.xlabel('Data Point', fontsize=10)
    
    plt.ylabel('Value', fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='upper right')
    plt.tight_layout()
    
    # Convert plot to base64 image
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close(fig)  # Close the figure explicitly
    
    # Create image source
    img_src = f"data:image/png;base64,{img_base64}"
    
    # Create the image component
    img = ft.Image(
        src=img_src,
        fit=ft.ImageFit.CONTAIN,
        expand=True
    )

    # Calculate average, max, and std dev values for display (including zeros)
    avg_val = sum(display_avg_data) / len(display_avg_data) if display_avg_data else 0
    max_val = max(display_avg_data) if display_avg_data else 0
    sd_val = sum(display_sd_data) / len(display_sd_data) if sd_data and display_sd_data else 0  # type: ignore
    
    # Show average, max, and std dev values
    stats_row = ft.Row([
        ft.Text(f"Avg: {avg_val:.2f}", size=12, weight=ft.FontWeight.BOLD, color=color),
        ft.Text(f"Max: {max_val:.2f}", size=12, weight=ft.FontWeight.BOLD, color=darker_color),  # type: ignore
        ft.Text(f"SD: {sd_val:.2f}", size=12, weight=ft.FontWeight.BOLD, color=lighter_color)  # type: ignore
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=20)
    
    # Create the chart container
    return ft.Container(
        content=ft.Column([
            img,
            stats_row
        ]),
        padding=10,
        bgcolor=ft.Colors.WHITE,
        border_radius=8,
        border=ft.border.all(1, ft.Colors.BLUE_100),
        expand=True
    )

def darken_color(color_name):
    """Return a darker version of the color for the maximum value line"""
    # Simple mapping for common colors
    color_map = {
        'blue': 'darkblue',
        'green': 'darkgreen',
        'orange': 'darkorange',
        'purple': 'indigo',
        'deeppink': 'mediumvioletred',
        'gold': 'darkgoldenrod'
    }
    return color_map.get(color_name, color_name)

def lighten_color(color_name):
    """Return a lighter version of the color for the standard deviation line"""
    # Simple mapping for common colors
    color_map = {
        'blue': 'lightskyblue',
        'green': 'lightgreen',
        'orange': 'sandybrown',
        'purple': 'mediumpurple',
        'deeppink': 'hotpink',
        'gold': 'khaki'
    }
    return color_map.get(color_name, color_name)

def get_chart_data(column_name):
    """Get data for a specific column from the logs dataframe"""
    df = state['df_logs']
    if df is None or len(df) == 0:
        return [], []
    
    # Apply filters to get the relevant data
    filtered_df = apply_filters(df, state['line_logs'], state['status_logs'], state['selected_date'], "Logs")
    
    # Check if the column exists
    if column_name not in filtered_df.columns:
        return [], []
    
    # Get the data and timestamps
    data = filtered_df[column_name].tolist()
    timestamps = filtered_df['TimeStamp'].tolist()
    
    return data, timestamps

def get_data_with_fallback(primary_name, fallback_name):
    """Try to get data for primary column name, fall back to secondary if not available"""
    data, timestamps = get_chart_data(primary_name)
    if not data and fallback_name:
        data, timestamps = get_chart_data(fallback_name)
    return data, timestamps

def set_default_date_filter():
    """Set a default date filter if none is selected"""
    if state['selected_date'] is None:
        # Set to today's date by default
        state['selected_date'] = datetime.now()
        return True
    return False

def create_prediction_view(page):
    # Set a default date filter when this tab is opened
    date_was_set = set_default_date_filter()
    
    # Create filter controls for predictions with the "charts" table type
    filter_controls = create_filter_controls(
        page=page,
        table_type="charts",  # Use the "charts" table type
        show_status=True,
        show_refresh=True
    )
    
    # Show notification if date was automatically set
    if date_was_set:
        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Date filter automatically set to {state['selected_date'].strftime('%Y-%m-%d')}"),
            action="OK"
        )
        page.snack_bar.open = True
        page.update()
    
    # Get average data and timestamps for each chart
    # Use fallback column names in case the primary ones don't exist
    avg_curr_x, timestamps_curr_x = get_data_with_fallback('AVG_X_Current', 'AVG_Current_X')
    avg_freq_x, timestamps_freq_x = get_data_with_fallback('AVG_X_Frequency', 'AVG_Frequency_X')
    
    avg_curr_y, timestamps_curr_y = get_data_with_fallback('AVG_Y_Current', 'AVG_Current_Y')
    avg_freq_y, timestamps_freq_y = get_data_with_fallback('AVG_Y_Frequency', 'AVG_Frequency_Y')

    avg_curr_z, timestamps_curr_z = get_data_with_fallback('AVG_Z_Current', 'AVG_Current_Z')
    avg_freq_z, timestamps_freq_z = get_data_with_fallback('AVG_Z_Frequency', 'AVG_Frequency_Z')

    # Get max data for each chart
    max_curr_x, _ = get_data_with_fallback('Max_X_Current', 'Max_Current_X')
    max_freq_x, _ = get_data_with_fallback('Max_X_Frequency', 'Max_Frequency_X')

    max_curr_y, _ = get_data_with_fallback('Max_Y_Current', 'Max_Current_Y')
    max_freq_y, _ = get_data_with_fallback('Max_Y_Frequency', 'Max_Frequency_Y')

    max_curr_z, _ = get_data_with_fallback('Max_Z_Current', 'Max_Current_Z')
    max_freq_z, _ = get_data_with_fallback('Max_Z_Frequency', 'Max_Frequency_Z')

    # Get standard deviation data for each chart
    std_curr_x, _ = get_data_with_fallback('SD_X_Current', 'SD_Current_X')
    std_freq_x, _ = get_data_with_fallback('SD_X_Frequency', 'SD_Frequency_X')
    
    std_curr_y, _ = get_data_with_fallback('SD_Y_Current', 'SD_Current_Y')
    std_freq_y, _ = get_data_with_fallback('SD_Y_Frequency', 'SD_Frequency_Y')

    std_curr_z, _ = get_data_with_fallback('SD_Z_Current', 'SD_Current_Z')
    std_freq_z, _ = get_data_with_fallback('SD_Z_Frequency', 'SD_Frequency_Z')
    
    # Create charts with different colors, including average, max, and std dev data, and timestamps
    current_x_chart = create_matplotlib_chart("Current X", avg_curr_x, max_curr_x, std_curr_x, timestamps_curr_x, 'blue')
    freq_x_chart = create_matplotlib_chart("Frequency X", avg_freq_x, max_freq_x, std_freq_x, timestamps_freq_x, 'green')
    
    current_y_chart = create_matplotlib_chart("Current Y", avg_curr_y, max_curr_y, std_curr_y, timestamps_curr_y, 'purple')
    freq_y_chart = create_matplotlib_chart("Frequency Y", avg_freq_y, max_freq_y, std_freq_y, timestamps_freq_y, 'deeppink')
    
    current_z_chart = create_matplotlib_chart("Current Z", avg_curr_z, max_curr_z, std_curr_z, timestamps_curr_z, 'orange')
    frequency_z_chart = create_matplotlib_chart("Frequency Z", avg_freq_z, max_freq_z, std_freq_z, timestamps_freq_z, 'gold')
    
    # Arrange charts in a grid (3x2)
    charts_grid = ft.Column([
        # Row 1: Current charts (X, Y, Z)
        ft.Row([current_x_chart, current_y_chart, current_z_chart], expand=True),
        # Row 2: Frequency charts (X, Y, Z)
        ft.Row([freq_x_chart, freq_y_chart, frequency_z_chart], expand=True)
    ], expand=True, spacing=10)
    
    # Main content
    return ft.Container(
        content=ft.Column([
            ft.Container(height=10),
            filter_controls,
            ft.Container(height=10),
            ft.Text("Time Series Analysis", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            charts_grid
        ], spacing=10),
        padding=15,
        expand=True,
        bgcolor=ft.Colors.WHITE,
        border_radius=8,
        border=ft.border.all(1, ft.Colors.GREY_300)
    )