import flet as ft
import pandas as pd
import base64
from io import BytesIO
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime, timedelta
from src.state import state
from src.filters import apply_filters, get_status_stats
from src.database import load_data

def create_dropdown(label, value, options, width, on_change):
    return ft.Dropdown(
        label=label, value=value,
        options=[ft.dropdown.Option(opt) for opt in options],
        width=width, on_change=on_change
    )

def create_button(text, icon, on_click, bgcolor=None, color=None, height=40):
    style = ft.ButtonStyle(bgcolor=bgcolor) if bgcolor else None
    return ft.ElevatedButton(
        text, icon=icon, on_click=on_click,
        style=style, color=color, height=height
    )

def create_summary_card(title, value, color):
    color_map = {
        "blue": (ft.Colors.BLUE_700, ft.Colors.BLUE_50),
        "green": (ft.Colors.GREEN_700, ft.Colors.GREEN_50),
        "orange": (ft.Colors.ORANGE_700, ft.Colors.ORANGE_50)
    }
    text_color, bg_color = color_map.get(color, (ft.Colors.GREY_700, ft.Colors.GREY_50))
    return ft.Container(
        content=ft.Column([
            ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=text_color),
            ft.Text(value, size=24, weight=ft.FontWeight.BOLD)
        ], alignment=ft.MainAxisAlignment.CENTER),
        width=200, height=100, bgcolor=bg_color, border_radius=8,
        padding=10, alignment=ft.alignment.center
    )

def get_unique_statuses(filter_type="All"):
    df = state['df_logs']
    if df is None or len(df) == 0:
        return ["All"]
    filtered_df = apply_filters(df, state['line_logs'], "All")
    if 'PLCCODE' in filtered_df.columns:
        if filter_type == "Alarm":
            alarm_statuses = filtered_df[filtered_df['PLCCODE'] > 100]['PLCCODE'].dropna().unique().tolist()
            return ["All"] + sorted(alarm_statuses)
        elif filter_type == "Normal":
            normal_statuses = filtered_df[filtered_df['PLCCODE'] <= 100]['PLCCODE'].dropna().unique().tolist()
            return ["All"] + sorted(normal_statuses)
        else:
            statuses = filtered_df['PLCCODE'].dropna().unique().tolist()
            return ["All"] + sorted(statuses)
    else:
        return ["All"]

def filter_data_by_type(df, filter_type):
    if df is None or len(df) == 0:
        return df
    if 'PLCCODE' in df.columns:
        if filter_type == "Alarm":
            return df[df['PLCCODE'] > 100]
        elif filter_type == "Normal":
            return df[df['PLCCODE'] <= 100]
    return df

# ---------- New helpers for date "chips" ----------
def _date_chip(label: str, value: datetime | None, on_tap, text_control=None):
    """Create a date chip with a calendar icon button and text showing the selected date"""
    txt = value.strftime('%Y-%m-%d') if value else 'Select'
    
    if text_control:
        text_display = text_control
    else:
        text_display = ft.Text(f"{label}: {txt}", size=14, weight=ft.FontWeight.W_500)
    
    return ft.Row([
        text_display,
        ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH,
            tooltip=f"Select {label.lower()} date",
            on_click=on_tap
        )
    ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)


