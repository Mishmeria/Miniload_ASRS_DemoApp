import flet as ft
import pandas as pd
import threading
import time
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime, timedelta
from src.state import state
from src.filters import get_status_stats, apply_filters
from src.ui_components import create_filter_controls
from src.database import load_data #use src.database for cloud, src.local_database for local
from views.Status_Detail import Alarm_status_map

# Define ASRS line options
asrs_options = [
    ft.dropdown.Option(key="0", text="All Lines"),
] + [
    ft.dropdown.Option(key=str(i), text=f"SRM{i:02d}") 
    for i in range(1, 9)
]

def create_statistics_view(page):
    # Default date range: last 7 days to today
    default_end_date = datetime.now()
    default_start_date = default_end_date - timedelta(days=7)

    # Create text fields for displaying selected dates
    start_date_field = ft.TextField(
        label="ตั้งแต่วันที่",
        value=default_start_date.strftime("%Y-%m-%d"),
        read_only=True,
        expand=1,
    )
    
    end_date_field = ft.TextField(
        label="ถึงวันที่",
        value=default_end_date.strftime("%Y-%m-%d"),
        read_only=True,
        expand=1,
    )

    # Store selected dates in variables accessible to all functions
    selected_start_date = default_start_date
    selected_end_date = default_end_date
    
    # Create date pickers
    start_date_picker = ft.DatePicker(
        first_date=datetime(2023, 1, 1),
        last_date=datetime(2026, 12, 31),
        current_date=default_start_date.date(),
    )
    
    end_date_picker = ft.DatePicker(
        first_date=datetime(2023, 1, 1),
        last_date=datetime(2026, 12, 31),
        current_date=default_end_date.date(),
    )

    # Add date pickers to page overlay
    page.overlay.append(start_date_picker)
    page.overlay.append(end_date_picker)
    
    # Date change handlers
    def on_start_date_change(e):
        nonlocal selected_start_date
        if e.control.value:
            date_obj = datetime.combine(e.control.value, datetime.min.time())
            selected_start_date = date_obj
            start_date_field.value = date_obj.strftime("%Y-%m-%d")
            page.update()
    
    def on_end_date_change(e):
        nonlocal selected_end_date
        if e.control.value:
            date_obj = datetime.combine(e.control.value, datetime.max.time())
            selected_end_date = date_obj
            end_date_field.value = date_obj.strftime("%Y-%m-%d")
            page.update()
    
    start_date_picker.on_change = on_start_date_change
    end_date_picker.on_change = on_end_date_change

    # Calendar buttons
    start_date_button = ft.IconButton(
        icon=ft.Icons.CALENDAR_TODAY,
        tooltip="Select start date",
        on_click=lambda _: (setattr(start_date_picker, 'open', True), page.update()),
    )
    
    end_date_button = ft.IconButton(
        icon=ft.Icons.CALENDAR_TODAY,
        tooltip="Select end date",
        on_click=lambda _: (setattr(end_date_picker, 'open', True), page.update()),
    )

    # ASRS line selection dropdown
    asrs_dropdown = ft.Dropdown(
        label="ASRS Line",
        hint_text="Select ASRS line to analyze",
        options=asrs_options,
        value="0",  # Default to "All Lines"
        expand=1,
    )

    # Status indicators
    status_text = ft.Text(
        "กรุณาเลือกช่วงวันที่และ ASRS Line แล้วกดปุ่ม 'ค้นหาข้อมูล'",
        color=ft.Colors.BLUE_GREY_700
    )
    progress_bar = ft.ProgressBar(visible=False)
    
    # Results containers for two tables
    results_container = ft.Container(
        content=ft.Text("ผลลัพธ์จะแสดงที่นี่หลังจากค้นหาข้อมูล", 
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.GREY_600),
        bgcolor=ft.Colors.WHITE,
        border_radius=10,
        padding=20,
        expand=True,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
    )

    line_stats_container = ft.Container(
        content=ft.Text("สถิติรายไลน์จะแสดงที่นี่",
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.GREY_600),
        bgcolor=ft.Colors.WHITE,
        border_radius=10,
        padding=20,
        expand=True,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
    )
    
    # Function to run query and update UI
    def run_query(e):
        nonlocal selected_start_date, selected_end_date
        
        # Validate date range
        if selected_end_date < selected_start_date:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("วันที่สิ้นสุดต้องมาหลังวันที่เริ่มต้น"),
                action="OK"
            )
            page.snack_bar.open = True
            page.update()
            return
            
        # Show loading state
        progress_bar.visible = True
        status_text.value = "กำลังโหลดข้อมูล กรุณารอสักครู่..."
        status_text.color = ft.Colors.BLUE_700
        page.update()
        
        # Function to run in background thread
        def load_data_thread():
            try:
                # Get selected ASRS line
                selected_line = None if asrs_dropdown.value == "0" else asrs_dropdown.value
                
                # Call load_data with date range
                success = load_data(start_date=selected_start_date, end_date=selected_end_date)
                
                if not success:
                    status_text.value = "ไม่สามารถโหลดข้อมูลได้ กรุณาตรวจสอบการเชื่อมต่อและลองอีกครั้ง"
                    status_text.color = ft.Colors.RED_600
                    progress_bar.visible = False
                    page.update()
                    return
                
                # Process data for statistics
                df = state.get('df_logs')
                
                if df is None or len(df) == 0:
                    # No data found
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text("ไม่พบข้อมูลในช่วงวันที่ที่เลือก"),
                        action="OK"
                    )
                    page.snack_bar.open = True
                    status_text.value = "ไม่พบข้อมูล กรุณาลองเลือกช่วงวันที่อื่น"
                    status_text.color = ft.Colors.RED_600
                    progress_bar.visible = False
                    page.update()
                    return
                
                # --- Main Alarm Table (Left Side) ---
                df_to_process = df.copy()
                if selected_line and selected_line != "0":
                    df_to_process = df[df['ASRS'] == int(selected_line)]

                if len(df_to_process) == 0:
                    status_text.value = f"ไม่พบข้อมูลสำหรับ SRM{selected_line} ในช่วงวันที่ที่เลือก"
                    status_text.color = ft.Colors.ORANGE_600
                    results_container.content = ft.Text(f"ไม่พบข้อมูลสำหรับ SRM{selected_line}")
                else:
                    if 'PLCCODE' in df_to_process.columns:
                        alarm_df = df_to_process[df_to_process['PLCCODE'] > 100]
                        if len(alarm_df) > 0:
                            plc_counts = alarm_df['PLCCODE'].value_counts().reset_index()
                            plc_counts.columns = ['PLCCODE', 'Count']
                            plc_counts = plc_counts.sort_values('Count', ascending=False)
                            
                            selected_line_text = "All Lines"
                            if selected_line and selected_line != "0":
                                for option in asrs_options:
                                    if option.key == selected_line:
                                        selected_line_text = option.text
                                        break
                            
                            date_header = create_date_header(selected_start_date, selected_end_date, selected_line_text, len(alarm_df))
                            alarm_table = create_alarm_table(plc_counts)
                            results_container.content = ft.Column([date_header, ft.Container(content=alarm_table, expand=True)], scroll=ft.ScrollMode.AUTO, expand=True)
                        else:
                            results_container.content = ft.Text("ไม่พบข้อมูล Alarm ในช่วงวันที่ที่เลือก")
                
                # --- Per-Line Summary Table (Right Side) ---
                line_summary_df = df[df['PLCCODE'] > 100].groupby('ASRS').size().reset_index(name='Count')
                line_summary_df = line_summary_df.sort_values('Count', ascending=False)
                
                if not line_summary_df.empty:
                    line_summary_table = create_line_summary_table(line_summary_df)
                    line_stats_container.content = ft.Column([
                        ft.Text("สรุปจำนวน Alarm แต่ละไลน์", size=16, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Container(content=line_summary_table, expand=True)
                    ], scroll=ft.ScrollMode.AUTO, expand=True)
                else:
                    line_stats_container.content = ft.Text("ไม่พบข้อมูล Alarm เพื่อสรุป")

                # Update status
                print_total_alarms = len(df_to_process[df_to_process['PLCCODE'] > 100])
                status_text.value = f"โหลดข้อมูลสำเร็จ พบข้อมูล {len(df)} มี Alarm ทั้งหมด {print_total_alarms} รายการในช่วงเวลาที่เลือก"
                status_text.color = ft.Colors.GREEN_700
                
            except Exception as e:
                print(f"Error loading data: {e}")
                status_text.value = f"เกิดข้อผิดพลาด: {str(e)}"
                status_text.color = ft.Colors.RED_600
                
                # Show error in snackbar
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"เกิดข้อผิดพลาด: {str(e)}"),
                    action="OK"
                )
                page.snack_bar.open = True
            
            # Hide progress bar
            progress_bar.visible = False
            page.update()
        
        # Start background thread
        threading.Thread(target=load_data_thread).start()
    
    # Query button
    query_button = ft.ElevatedButton(
        text="ค้นหาข้อมูล", 
        icon=ft.Icons.SEARCH,
        on_click=run_query,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.BLUE,
        )
    )
    
    # Create the main layout
    date_controls = ft.Row([
        ft.Container(
            content=ft.Row([start_date_field, start_date_button]),
            expand=1,
        ),
        ft.Container(
            content=ft.Row([end_date_field, end_date_button]),
            expand=1,
        ),
        ft.Container(
            content=asrs_dropdown,
            expand=1,
        ),
        query_button,
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    
    # Main container
    main_container = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Text("สถิติการเกิด Alarm", size=24, weight=ft.FontWeight.BOLD),
                margin=ft.margin.only(bottom=10),
            ),
            date_controls,
            ft.Container(height=10),  # Spacer
            status_text,
            progress_bar,
            ft.Container(height=10),  # Spacer
            ft.Row([
                results_container,
                line_stats_container
            ], expand=True)
        ], expand=True),
        padding=20,
        expand=True,
    )
    
    return main_container

