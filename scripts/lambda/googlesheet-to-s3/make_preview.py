"""สร้าง preview อีเมลที่เปิดในเบราว์เซอร์แล้วเห็นโลโก้

อีเมลจริงใช้ cid: ซึ่งอ้างไฟล์แนบใน MIME - เบราว์เซอร์ไม่รู้จัก
สคริปต์นี้แทนด้วย data: URI เพื่อดูหน้าตาก่อนส่งจริง

    python make_preview.py        มี tab พัง 1 ตัว
    python make_preview.py ok     สำเร็จทุก tab
"""
import base64
import importlib.util
import os
import random
import sys
from datetime import datetime, timedelta, timezone

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-7")

spec = importlib.util.spec_from_file_location("lf", "lambda_function.py")
lf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lf)

TH = timezone(timedelta(hours=7))
ALL_OK = len(sys.argv) > 1 and sys.argv[1] == "ok"
FAIL_TAB = "rawdataTestdrive"

runs = [dict(r) for r in lf.SOURCES]
ok, failed = [], []
t = datetime.now(TH)

for run in runs:
    for tab, table in run["tabs"].items():
        random.seed(abs(hash(tab)) % 9999)
        secs = round(random.uniform(0.8, 9.5), 2)
        t0, t = t, t + timedelta(seconds=secs)

        if tab == FAIL_TAB and not ALL_OK:
            failed.append({"source": run["label"], "tab": tab, "table": table,
                           "error": "TimeoutError: The read operation timed out",
                           "passes": 3, "tab_start": t0, "tab_end": t,
                           "tab_seconds": secs})
            continue

        rows = random.randint(11, 43000)
        ok.append({"source": run["label"], "tab": tab, "table": table,
                   "rows": rows, "rows_written": rows,
                   "columns": random.randint(1, 120),
                   "bytes": rows * random.randint(60, 2400),
                   "s3_key": f"{run['prefix']}/{table}/data.csv",
                   "header_hash": "0" * 16, "etag": "0" * 32, "pass_no": 1,
                   "tab_start": t0, "tab_end": t, "tab_seconds": secs})

total_rows = sum(x["rows"] for x in ok)
total_bytes = sum(x["bytes"] for x in ok)
elapsed = sum(x["tab_seconds"] for x in ok + failed)

html = lf.build_html(ok, failed, runs, total_rows, total_bytes, elapsed)

for path, cid in ((lf.LOGO_FILE, "logo"), (lf.LOGO_SHEET, "sheets"),
                  (lf.LOGO_EV7, "ev7"), (lf.LOGO_GI, "gi")):
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    html = html.replace(f"cid:{cid}", f"data:image/png;base64,{b64}")

open("preview.html", "w", encoding="utf-8").write(html)
print(f"preview.html  {len(html):,} bytes  |  "
      f"{len(ok)} ok / {len(failed)} failed  |  {total_rows:,} rows")
