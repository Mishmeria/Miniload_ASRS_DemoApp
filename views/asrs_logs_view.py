# views/asrs_logs_view.py

import flet as ft
import sys
import os
import re
import pandas as pd
import threading

# allow "from src..." imports when running from app root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.state import state
from src.filters import apply_filters
from src.ui_components import create_filter_controls, change_page, filter_data_by_type
from views.Status_Detail import ALARM_CATEGORIES, CATEGORY_COLORS

# --- Mapping: server md_* → legacy display labels used by the UI table ---
MD_TO_LABELS = {
    "md_D57":  "X_Distance_mm (D57)",
    "md_D130": "Start_Bank (D130)",
    "md_D131": "Start_Pos_mm (D131)",
    "md_D133": "Start_Level_mm (D133)",
    "md_D134": "End_Bank (D134)",
    "md_D135": "End_Position_mm (D135)",
    "md_D137": "End_Level_mm (D137)",
    "md_D138": "Pallet_ID (D138)",
    "md_D140": "Present_Bay_Arm1 (D140)",
    "md_D145": "Present_Level (D145)",
    "md_D146": "Status_Arm1 (D146)",
    "md_D147": "Status (D147)",
    "md_D148": "Command Machine (D148)",
    "md_D174": "Command_X_Pos (D174)",
}

NUMERIC_DISPLAY_COLS = set(MD_TO_LABELS.values()) | {"ASRS", "PLCCODE"}

# Fallback regex to parse "Dxxx<sep>value" where <sep> can be '=', ':', or whitespace
DPAIR_RE = re.compile(r"\b(D\d+)\s*(?:[:=]|\s)\s*(-?\d+)\b")

def _rename_md_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    present = {k: v for k, v in MD_TO_LABELS.items() if k in df.columns}
    if present:
        df = df.rename(columns=present)
    return df

def _fallback_parse_from_raw(df: pd.DataFrame) -> pd.DataFrame:
    """
    If md_* fields are missing but MONITORDATA exists, try a lightweight parse on the client.
    This handles tokens like 'D174=31400', 'D174:31400', or 'D174 31400'.
    """
    if df is None or df.empty or "MONITORDATA" not in df.columns:
        return df

    # Find which legacy columns we still need (i.e., entirely null or missing)
    for md_key, legacy_col in MD_TO_LABELS.items():
        if legacy_col not in df.columns or df[legacy_col].isna().all():
            # Extract from MONITORDATA
            dcode = md_key.replace("md_", "")  # e.g., 'D174'
            def extract_from_raw(s):
                if not isinstance(s, str):
                    return pd.NA
                # search all pairs and return the one matching dcode
                for k, v in DPAIR_RE.findall(s):
                    if k == dcode:
                        try:
                            return int(v)
                        except:
                            return pd.to_numeric(v, errors="coerce")
                return pd.NA
            df[legacy_col] = df[legacy_col] if legacy_col in df.columns else pd.NA
            filled = df["MONITORDATA"].apply(extract_from_raw)
            # Only overwrite where we still have NA
            mask = df[legacy_col].isna()
            df.loc[mask, legacy_col] = filled[mask]
    return df

def _ensure_legacy_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    for col in MD_TO_LABELS.values():
        if col not in df.columns:
            df[col] = pd.NA
    return df