def create_filter_controls(page, show_status=True):
    if 'filter_choice' not in state:
        state['filter_choice'] = "All"
    if 'end_date' not in state:
        state['end_date'] = None  # defaults to single-day until user picks end date

    line_filter = state['line_logs']
    status_filter = state['status_logs']
    filter_choice = state['filter_choice']
    status_choices = get_unique_statuses(filter_choice)

    # Left section
    left_controls = []
    left_controls.append(
        create_dropdown(
            "SRM",
            line_filter,
            ["All"] + [str(i) for i in range(1, 9)],
            120,
            lambda e: on_line_filter_change(e, page)
        )
    )
    if show_status:
        left_controls.append(
            create_dropdown(
                "MSGTYPE",
                filter_choice,
                ["All", "Normal", "Alarm"],
                120,
                lambda e: on_filter_choice_change(e, page)
            )
        )
        left_controls.append(
            create_dropdown(
                'PLCCODE',
                status_filter,
                status_choices,
                120,
                lambda e: on_status_filter_change(e, page)
            )
        )

    # Center section: clickable chips + Apply (no extra text underneath)
    center_controls = ft.Row([
        _date_chip("Start", state.get('selected_date'), lambda e: page.open(page.date_picker), 
                  text_control=getattr(page, 'start_date_text', None)),
        _date_chip("End", state.get('end_date'), lambda e: page.open(page.end_date_picker),
                  text_control=getattr(page, 'end_date_text', None)),
        create_button(
            "ค้นหา",
            ft.Icons.SEARCH,
            lambda e: apply_date_range(e, page),
            bgcolor=ft.Colors.ORANGE_500,
            color=ft.Colors.WHITE,
            height=40
        ),
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=12)

    # Right section
    right_controls = []
    
    right_controls.append(
        create_button(
            "Export",
            ft.Icons.IMPORT_EXPORT,
            lambda e: export_excel(page),
            bgcolor=ft.Colors.GREEN,
            color=ft.Colors.WHITE
        )
    )
    right_controls.append(
        create_button(
            "Clear Filter",
            ft.Icons.CLEAR,
            lambda e: clear_filter(e, page),
            bgcolor=ft.Colors.ORANGE_600,
            color=ft.Colors.WHITE
        )
    )

    progress_gauge = create_task_progress_gauge()

    filter_row = ft.Row([
        ft.Container(content=ft.Row(left_controls, spacing=15), expand=1, padding=5),
        ft.Container(content=center_controls, expand=1, alignment=ft.alignment.center, padding=5),
        ft.Container(content=ft.Row(right_controls, alignment=ft.MainAxisAlignment.END), padding=5, expand=1),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    return ft.Column([
        filter_row,
        progress_gauge
    ])
# ---------- Events ----------
def export_excel(page):
    # Determine which tab is currently active
    if not hasattr(page, 'tabs_control') or page.tabs_control is None:
        page.snack_bar = ft.SnackBar(content=ft.Text("Cannot determine active tab"))
        page.snack_bar.open = True
        page.update()
        return
    
    current_tab_index = page.tabs_control.selected_index
    tab_names = ["กราฟ", "ก่อนเกิด Alarm", "สรุป Alarm", "รายละเอียด"]
    current_tab = tab_names[current_tab_index] if current_tab_index < len(tab_names) else "Unknown"
    
    # Get common filter values
    line_logs = state.get("line_logs", "All")
    status_logs = state.get("status_logs", "All")
    filter_choice = state.get("filter_choice", "All")
    
    # Prepare data based on the active tab
    if current_tab == "รายละเอียด" or current_tab == "กราฟ":  # Details tab or Chart tab
        df = state.get("df_logs")
        if df is None or df.empty:
            show_no_data_message(page, f"No data available for {current_tab}")
            return
        
        # Apply filters for both tabs in the same way
        df_filtered = apply_filters(df, line_logs, status_logs)
        
        # Apply message type filter
        if filter_choice == "Alarm":
            df_filtered = df_filtered[df_filtered['PLCCODE'] > 100]
        elif filter_choice == "Normal":
            df_filtered = df_filtered[df_filtered['PLCCODE'] <= 100]
        
        # Set appropriate sheet name and filename based on tab
        if current_tab == "รายละเอียด":
            sheet_name = "Logs"
            filename = f"logs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        else:  # Chart tab
            sheet_name = "Chart_Data"
            filename = f"chart_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
        # Export the data to a single sheet
        try:
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_filtered.to_excel(writer, index=False, sheet_name=sheet_name)
            buf.seek(0)
            
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            data_url = f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}"

            page.launch_url(data_url)
            print(f"Downloaded {current_tab} data with filters: line={line_logs}, status={status_logs}, type={filter_choice}")
            
            page.snack_bar = ft.SnackBar(content=ft.Text(f"Exported {current_tab} data successfully"))
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(content=ft.Text(f"Export error: {str(ex)}"))
            page.snack_bar.open = True
            page.update()
    
    elif current_tab == "สรุป Alarm":  # Alarm Summary tab
        from views.Status_Detail import Alarm_status_map
        
        df = state.get("df_logs")
        if df is None or df.empty:
            show_no_data_message(page, "No alarm summary data available")
            return
        
        try:
            # First filter by line
            df_filtered = apply_filters(df, line_logs, "All")
            
            # Then filter for alarms only
            alarm_df = df_filtered[df_filtered['PLCCODE'] > 100]
            
            if alarm_df.empty:
                show_no_data_message(page, "No alarm data after filtering")
                return
            
            # Create the same tables as shown in the UI
            # 1. Alarm frequency table
            plc_counts = alarm_df['PLCCODE'].value_counts().reset_index()
            plc_counts.columns = ['PLCCODE', 'Count']
            plc_counts = plc_counts.sort_values('Count', ascending=False)
            
            # Calculate percentages
            total_alarms = plc_counts['Count'].sum()
            plc_counts['Percentage'] = (plc_counts['Count'] / total_alarms * 100).round(1).astype(str) + '%'
            
            # Add descriptions
            plc_counts['Description'] = plc_counts['PLCCODE'].map(
                lambda x: Alarm_status_map.get(x, "Unknown alarm")
            )
            
            # 2. Line summary table
            line_summary = alarm_df.groupby('ASRS').size().reset_index(name='Total_Alarms')
            line_summary = line_summary.sort_values('Total_Alarms', ascending=False)
            line_summary['ASRS_Line'] = line_summary['ASRS'].apply(lambda x: f"SRM{x:02d}")
            
            # Export both tables to separate sheets
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                # First sheet: Alarm frequency
                plc_counts.to_excel(writer, index=False, sheet_name="Alarm_Frequency")
                
                # Second sheet: Line summary
                line_summary.to_excel(writer, index=False, sheet_name="Line_Summary")
                
                # Optional: Add a third sheet with the raw alarm data
                alarm_df.to_excel(writer, index=False, sheet_name="Raw_Alarm_Data")
            
            buf.seek(0)
            
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            data_url = f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}"

            page.launch_url(data_url)
            print(f"Downloaded Alarm Summary data with filters: line={line_logs}")
            
            page.snack_bar = ft.SnackBar(content=ft.Text("Exported Alarm Summary data successfully"))
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(content=ft.Text(f"Error preparing summary data: {str(ex)}"))
            page.snack_bar.open = True
            page.update()
            return
    
    elif current_tab == "ก่อนเกิด Alarm":  # Before Alarm tab
        # Get data from the stats_cache in before_alm_view
        try:
            from views.before_alm_view import stats_cache, process_alarm_data
            from views.Status_Detail import Alarm_status_map, Normal_status_map
            
            # Get both alarm_df and before_alarm_df
            alarm_df = stats_cache.get('alarm_df')
            before_alarm_df = stats_cache.get('before_alarm_df')
            
            # If not available in cache, try to generate them
            if alarm_df is None or before_alarm_df is None or alarm_df.empty or before_alarm_df.empty:
                alarm_df, before_alarm_df = process_alarm_data()
            
            if (alarm_df is None or alarm_df.empty) and (before_alarm_df is None or before_alarm_df.empty):
                show_no_data_message(page, "No before-alarm data available")
                return
            
            # Format the before_alarm_df data to match the UI display
            if before_alarm_df is not None and not before_alarm_df.empty:
                # Make a copy to avoid modifying the original DataFrame
                display_df = before_alarm_df.copy()
                
                # Sort by CDATE descending (same as in the UI)
                display_df = display_df.sort_values('CDATE', ascending=False)
                
                # Add missing columns with N/A values
                for col in ['BARCODE', 'Present_Level (D145)', 'Present_Bay_Arm1 (D140)']:
                    if col not in display_df.columns:
                        display_df[col] = "N/A"
                
                # Add Detail column for Alarm status
                if 'Alarm' in display_df.columns:
                    display_df['Detail'] = display_df['Alarm'].astype(int).map(
                        lambda x: Alarm_status_map.get(x, "ไม่ทราบสถานะ")
                    )
                
                # Add Description column for Status
                if 'PLCCODE' in display_df.columns:
                    display_df['Description'] = display_df['PLCCODE'].astype(int).map(
                        lambda x: Normal_status_map.get(x, "ไม่ทราบสถานะ")
                    )
                
                # Define the desired column order (same as in the UI)
                desired_cols = ['ASRS', 'BARCODE', 'Present_Level (D145)', 'Present_Bay_Arm1 (D140)', 
                               'AlarmTime', 'Alarm', 'Detail', 'CDATE', 'PLCCODE', 'Description', 'Duration']
                
                # Only include columns that exist in the DataFrame
                available_cols = [col for col in desired_cols if col in display_df.columns]
                
                # Select only the available columns in the desired order
                display_df = display_df[available_cols]
                
                # Rename columns to match UI display names
                column_display_names = {
                    'ASRS': 'SRM',
                    'BARCODE': 'BARCODE',
                    'Present_Level (D145)': 'Level',
                    'Present_Bay_Arm1 (D140)': 'Bay',
                    'AlarmTime': 'เวลาที่เกิด Alarm',
                    'Alarm': 'รหัส Alarm',
                    'Detail': 'รายละเอียด Alarm',
                    'CDATE': 'เวลาของ Status ล่าสุดก่อนเกิด Alarm',
                    'PLCCODE': 'รหัส Status',
                    'Description': 'รายละเอียด Status',
                    'Duration': 'ระยะเวลาก่อนเกิด Alarm (วินาที)'
                }
                
                # Rename the columns for export
                display_df = display_df.rename(columns=column_display_names)
                
                # Format timestamps for better readability in Excel
                for col in ['เวลาที่เกิด Alarm', 'เวลาของ Status ล่าสุดก่อนเกิด Alarm']:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(
                            lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if isinstance(x, pd.Timestamp) else x
                        )
                
                before_alarm_df = display_df
            
            # Export the data to Excel with multiple sheets
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                # Export before_alarm_df as the main sheet
                if before_alarm_df is not None and not before_alarm_df.empty:
                    before_alarm_df.to_excel(writer, index=False, sheet_name="Before_Alarm")
                
                # Export alarm_df as a secondary sheet if available
                if alarm_df is not None and not alarm_df.empty:
                    # Format alarm_df for better readability
                    alarm_display = alarm_df.copy()
                    if 'PLCCODE' in alarm_display.columns:
                        alarm_display['Detail'] = alarm_display['PLCCODE'].astype(int).map(
                            lambda x: Alarm_status_map.get(x, "ไม่ทราบสถานะ")
                        )
                    if 'CDATE' in alarm_display.columns:
                        alarm_display['CDATE'] = alarm_display['CDATE'].apply(
                            lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if isinstance(x, pd.Timestamp) else x
                        )
                    alarm_display.to_excel(writer, index=False, sheet_name="Alarms")
            
            buf.seek(0)
            
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            data_url = f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}"

            page.launch_url(data_url)
            print(f"Downloaded Before Alarm data with filters: line={line_logs}")
            
            page.snack_bar = ft.SnackBar(content=ft.Text("Exported Before Alarm data successfully"))
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(content=ft.Text(f"Error accessing before alarm data: {str(ex)}"))
            page.snack_bar.open = True
            page.update()
            return
    
    else:
        page.snack_bar = ft.SnackBar(content=ft.Text(f"Export not implemented for tab: {current_tab}"))
        page.snack_bar.open = True
        page.update()
        return

