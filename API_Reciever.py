import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, text
from fastapi.responses import JSONResponse
import re

app = FastAPI(title="ASRS Logs API")
app.add_middleware(GZipMiddleware, minimum_size=1024)  # compress large payloads

DB_CONFIG = {
    'server': '191.20.80.101\\WMS',
    'database': 'WCSLOG',
    'username': 'sa',
    'password': 'amwteam',
    'driver': 'ODBC Driver 17 for SQL Server'
}

def get_connection_string() -> str:
    return (
        f"mssql+pyodbc://{DB_CONFIG['username']}:{DB_CONFIG['password']}@"
        f"{DB_CONFIG['server']}/{DB_CONFIG['database']}?"
        f"driver={DB_CONFIG['driver'].replace(' ', '+')}"
    )

# global pooled engine (avoid creating per request)
engine = create_engine(
    get_connection_string(),
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False,
)

DPAIR_RE = re.compile(r"\b(D\d+)\s*(?:[:=]|\s)\s*(-?\d+)\b")
LEADING_INT_RE = re.compile(r"^\s*(-?\d+)\b")

def _coerce_int(x: Any):
    try:
        if isinstance(x, str):
            xs = x.strip()
            if xs.isdigit() or (xs.startswith("-") and xs[1:].isdigit()):
                return int(xs)
        return int(x)
    except Exception:
        return x

def _fmt_dt(dt: Any) -> str:
    try:
        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return datetime.fromisoformat(str(dt)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(dt)

def parse_monitor_data(s: Optional[str]) -> Dict[str, Any]:
    """
    Parse MONITORDATA like:
      '31400      D57=31373 D130=1 ... D148=1'
    Rules:
      - Leading bare integer (before any Dxxx pairs) -> D174
      - Then parse all Dxxx=<num> (or Dxxx:<num>, or 'Dxxx <num>')
    """
    if not s or not isinstance(s, str):
        return {}

    out: Dict[str, Any] = {}

    # 1) leading integer => D174 (command X pos)
    m = LEADING_INT_RE.match(s)
    if m:
        try:
            out["D174"] = int(m.group(1))
        except ValueError:
            pass

    # 2) all Dxxx pairs
    for k, v in DPAIR_RE.findall(s):
        try:
            out[k] = int(v)
        except ValueError:
            continue

    return out

@app.get("/health")
def health_check():
    return {"status": "OK"}

@app.get("/logs")
def get_logs(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD (inclusive)"),
    end_date: Optional[str]   = Query(None, description="YYYY-MM-DD (exclusive if paired, else start+1d)"),
    limit: int                = Query(1000, ge=1, le=5000),
    offset: int               = Query(0, ge=0),
    parse: bool               = Query(True, description="Parse MONITORDATA into md_* fields"),
    include_raw_md: bool      = Query(False, description="Include original MONITORDATA string"),
    fields: Optional[str]     = Query(None, description="Comma list of columns to return (ASRS,BARCODE,...)"),
):
    # Resolve date window
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt   = datetime.strptime(end_date,   "%Y-%m-%d")
    elif start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt   = start_dt + timedelta(days=1)
    else:
        end_dt   = datetime.now()
        start_dt = end_dt - timedelta(days=1)

    # Build SELECT list
    base_cols = ["ASRS","BARCODE","CHKTYPE","MSGLOG","CDATE","MSGTYPE","PLCCODE","MONITORDATA"]
    if fields:
        req = [c.strip().upper() for c in fields.split(",") if c.strip()]
        unknown = [c for c in req if c not in [x.upper() for x in base_cols]]
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown fields: {unknown}")
        select_cols = req
    else:
        select_cols = base_cols

    if not parse and not include_raw_md and "MONITORDATA" in select_cols:
        select_cols = [c for c in select_cols if c != "MONITORDATA"]

    sql = text(f"""
        SELECT {", ".join(select_cols)}
        FROM [WCSLOG].[dbo].[LogMnpAsrs]
        WHERE CDATE >= :start AND CDATE < :end
        ORDER BY CDATE DESC
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """)

    params = {"start": start_dt, "end": end_dt, "offset": offset, "limit": limit}

    try:
        with engine.connect() as conn:
            rows: List[Dict[str, Any]] = [dict(r) for r in conn.execute(sql, params).mappings()]

        out: List[Dict[str, Any]] = []
        for r in rows:
            if "ASRS" in r:     r["ASRS"]    = _coerce_int(r.get("ASRS"))
            if "PLCCODE" in r:  r["PLCCODE"] = _coerce_int(r.get("PLCCODE"))
            if "CDATE" in r:    r["CDATE"]   = _fmt_dt(r.get("CDATE"))

            if parse and "MONITORDATA" in r:
                md = parse_monitor_data(r.get("MONITORDATA"))
                for k, v in md.items():
                    r[f"md_{k}"] = v
                if not include_raw_md:
                    r.pop("MONITORDATA", None)

            out.append(r)

        return JSONResponse(out)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    uvicorn.run("API_Reciever:app", host="0.0.0.0", port=6969, reload=False)