def create_date_header(start_date, end_date, line_text, total_alarms):
    return ft.Container(
        content=ft.Column([
            ft.Text(
                f"ข้อมูลช่วงวันที่: {start_date.strftime('%Y-%m-%d')} ถึง {end_date.strftime('%Y-%m-%d')}", 
                weight=ft.FontWeight.BOLD, 
                size=16
            ),
        ]),
        padding=10,
        margin=ft.margin.only(bottom=10),
    )

def create_alarm_table(alarm_df):
    """Create a table showing alarm frequencies"""
    if len(alarm_df) == 0:
        return ft.Text("ไม่มีข้อมูล Alarm")
    
    # Create table headers
    headers = ft.Row([
        ft.Container(
            content=ft.Text("รหัส Alarm", weight=ft.FontWeight.BOLD),
            width=100,
            padding=10,
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.BLUE_GREY_100,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_300),
        ),
        ft.Container(
            content=ft.Text("จำนวนครั้ง", weight=ft.FontWeight.BOLD),
            width=100,
            padding=10,
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.BLUE_GREY_100,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_300),
        ),
        ft.Container(
            content=ft.Text("เปอร์เซ็นต์", weight=ft.FontWeight.BOLD),
            width=100,
            padding=10,
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.BLUE_GREY_100,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_300),
        ),
        ft.Container(
            content=ft.Text("รายละเอียด", weight=ft.FontWeight.BOLD),
            width=500,
            padding=10,
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.BLUE_GREY_100,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_300),
        ),
    ], spacing=0)
    
    # Calculate total for percentages
    total_alarms = alarm_df['Count'].sum()
    
    # Create rows
    rows = []
    for _, row in alarm_df.iterrows():
        plc_code = row['PLCCODE']
        count = row['Count']
        percentage = (count / total_alarms * 100) if total_alarms > 0 else 0
        
        # Get description from Alarm_status_map
        description = Alarm_status_map.get(plc_code, "Unknown alarm")
        
        row_color = ft.Colors.RED_50 if len(rows) % 2 == 0 else ft.Colors.WHITE
        
        rows.append(ft.Row([
            ft.Container(
                content=ft.Text(str(plc_code), color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD),
                width=100,
                padding=10,
                alignment=ft.alignment.center,
                bgcolor=row_color,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
            ),
            ft.Container(
                content=ft.Text(str(count)),
                width=100,
                padding=10,
                alignment=ft.alignment.center,
                bgcolor=row_color,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
            ),
            ft.Container(
                content=ft.Text(f"{percentage:.1f}%"),
                width=100,
                padding=10,
                alignment=ft.alignment.center,
                bgcolor=row_color,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
            ),
            ft.Container(
                content=ft.Text(description, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                width=500,
                padding=10,
                alignment=ft.alignment.center_left,
                bgcolor=row_color,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
            ),
        ], spacing=0))
    
    # Combine headers and rows
    return ft.Column([headers] + rows, spacing=0, scroll=ft.ScrollMode.AUTO)

def create_line_summary_table(summary_df):
    """Creates a table summarizing alarm counts per ASRS line."""
    if summary_df.empty:
        return ft.Text("No data to summarize.")

    headers = ft.Row([
        ft.Container(
            content=ft.Text("ASRS Line", weight=ft.FontWeight.BOLD),
            expand=1,
            padding=10,
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.BLUE_GREY_100,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_300),
        ),
        ft.Container(
            content=ft.Text("Total Alarms", weight=ft.FontWeight.BOLD),
            expand=1,
            padding=10,
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.BLUE_GREY_100,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_300),
        ),
    ], spacing=0)

    rows = []
    for _, row in summary_df.iterrows():
        row_color = ft.Colors.BLUE_50 if len(rows) % 2 == 0 else ft.Colors.WHITE
        rows.append(ft.Row([
            ft.Container(
                content=ft.Text(f"SRM{row['ASRS']:02d}", weight=ft.FontWeight.BOLD),
                expand=1,
                padding=10,
                alignment=ft.alignment.center,
                bgcolor=row_color,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
            ),
            ft.Container(
                content=ft.Text(str(row['Count'])),
                expand=1,
                padding=10,
                alignment=ft.alignment.center,
                bgcolor=row_color,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
            ),
        ], spacing=0))

    return ft.Column([headers] + rows, spacing=0, scroll=ft.ScrollMode.AUTO)