def show_no_data_message(page, message):
    """Helper function to show a consistent no-data message"""
    print(message)
    page.snack_bar = ft.SnackBar(content=ft.Text(message))
    page.snack_bar.open = True
    page.update()
    
def on_line_filter_change(e, page):
    state['line_logs'] = e.control.value
    state['page_logs'] = 0
    from main import update_view
    update_view(page)

def on_filter_choice_change(e, page):
    state['filter_choice'] = e.control.value
    state['status_logs'] = "All"
    state['page_logs'] = 0
    from main import update_view
    update_view(page)

def on_status_filter_change(e, page):
    state['status_logs'] = e.control.value
    state['page_logs'] = 0
    from main import update_view
    update_view(page)

def on_date_change(e, page):
    state['selected_date'] = e.control.value
    if not state.get('end_date'):
        state['end_date'] = state['selected_date']
    
    if hasattr(page, 'start_date_text') and page.start_date_text:
        page.start_date_text.value = f"Start: {state['selected_date'].strftime('%Y-%m-%d')}"
        page.update()

def on_end_date_change(e, page):
    state['end_date'] = e.control.value
    if not state.get('selected_date'):
        state['selected_date'] = state['end_date']
    
    if hasattr(page, 'end_date_text') and page.end_date_text:
        page.end_date_text.value = f"End: {state['end_date'].strftime('%Y-%m-%d')}"
        page.update()

