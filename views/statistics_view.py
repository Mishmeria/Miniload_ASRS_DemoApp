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

def create_statistics_view(page):
    # Create filter controls from ui_components
    filter_container = create_filter_controls(page)
    
    # Status indicators
    status_text = ft.Text(
        "กำลังโหลดข้อมูล กรุณารอสักครู่...",
        color=ft.Colors.BLUE_700
    )
    progress_bar = ft.ProgressBar(visible=True)
    
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
    def run_query():
        # Function to run in background thread
        def load_data_thread():
            try:
                # Get data from state
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
                
                # Apply filters - use the filters directly from the page
                filtered_df = df
                if hasattr(page, 'filter_asrs') and page.filter_asrs.value != "0":
                    filtered_df = filtered_df[filtered_df['ASRS'] == int(page.filter_asrs.value)]
                
                if hasattr(page, 'filter_status') and page.filter_status.value != "0":
                    status_filter = int(page.filter_status.value)
                    if status_filter > 0:
                        filtered_df = filtered_df[filtered_df['PLCCODE'] == status_filter]
                
                if len(filtered_df) == 0:
                    status_text.value = "ไม่พบข้อมูลที่ตรงกับเงื่อนไขที่เลือก"
                    status_text.color = ft.Colors.ORANGE_600
                    results_container.content = ft.Text("ไม่พบข้อมูลที่ตรงกับเงื่อนไขที่เลือก")
                    line_stats_container.content = ft.Text("ไม่พบข้อมูลที่ตรงกับเงื่อนไขที่เลือก")
                    progress_bar.visible = False
                    page.update()
                    return
                
                # --- Main Alarm Table (Left Side) ---
                if 'PLCCODE' in filtered_df.columns:
                    alarm_df = filtered_df[filtered_df['PLCCODE'] > 100]
                    if len(alarm_df) > 0:
                        plc_counts = alarm_df['PLCCODE'].value_counts().reset_index()
                        plc_counts.columns = ['PLCCODE', 'Count']
                        plc_counts = plc_counts.sort_values('Count', ascending=False)
                        
                        start_date = state.get('selected_date')
                        end_date = state.get('end_date')
                        
                        date_header = create_date_header(start_date, end_date, len(alarm_df))
                        alarm_table = create_alarm_table(plc_counts)
                        results_container.content = ft.Column([date_header, ft.Container(content=alarm_table, expand=True)], scroll=ft.ScrollMode.AUTO, expand=True)
                    else:
                        results_container.content = ft.Text("ไม่พบข้อมูล Alarm ในช่วงวันที่ที่เลือก")
                
                # --- Per-Line Summary Table (Right Side) ---
                line_summary_df = filtered_df[filtered_df['PLCCODE'] > 100].groupby('ASRS').size().reset_index(name='Count')
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
                print_total_alarms = len(filtered_df[filtered_df['PLCCODE'] > 100])
                status_text.value = f"โหลดข้อมูลสำเร็จ พบข้อมูล {len(filtered_df)} มี Alarm ทั้งหมด {print_total_alarms} รายการในช่วงเวลาที่เลือก"
                status_text.color = ft.Colors.GREEN_700
                
            except Exception as e:
                print(f"Error processing data: {e}")
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
    
    # Main container
    main_container = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Text("สถิติการเกิด Alarm", size=24, weight=ft.FontWeight.BOLD),
                margin=ft.margin.only(bottom=10),
            ),
            filter_container,  # Add the filter controls from ui_components
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
    
    # Set up filter change handlers to automatically refresh data
    if hasattr(page, 'filter_asrs'):
        original_on_change = page.filter_asrs.on_change
        def on_filter_change(e):
            if original_on_change:
                original_on_change(e)
            status_text.value = "กำลังโหลดข้อมูล กรุณารอสักครู่..."
            status_text.color = ft.Colors.BLUE_700
            progress_bar.visible = True
            page.update()
            run_query()
        page.filter_asrs.on_change = on_filter_change
    
    if hasattr(page, 'filter_status'):
        original_on_change = page.filter_status.on_change
        def on_filter_change(e):
            if original_on_change:
                original_on_change(e)
            status_text.value = "กำลังโหลดข้อมูล กรุณารอสักครู่..."
            status_text.color = ft.Colors.BLUE_700
            progress_bar.visible = True
            page.update()
            run_query()
        page.filter_status.on_change = on_filter_change
    
    # Run the query automatically when the view is loaded
    run_query()
    
    return main_container

def create_date_header(start_date, end_date, total_alarms):
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