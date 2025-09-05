ASRS Dashboard Webapp

This project is a lightweight dashboard for monitoring and analyzing Automated Storage & Retrieval System (ASRS) operations.
Built with Python (Flet UI) and a simple backend layer for querying ASRS logs, filtering, charting, and exporting.

Feature
- interactive dashboard with 4 pages Alarm Charts, Logs viewer,status detail,Before Alarm analysis
- Exccel export with the current page
- filtered data from fixed miniload database

Tech Stack
- Python
- Flet (UI)
- SQL Server management
- Docker

Exact libraries are pinned in requirements.txt.
```
📁 Project Structure
├─ src/
│  ├─ database.py          # DB connection & query helpers
│  ├─ filters.py           # Filter models & utilities (date/bank/status/...)
│  ├─ state.py             # App-wide state/config
│  └─ ui_components.py     # Shared UI widgets (tables, filter bars, dialogs)
│
├─ views/
│  ├─ Status_Detail.py     # Status detail page
│  ├─ asrs_logs_view.py    # Main logs table + export
│  ├─ before_alm_view.py   # Pre-alarm / anomalies view
│  ├─ chart_view.py        # Charts/analytics
│  ├─ login_view.py        # Login page (optional)
│  └─ statistics_view.py   # Summary KPIs & aggregates
│
├─ main.py                 # App entrypoint
├─ requirements.txt        # Python dependencies
├─ Dockerfile              # Container build
├─ .gitignore
└─ README.md
```

⚙️ Configuration
Provide your connection string/parameters inside database.py. For example:

# Example only — adjust to your driver/DB
```
DB_CONFIG = {
    "driver": "mssql+pyodbc",
    "host": "192.168.x.x",
    "database": "WCSLOG",
    "user": "asrs_user",
    "password": "********",
    "odbc_dsn": "ODBC Driver 17 for SQL Server",
}
```

🚀 Quick Start (Local)
- Active venv first then install the all lib is needed in requirment.txt with
```
pip install -r requirements.txt
```
then run with this command
```
python main.py
```
🐳 Run with Docker
Build the project with this command
```
docker build -t asrs-dashboard .
```
then rin the docker image into a container with this command 
```
docker run --rm -p 7777:7777 --name asrs asrs-dashboard
```
You can actualy change the port in main.py