def apply_date_range(e, page):
    page.splash.visible = True
    page.update()
    try:
        start = state.get('selected_date')
        end = state.get('end_date') or start
        if not start:
            # no start date chosen; just hide splash and bail
            page.splash.visible = False
            page.snack_bar = ft.SnackBar(ft.Text("Please select a start date."))
            page.snack_bar.open = True
            page.update()
            return
        # load [start, end + 1d)
        load_data(start, end) 
        state['page_logs'] = 0
        from main import update_view
        update_view(page)
        page.snack_bar = ft.SnackBar(ft.Text(f"Applied: {start:%Y-%m-%d} → {(end):%Y-%m-%d}"))
        page.snack_bar.open = True
    except Exception as ex:
        page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"))
        page.snack_bar.open = True
    finally:
        page.splash.visible = False
        page.update()

def clear_filter(e, page):
    page.splash.visible = True
    page.update()
    state['page_logs'] = 0
    state['line_logs'] = "All"
    state['status_logs'] = "All"
    state['filter_choice'] = "All"
    # Keep selected_date; clear end_date so it becomes single-day again
    state['end_date'] = None
    from main import update_view
    update_view(page)
    page.splash.visible = False
    page.update()

def change_page(table_type, direction, page):
    if table_type == "TaskLogs":
        state['page_loops'] = max(0, state['page_loops'] + direction)
    else:
        state['page_logs'] = max(0, state['page_logs'] + direction)
    from main import update_view
    update_view(page)

