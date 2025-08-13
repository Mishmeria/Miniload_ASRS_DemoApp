import requests
import pandas as pd
from datetime import datetime, timedelta
from src.state import API_CONFIG, state

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

class APIClient:
    def __init__(self):
        self.base_url = API_CONFIG['base_url']
        self.timeout = API_CONFIG['timeout']
        self.headers = API_CONFIG['headers']
        self.session = requests.Session()  # keep TCP alive

    def _make_request(self, endpoint, params=None, method='GET'):
        url = f"{self.base_url}{endpoint}"
        try:
            if method == 'GET':
                resp = self.session.get(url, params=params, headers=self.headers, timeout=self.timeout)
            elif method == 'POST':
                resp = self.session.post(url, json=params, headers=self.headers, timeout=self.timeout)
            else:
                raise ValueError("Unsupported HTTP method")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"API request error: {e}")
            return None

    def check_health(self):
        res = self._make_request(API_CONFIG['endpoints']['health'])
        return res and "status" in res

    def fetch_logs(self, date_filter=None, limit=1000, offset=0):
        params = {
            "limit": limit,
            "offset": offset,
            "parse": "true",
            "include_raw_md": "false"
        }
        if date_filter:
            params.update({k: v for k, v in date_filter.items() if v})
        return self._make_request(API_CONFIG['endpoints']['logs'], params)

def load_data(start_date=None, end_date=None):
    client = APIClient()
    if not client.check_health():
        print("API not reachable. Check VPN/API server.")
        return False

    date_filter = None
    if start_date and end_date:
        date_filter = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
    elif 'selected_date' in state and state['selected_date']:
        sd = state['selected_date']
        date_filter = {
            'start_date': sd.strftime('%Y-%m-%d'),
            'end_date': (sd + timedelta(days=1)).strftime('%Y-%m-%d')
        }

    PAGE = 1000
    offset = 0
    frames = []

    while True:
        page = client.fetch_logs(date_filter, limit=PAGE, offset=offset)
        if not page:
            break
        df_page = pd.DataFrame(page)

        if 'ASRS' in df_page.columns:
            df_page['ASRS'] = pd.to_numeric(df_page['ASRS'], errors='coerce').astype('Int64')
        if 'PLCCODE' in df_page.columns:
            df_page['PLCCODE'] = pd.to_numeric(df_page['PLCCODE'], errors='coerce').astype('Int64')
        if 'CDATE' in df_page.columns:
            df_page['CDATE'] = pd.to_datetime(df_page['CDATE'], errors='coerce')

        frames.append(df_page)
        offset += PAGE
        if len(page) < PAGE:
            break

    if not frames:
        print("No data returned from API")
        return False

    NUMERIC_DISPLAY_COLS = set(MD_TO_LABELS.values()) | {"ASRS", "PLCCODE"}

    def normalize_logs_df(df: pd.DataFrame) -> pd.DataFrame:
        # 1) rename md_* to legacy labels (only those present)
        present = {k: v for k, v in MD_TO_LABELS.items() if k in df.columns}
        df = df.rename(columns=present)

        # 2) drop raw MONITORDATA if it sneaks in
        if "MONITORDATA" in df.columns:
            df = df.drop(columns=["MONITORDATA"])

        # 3) ensure all expected display columns exist (so the table headers don’t “disappear”)
        for col in MD_TO_LABELS.values():
            if col not in df.columns:
                df[col] = pd.NA

        # 4) coerce numeric display cols to numbers (clean up “D57=31373” or stray strings)
        for col in NUMERIC_DISPLAY_COLS:
            if col in df.columns:
                # if any value is like "D57=31373", split on '=' and take the right part
                df[col] = df[col].apply(
                    lambda x: str(x).split("=")[-1] if isinstance(x, str) and "=" in x else x
                )
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # 5) timestamp
        if "CDATE" in df.columns:
            df["CDATE"] = pd.to_datetime(df["CDATE"], errors="coerce")

        return df
    
    df_logs = pd.concat(frames, ignore_index=True)
    
    df_logs = normalize_logs_df(df_logs)

    print(f"Data loaded via API. Rows: {len(df_logs)}")
    
    state['df_logs'] = df_logs

    return True