def _coerce_numeric_display_cols(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    for col in NUMERIC_DISPLAY_COLS:
        if col in df.columns:
            # clean patterns like "D57=31373"
            df[col] = df[col].apply(
                lambda x: str(x).split("=")[-1] if isinstance(x, str) and "=" in x else x
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "CDATE" in df.columns:
        df["CDATE"] = pd.to_datetime(df["CDATE"], errors="coerce")
    # don't show raw MONITORDATA in table
    if "MONITORDATA" in df.columns:
        # keep the column for fallback parsing in other views; remove from this view
        pass
    return df

def _get_alarm_category_color(status):
    if pd.isna(status):
        return None
    try:
        status_code = int(status)
        for category, codes in ALARM_CATEGORIES.items():
            if status_code in codes:
                return ft.Colors.with_opacity(0.3, CATEGORY_COLORS[category])
    except Exception:
        pass
    return None

def build_data_table(df: pd.DataFrame):
    if df is None or len(df) == 0:
        return ft.Text("No data available", size=14, color=ft.Colors.GREY_700)

    # Normalize: map md_* → legacy, try fallback from raw, coerce numerics
    display_df = df.copy()
    display_df = _rename_md_columns(display_df)
    display_df = _fallback_parse_from_raw(display_df)
    display_df = _ensure_legacy_columns(display_df)
    display_df = _coerce_numeric_display_cols(display_df)

    column_widths = {
        'CDATE': 150,
        'ASRS': 60,
        'BARCODE': 90,
        'CHKTYPE': 90,
        'MSGLOG': 250,
        'MSGTYPE': 90,
        'PLCCODE': 90,
        'X_Distance_mm (D57)': 120,
        'Start_Bank (D130)': 100,
        'Start_Pos_mm (D131)': 120,
        'Start_Level_mm (D133)': 120,
        'End_Bank (D134)': 100,
        'End_Position_mm (D135)': 120,
        'End_Level_mm (D137)': 120,
        'Pallet_ID (D138)': 100,
        'Present_Bay_Arm1 (D140)': 120,
        'Present_Level (D145)': 120,
        'Status_Arm1 (D146)': 100,
        'Status (D147)': 100,
        'Command Machine (D148)': 130,
        'Command_X_Pos (D174)': 120,
    }

    ordered_columns = [c for c in column_widths.keys() if c in display_df.columns]
    remaining_columns = [c for c in display_df.columns if c not in ordered_columns]
    final_column_order = ordered_columns + remaining_columns
    display_df = display_df[final_column_order]

    header_display_names = {'CDATE': 'CDATE', 'ASRS': 'SRM LINE'}

    header_cells = []
    for col in display_df.columns:
        width = column_widths.get(col, 120)
        header_cells.append(
            ft.Container(
                content=ft.Text(header_display_names.get(col, col),
                                weight=ft.FontWeight.BOLD, size=14, text_align=ft.TextAlign.CENTER),
                padding=8,
                alignment=ft.alignment.center,
                bgcolor=ft.Colors.GREY_100,
                border=ft.border.all(1, ft.Colors.GREY_400),
                width=width, height=60
            )
        )
    header_row = ft.Row(header_cells, spacing=0)

    data_rows = []
    for idx, (_, row) in enumerate(display_df.iterrows()):
        row_cells = []

        plccode_val = pd.to_numeric(row.get('PLCCODE', pd.NA), errors='coerce')
        row_color = _get_alarm_category_color(plccode_val) if pd.notna(plccode_val) and plccode_val > 100 else None
        if not row_color:
            row_color = ft.Colors.with_opacity(0.05, ft.Colors.GREY_800) if idx % 2 == 0 else ft.Colors.WHITE

        for col in display_df.columns:
            value = row[col]
            width = column_widths.get(col, 120)

            if pd.isna(value):
                cell_text = "NULL"
            elif isinstance(value, pd.Timestamp):
                cell_text = value.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(value, (int, float)):
                cell_text = str(int(value)) if float(value).is_integer() else str(value)
            elif col == 'MSGLOG':
                cell_text = str(value).replace("\n", " ")
            else:
                cell_text = str(value).replace("\n", " ")[:50]

            text_color = None
            text_weight = None
            if col == 'PLCCODE' and pd.notna(plccode_val) and plccode_val > 100:
                try:
                    for category, codes in ALARM_CATEGORIES.items():
                        if int(plccode_val) in codes:
                            text_color = CATEGORY_COLORS[category]
                            text_weight = ft.FontWeight.BOLD
                            break
                except Exception:
                    pass

            row_cells.append(
                ft.Container(
                    content=ft.Text(cell_text, size=13, color=text_color, weight=text_weight,
                                    text_align=ft.TextAlign.CENTER, max_lines=2),
                    padding=6,
                    alignment=ft.alignment.center,
                    bgcolor=row_color,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    width=width, height=60
                )
            )

        data_rows.append(ft.Row(row_cells, spacing=0))

    table_content = ft.Column(
        [
            ft.Container(content=header_row, padding=0),
            ft.Container(content=ft.Column(data_rows, scroll=ft.ScrollMode.ALWAYS, spacing=0, expand=True),
                         expand=True)
        ],
        spacing=0, expand=True
    )

    total_width = sum(column_widths.get(col, 120) for col in display_df.columns)

    return ft.Container(
        content=ft.Row(
            controls=[ft.Container(content=table_content, width=max(total_width, 800))],
            scroll=ft.ScrollMode.ALWAYS, expand=True
        ),
        expand=True, bgcolor=ft.Colors.WHITE, border=ft.border.all(1, ft.Colors.GREY_300)
    )

def create_data_table_view(page):
    df = state['df_logs']
    current_page = state['page_logs']
    line_filter = state['line_logs']
    status_filter = state['status_logs']
    filter_choice = state.get('filter_choice', 'All')

    filtered_df = apply_filters(df, line_filter, status_filter, state['start_date'], "Logs")
    filtered_df = filter_data_by_type(filtered_df, filter_choice)

    total_pages = max(1, (len(filtered_df) + state['rows_per_page'] - 1) // state['rows_per_page'])
    
    # Create page dropdown options
    page_options = [
        ft.dropdown.Option(key=str(i), text=f"{i+1}")
        for i in range(total_pages)
    ]
    
    # Create page dropdown
    page_dropdown = ft.Dropdown(
        options=page_options,
        value=str(current_page),
        width=100,
        on_change=lambda e: on_page_change(e, page),
    )
    
    def on_page_change(e, page):
        state['page_logs'] = int(e.control.value)
        page.update()
        # Update the view
        page.tabs["รายละเอียด"].content.content = create_data_table_view(page)
        page.update()
    
    # Calculate current page slice
    start_idx = current_page * state['rows_per_page']
    end_idx = start_idx + state['rows_per_page']
    current_df = filtered_df.iloc[start_idx:end_idx]

    # Normalize the slice (safe even if df was normalized at load)
    # NOTE: If server has md_* values, these will populate; otherwise fallback tries MONITORDATA.
    current_df = _rename_md_columns(current_df.copy())
    current_df = _fallback_parse_from_raw(current_df)
    current_df = _ensure_legacy_columns(current_df)
    current_df = _coerce_numeric_display_cols(current_df)

    filter_controls = create_filter_controls(page=page, show_status=True)

    # New pagination controls with dropdown and export button
    pagination_controls = ft.Row(
        [
            ft.Row([
                ft.Text("หน้าที่: ", size=16),
                page_dropdown,
                ft.Text(f" แสดงข้อมูลแถวที่ {start_idx + 1} ถึงแถวที่ {min(end_idx, len(filtered_df))} จากทั้งหมด {len(filtered_df)} แถว", size=16),
            ])
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    data_table = build_data_table(current_df)

    return ft.Container(
        content=ft.Column([filter_controls, ft.Container(height=10), pagination_controls, ft.Container(height=10), data_table]),
        padding=10, expand=True
    )