def refresh_data(e, page):
    page.splash.visible = True
    page.update()
    try:
        state['page_logs'] = 0
        state['line_loops'] = "All"
        state['line_logs'] = "All"
        state['status_loops'] = "All"
        state['status_logs'] = "All"
        state['filter_choice'] = "All"
        from src.database import load_data  # Changed from API_request to match your imports
        start = state.get('selected_date')
        if start:
            end = state.get('end_date') or start
            load_data(start_date=start, end_date=end + timedelta(days=1))
        from main import update_view
        update_view(page)
        page.snack_bar = ft.SnackBar(ft.Text("Data refreshed."))
        page.snack_bar.open = True
    except Exception as ex:
        page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"))
        page.snack_bar.open = True
    finally:
        page.splash.visible = False
        page.update()

def create_task_progress_gauge():
    logs_stats, total = get_status_stats(state['df_logs'], state['line_logs'], state['selected_date'])
    
    if total == 0:
        return ft.Container(
            content=ft.Text("No TaskLogs data available", size=14, color=ft.Colors.GREY_600),
            height=100, alignment=ft.alignment.center,
            bgcolor=ft.Colors.GREY_50, border_radius=8,
            border=ft.border.all(1, ft.Colors.GREY_300)
        )
    
    complete_count = logs_stats[logs_stats["PLCCODE"] <= 100]["Count"].sum()
    incomplete_count = logs_stats[logs_stats["PLCCODE"] > 100]["Count"].sum()

    complete_percent = (complete_count / total) * 100 if total else 0
    
    header = ft.Row([
        ft.Text(f"Logs ทั้งหมด : {total} records", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
        ft.Text(f"Status ปกติ : {complete_count} ครั้ง (คิดเป็น {complete_percent:.1f}% ของวัน)", size=14, color=ft.Colors.GREEN_700),
        ft.Text(f"เกิด Alarm : {incomplete_count} ครั้ง (คิดเป็น {100-complete_percent:.1f}% ของวัน)", size=14, color=ft.Colors.RED_700)
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=25)
    
    # Use ProgressBar with custom colors
    progress_bar = ft.ProgressBar(
        value=complete_percent / 100,  # Value between 0 and 1
        bgcolor=ft.Colors.RED_400,     # Background color (red for alarms)
        color=ft.Colors.GREEN_400,     # Progress color (green for working)
        height=20
    )
    
    return ft.Container(
        content=ft.Column([header, progress_bar, ft.Container(height=6)], spacing=5),
        alignment=ft.alignment.center, padding=4,
        bgcolor=ft.Colors.WHITE, border_radius=3,
    )
