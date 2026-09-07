"""สร้างไฟล์ preview ที่เปิดในเบราว์เซอร์แล้วเห็นโลโก้

อีเมลจริงใช้ cid: ซึ่งอ้างไฟล์ที่แนบมาใน MIME - เบราว์เซอร์ไม่รู้จัก
สคริปต์นี้แทน cid: ด้วย data: URI เพื่อดูหน้าตาก่อนส่งจริง
"""
import base64, importlib.util, os
from datetime import datetime, timezone, timedelta

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-7")
os.environ.setdefault("LOG_BUCKET", "com7-data-logs")

spec = importlib.util.spec_from_file_location("lf", "lambda_function.py")
lf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lf)

TH = timezone(timedelta(hours=7))
ok = [
    {"tab": "Query", "table": "ev7_query", "rows": 70000, "rows_written": 70000,
     "columns": 15, "bytes": 19200000, "s3_key": "google-sheet-ev7/ev7_query/data.csv"},
    {"tab": "2026", "table": "ev7_2026", "rows": 4210, "rows_written": 4210,
     "columns": 12, "bytes": 812345, "s3_key": "google-sheet-ev7/ev7_2026/data.csv"},
    {"tab": "Filter", "table": "ev7_filter", "rows": 980, "rows_written": 980,
     "columns": 9, "bytes": 145200, "s3_key": "google-sheet-ev7/ev7_filter/data.csv"},
]
failed = [{"tab": "Check", "table": "ev7_check",
           "error": "HTTPError: HTTP Error 400: Bad Request"}]

tr = sum(x["rows"] for x in ok)
tb = sum(x["bytes"] for x in ok)
html = lf.build_html(ok, failed, lf.SHEETS, tr, tb, 47.0, "EV7 Leads 2026")

for path, cid in ((lf.LOGO_FILE, "logo"), (lf.LOGO_SHEET, "sheets"),
                  (lf.LOGO_EV7, "ev7"), (lf.LOGO_GI, "gi")):
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    html = html.replace(f"cid:{cid}", f"data:image/png;base64,{b64}")

open("preview.html", "w", encoding="utf-8").write(html)
print("preview.html  ", len(html), "bytes  - เปิดในเบราว์เซอร์ได้เลย")
