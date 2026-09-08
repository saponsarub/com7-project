import json
import csv
import hashlib
import io
import os
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import boto3
import urllib.request
import urllib.parse
import urllib.error

from google.oauth2 import service_account
from google.auth.transport.requests import Request
from datetime import datetime, timezone, timedelta

VERSION = "2.4.2"

# Google Sheet -> S3  ·  เอกสาร: docs/googlesheet-to-s3.md

S3_BUCKET = "google-sheet-extract"

SECRET_NAME = "com7/google-sheets/service-account"

# SES ไม่มีที่ ap-southeast-7 · ไม่ตั้ง SES_FROM/SES_TO = ไม่ส่งอีเมล
SES_REGION = os.environ.get("SES_REGION", "ap-southeast-1")
SES_FROM   = os.environ.get("SES_FROM", "")
SES_TO     = [x.strip() for x in os.environ.get("SES_TO", "").split(",") if x.strip()]

TH = timezone(timedelta(hours=7))
JOB_NAME = "ingest-googlesheet-daily"

# Lambda ใส่ AWS_LAMBDA_FUNCTION_NAME ให้เอง
TEAM      = "Data Management Team"
SERVICE   = "AWS Lambda"
TASK_NAME = os.environ.get("AWS_LAMBDA_FUNCTION_NAME",
                           "com7-ingest-googlesheet-ev7")

# แหล่งข้อมูล · เพิ่มชีต = เพิ่ม dict หนึ่งก้อน
# ปลายทาง s3://<bucket>/<prefix>/<table>/data.csv
# รายละเอียด: docs/googlesheet-to-s3.md
SOURCES = [
    {
        "id": "1ZuZvelevthX1O0bcaWaWfMuh16zteZkbYim8OPgPwn4",
        "label": "EV7 Main",
        "brand": "ev7",
        "prefix": "google-sheet-ev7",
        "tabs": {
            "Query":           "ev7_query",
            "2025":            "ev7_2025",
            "2026":            "ev7_2026",
            "Check":           "ev7_check",
            "Filter":          "ev7_filter",
            "Event":           "ev7_event",
            "Compare by puii": "ev7_compare_by_puii",
        },
    },

    {
        "id": "1hZz6daP3SEeItf-qORYjhPYt9RIGo5EJ1t9tKflf0nQ",
        "label": "Grab",
        "brand": "ev7",
        "prefix": "google-sheet-ev7",
        "tabs": {
            "Clean": "Grab_Clean",
            "ชีต1":  "Grab",
        },
    },
    {
        "id": "1sA6yblgx5b2_OOK29S7K0JODI7Iy473GLfnB8jSMxC8",
        "label": "Lineman",
        "brand": "ev7",
        "prefix": "google-sheet-ev7",
        "tabs": {
            "Clean": "Lineman_Clean",
            "ชีต1":  "Lineman",
        },
    },
    {
        "id": "1SuhcbUaP3iaJUE6Beb4HJgukeBjy6orv9euonJdDnZg",
        "label": "GI",
        "brand": "gi",
        "prefix": "google-sheet-gi",
        "tabs": {
            "rawdataInteresting": "GI_Interest",
            "rawdataTestdrive":   "GI_Testdrive",
            "rawdataBooking":     "GI_Booking",
        },
    },
]


def total_tabs(runs):
    """จำนวน tab ทั้งหมดที่ตั้งใจจะดึงในรอบนี้"""
    return sum(len(r["tabs"]) for r in runs)

TMP_PATH = "/tmp/out.csv"

# เครือข่าย · ยิงติดกันหลาย tab แล้ว Google ตอบช้าลง ต้องเผื่อและ retry
# timeout x retry ต้องไม่เกินเวลาที่ Lambda เหลือ - มี guard เช็คให้อีกชั้น
HTTP_TIMEOUT = int(os.environ.get("HTTP_TIMEOUT", "90"))
HTTP_RETRY   = int(os.environ.get("HTTP_RETRY", "3"))

# ingest ซ้ำทั้งรอบสำหรับ tab ที่พัง · เว้นระยะให้ Google หายหน่วง
INGEST_PASSES = int(os.environ.get("INGEST_PASSES", "3"))
PASS_WAIT     = int(os.environ.get("PASS_WAIT", "20"))

CONTEXT = None


def time_left():
    """วินาทีที่ Lambda เหลือ · ตอนรันบนเครื่องคืนค่าสูงไว้"""
    try:
        return CONTEXT.get_remaining_time_in_millis() / 1000
    except Exception:
        return 900

secrets = boto3.client("secretsmanager")
s3 = boto3.client("s3")
ses = boto3.client("ses", region_name=SES_REGION) if SES_FROM else None

# Lambda นับแถวจาก S3 · ยิงต่อแบบ async หลังเขียน log เสร็จ
# ไม่ตั้ง = ไม่เรียก (จะไปผูกด้วย S3 Event Notification แทนก็ได้ ตัวนั้นรับได้ 2 แบบ)
ROWCOUNT_LAMBDA = os.environ.get("ROWCOUNT_LAMBDA", "")
lam = boto3.client("lambda") if ROWCOUNT_LAMBDA else None


def get_access_token():
    """Secrets Manager -> access token (อายุ 1 ชม. ใช้ได้ทุกชีต)"""
    secret_response = secrets.get_secret_value(SecretId=SECRET_NAME)
    credentials = json.loads(secret_response["SecretString"])

    creds = service_account.Credentials.from_service_account_info(
        credentials,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    creds.refresh(Request())

    return creds.token, credentials.get("client_email")


def fetch_tab(sheet_id, tab, token, client_email):
    """ดึงข้อมูลทั้ง tab จาก Sheets API · retry เมื่อ timeout / throttle"""
    url = (
        "https://sheets.googleapis.com/v4/spreadsheets/"
        + sheet_id
        + "/values/"
        + urllib.parse.quote(tab + "!A:ZZ")
    )

    raw = None

    for attempt in range(1, HTTP_RETRY + 1):
        request = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )

        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
                raw = response.read()
            break

        except urllib.error.HTTPError as e:
            # urlopen ทิ้ง body ของ Google ต้องดักเอง
            body = e.read().decode("utf-8", "replace")

            # 429 = เกิน quota · 5xx = ฝั่ง Google เอง · ทั้งคู่ลองใหม่ได้
            if e.code in (429, 500, 502, 503, 504) and attempt < HTTP_RETRY:
                wait = 2 ** attempt
                if time_left() > wait + HTTP_TIMEOUT + 30:
                    print(f"  retry {tab} in {wait}s (HTTP {e.code}) [{attempt}/{HTTP_RETRY}]")
                    time.sleep(wait)
                    continue
                print(f"  no retry {tab} - Lambda เหลือ {time_left():.0f}s ไม่พอ")

            print("Google API HTTP", e.code, "| tab:", tab)
            print("Google API says:", body)
            print("Spreadsheet ID used:", sheet_id)
            print("Service account:", client_email)
            raise

        except (TimeoutError, urllib.error.URLError) as e:
            wait = 2 ** attempt
            if attempt < HTTP_RETRY and time_left() > wait + HTTP_TIMEOUT + 30:
                print(f"  retry {tab} in {wait}s ({type(e).__name__}) [{attempt}/{HTTP_RETRY}]")
                time.sleep(wait)
                continue
            if attempt < HTTP_RETRY:
                print(f"  no retry {tab} - Lambda เหลือ {time_left():.0f}s ไม่พอ")
            raise

    data = json.loads(raw.decode("utf-8"))
    del raw

    return data.get("values", [])


def write_csv(values, path):
    """เขียน CSV ทีละแถวลง /tmp · คืน (bytes, จำนวนแถว)"""
    headers = values[0]
    width = len(headers)

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, lineterminator=chr(10))
        writer.writerow(headers)

        for i in range(1, len(values)):
            row = values[i]
            values[i] = None

            # Google ตัดช่องว่างท้ายแถว ต้องเติมเอง
            if len(row) < width:
                row = row + [""] * (width - len(row))

            writer.writerow(row[:width])

    return os.path.getsize(path), len(values) - 1


def human_size(n):
    """bytes -> KB/MB/GB (ฐาน 1024)"""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:,.1f} {unit}" if unit != "B" else f"{n:,} B"
        n /= 1024


def group_by_source(items, runs):
    """จัดรายการตามชีต คงลำดับตาม SOURCES"""
    out = []
    for r in runs:
        rows = [x for x in items if x["source"] == r["label"]]
        if rows:
            out.append((r, rows))
    return out


def build_report(ok, failed, runs, total_rows, total_bytes, elapsed):
    """รายงาน plain text · จัดกลุ่มตามชีต"""
    now = datetime.now(TH)
    n = total_tabs(runs)
    all_ok = not failed
    bar = "=" * 54
    sub = "-" * 48

    prefixes = sorted({r["prefix"] for r in runs})
    src_line = f"{len(runs)} spreadsheets · {n} tabs" if len(runs) > 1 else                f"{runs[0]['label']} ({n} tabs)"

    out = [
        "GOOGLE SHEET -> S3   Daily Ingestion Report",
        f"{now:%d %b %Y, %H:%M} (UTC+7)",
        "",
        f"Source   : {src_line}",
        (chr(10) + " " * 11).join(
            ["Target   : " + f"s3://{S3_BUCKET}/{prefixes[0]}/"]
            + [f"s3://{S3_BUCKET}/{x}/" for x in prefixes[1:]]),
        f"Log      : {LOG_S3}",
        f"Run by   : {SERVICE} - {TASK_NAME}",
        f"Status   : {'SUCCESS - all ' + str(n) + ' tabs' if all_ok else 'PARTIAL - ' + str(len(ok)) + ' of ' + str(n) + ' tabs'}",
        f"Duration : {elapsed:.0f} seconds",
        "",
        bar,
        "TABLE SUMMARY",
        bar,
    ]

    for run, rows in group_by_source(ok + failed, runs):
        g_ok = [x for x in rows if "rows" in x]
        g_rows = sum(x["rows"] for x in g_ok)
        g_bytes = sum(x["bytes"] for x in g_ok)

        if len(runs) > 1:
            out += ["", f"  {run['label']}", f"  {sub}"]
        else:
            out += [""]

        for x in sorted(g_ok, key=lambda r: -r["rows"]):
            out.append(f"  {x['table']:<26}{x['rows']:>9,} rows{human_size(x['bytes']):>12}")
        for x in rows:
            if "rows" not in x:
                out.append(f"  {x['table']:<26}{'-':>9} rows{'FAILED':>12}")

        if len(runs) > 1:
            out.append(f"  {'subtotal':<26}{g_rows:>9,} rows{human_size(g_bytes):>12}")

    out += [
        "",
        f"  {'=' * 48}",
        f"  {'TOTAL':<26}{total_rows:>9,} rows{human_size(total_bytes):>12}",
        "",
        bar,
        "VALIDATION",
        bar,
        "",
        "  [ok] Google authentication",
        f"  [{'ok' if all_ok else '!!'}] All tabs returned data ({len(ok)}/{n})",
        "  [ok] Uploaded to S3",
        "  [ok] Target files verified",
        "",
    ]

    if failed:
        out += [bar, "ERRORS", bar, ""]
        for x in failed:
            out += [f"  {x['source']} · {x['tab']}", f"       {x['error']}", ""]

    out += [
        f"Next run : {NEXT_RUN}",
        "",
        "",
        TEAM,
    ]
    return chr(10).join(out)


# สีจากโลโก้ COM7
GREEN      = "#58B040"
GREEN_DARK = "#357C27"
GREEN_TINT = "#EEF7EA"
GRAY       = "#5F6670"
GRAY_SOFT  = "#8A9099"
AMBER_DARK = "#B15E06"
INK        = "#1A1D21"
_HERE      = os.path.dirname(os.path.abspath(__file__))
LOGO_FILE  = os.path.join(_HERE, "logocom7.png")
LOGO_SHEET = os.path.join(_HERE, "logo_sheets.png")
LOGO_EV7   = os.path.join(_HERE, "ev7logo.png")
LOGO_GI    = os.path.join(_HERE, "GIlogo.png")

NEXT_RUN = "Tomorrow 23:30 (UTC+7)"

# log · ไม่ตั้ง LOG_BUCKET = ไม่เขียน · ต้องแยกถังจากข้อมูล
LOG_BUCKET = os.environ.get("LOG_BUCKET", "")
LOG_PREFIX = os.environ.get(
    "LOG_PREFIX",
    "ingest-log/source=google_sheet/job=com7-ingest-googlesheet-ev7",
).strip("/")

LOG_S3 = f"s3://{LOG_BUCKET}/{LOG_PREFIX}/" if LOG_BUCKET else "(ยังไม่ได้ตั้ง LOG_BUCKET)"


def esc(text):
    """escape HTML"""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def build_html(ok, failed, runs, total_rows, total_bytes, elapsed):
    """รายงาน HTML สำหรับ SES · table layout + inline style"""
    now = datetime.now(TH)
    n = total_tabs(runs)
    all_ok = not failed

    if all_ok:
        badge_col = GREEN_DARK
        badge_ico = "&#9989;"
        badge_txt = "Completed"
    else:
        badge_col = "#C4761E"
        badge_ico = "&#9888;&#65039;"
        badge_txt = f"Partial {len(ok)}/{n}"

    cell = f"padding:13px 16px;font-size:15px;color:{INK};border-bottom:1px solid #E9ECE9;"
    mono = ("font-family:'JetBrains Mono','Cascadia Mono','Cascadia Code',"
            "'SF Mono',Menlo,Consolas,'Roboto Mono','DejaVu Sans Mono',monospace;")
    num = cell + "text-align:right;white-space:nowrap;" + mono
    head = ("padding:12px 16px;font-size:12px;font-weight:700;color:#ffffff;"
            "letter-spacing:.07em;text-transform:uppercase;background:" + GREEN_DARK + ";")

    grp = ("padding:14px 16px 9px;font-size:13px;font-weight:700;"
           f"color:{AMBER_DARK};letter-spacing:.06em;text-transform:uppercase;"
           f"background:{GREEN_TINT};border-bottom:1px solid #D6E6CE;")
    tot = f"padding:15px 16px;background:{GREEN_TINT};"
    sub_cell = (f"padding:10px 16px;font-size:13px;color:{GRAY};font-weight:700;"
                "border-bottom:2px solid #E9ECE9;background:#F6F8F6;" + mono)

    rows = []
    multi = len(runs) > 1

    for run, items in group_by_source(ok + failed, runs):
        g_ok = [x for x in items if "rows" in x]
        g_bad = [x for x in items if "rows" not in x]

        if multi:
            rows.append(
                f'<tr><td colspan="4" style="{grp}">' + esc(run["label"]) + "</td>"
                + f'<td style="{grp}text-align:right;color:{GRAY};">'
                + f'{len(items)} tabs</td></tr>'
            )

        for i, x in enumerate(sorted(g_ok, key=lambda r: -r["rows"])):
            bg = "background:#FAFCFA;" if i % 2 else ""
            rows.append(
                "<tr>"
                + f'<td style="{cell}{bg}">'
                + f'<span style="{mono}font-size:15px;color:{GREEN_DARK};font-weight:700;">'
                + esc(x["table"]) + "</span></td>"
                + f'<td style="{cell}{bg}{mono}font-size:14px;color:{GRAY};">&#128203;&nbsp; '
                + esc(x["tab"]) + "</td>"
                + f'<td style="{num}{bg}font-weight:700;font-size:16px;">'
                + f'{x["rows"]:,}' + "</td>"
                + f'<td style="{num}{bg}color:{GRAY};font-size:15px;">'
                + human_size(x["bytes"]) + "</td>"
                + f'<td style="{cell}{bg}text-align:center;font-size:16px;">&#9989;</td></tr>'
            )

        for x in g_bad:
            rows.append(
                "<tr>"
                + f'<td style="{cell}background:#FDF3F2;">'
                + f'<span style="{mono}font-size:15px;color:#B0261A;font-weight:700;">'
                + esc(x["table"]) + "</span></td>"
                + f'<td style="{cell}background:#FDF3F2;{mono}font-size:14px;color:{GRAY};">'
                + "&#128203;&nbsp; " + esc(x["tab"]) + "</td>"
                + f'<td colspan="2" style="{num}background:#FDF3F2;color:#B0261A;'
                + 'font-weight:700;">Failed</td>'
                + f'<td style="{cell}background:#FDF3F2;text-align:center;font-size:16px;">&#10060;</td></tr>'
            )

        if multi:
            rows.append(
                f'<tr><td style="{sub_cell}">subtotal</td>'
                + f'<td style="{sub_cell}"></td>'
                + f'<td style="{sub_cell}text-align:right;">'
                + f'{sum(x["rows"] for x in g_ok):,}</td>'
                + f'<td style="{sub_cell}text-align:right;">'
                + human_size(sum(x["bytes"] for x in g_ok)) + "</td>"
                + f'<td style="{sub_cell}"></td></tr>'
            )

    err_block = ""
    if failed:
        items = "".join(
            '<div style="margin-bottom:12px;">'
            + f'<div style="font-weight:700;font-size:14px;color:{INK};">'
            + esc(x["tab"]) + "</div>"
            + f'<div style="{mono}font-size:13px;color:#B0261A;margin-top:3px;">'
            + esc(x["error"]) + "</div></div>"
            for x in failed
        )
        err_block = (
            '<tr><td style="padding:0 28px 8px;">'
            + '<div style="padding:18px 20px;background:#FDF3F2;border-radius:10px;'
            + 'border-left:4px solid #B0261A;">'
            + '<div style="font-weight:700;font-size:14px;color:#B0261A;margin-bottom:12px;">'
            + "&#128680; Failed tabs</div>" + items + "</div></td></tr>"
        )

    def meta(icon, label, value, is_mono=False, extra=""):
        style = mono + "font-size:14px;" if is_mono else "font-size:15px;"
        return ('<tr><td style="padding:7px 0;width:28px;vertical-align:top;'
                'font-size:16px;">' + icon + "</td>"
                + f'<td style="padding:7px 0;width:104px;color:{GRAY};font-size:14px;'
                + 'font-weight:600;vertical-align:top;">' + label + "</td>"
                + f'<td style="padding:7px 0;color:{INK};{style}">' + value + "</td>"
                + (extra or '<td></td>') + "</tr>")

    if len(runs) > 1:
        src_txt = (f"{len(runs)} spreadsheets"
                   + f" &nbsp;<span style='color:{GRAY};'>({n} tabs)</span>")
    else:
        src_txt = (esc(runs[0]["label"])
                   + f" &nbsp;<span style='color:{GRAY};'>({n} tabs)</span>")

    dest_txt = "<br>".join(
        f"s3://{S3_BUCKET}/{x}/" for x in sorted({r["prefix"] for r in runs}))

    meta_rows = (
        meta("&#128193;", "Source", src_txt)
        + meta("&#9729;&#65039;", "Destination", dest_txt, True)
        + meta("&#128221;", "Log", esc(LOG_S3), True)
        + meta("&#9881;&#65039;", "Run by", f"{SERVICE} &nbsp;<span style='color:{GRAY};'>"
               + f"&#183;</span>&nbsp; <span style='{mono}font-size:14px;'>"
               + esc(TASK_NAME) + "</span>")
        + meta("&#128260;", "Next run", NEXT_RUN, extra=(
            '<td style="text-align:right;white-space:nowrap;vertical-align:middle;">'
            + '<img src="cid:ev7" alt="EV7" width="66" style="display:inline-block;'
            + 'border:0;height:auto;vertical-align:middle;margin-left:10px;">'
            + '<img src="cid:gi" alt="GI" width="66" style="display:inline-block;'
            + 'border:0;height:auto;vertical-align:middle;margin-left:10px;"></td>'))
    )

    stat = (
        '<td width="{w}%" style="width:{w}%;text-align:{align};'
        'border-left:{border};padding:0 8px;">'
        '<div style="font-size:11px;color:{g};text-transform:uppercase;'
        'letter-spacing:.07em;font-weight:700;white-space:nowrap;">{label}</div>'
        '<div style="font-size:{fs}px;font-weight:700;color:{d};margin-top:6px;'
        'letter-spacing:-.4px;white-space:nowrap;">{value}</div>'
        "</td>"
    )
    sep = "1px solid #D6E6CE"
    stats = (
        stat.format(w=28, fs=16, g=GRAY, d=badge_col, label="Status", align="center",
                    border="none", value=badge_txt)
        + stat.format(w=24, fs=20, g=GRAY, d=GREEN_DARK, label="Total rows",
                      align="center", border=sep, value=f"{total_rows:,}")
        + stat.format(w=24, fs=20, g=GRAY, d=GREEN_DARK, label="Total size",
                      align="center", border=sep, value=human_size(total_bytes))
        + stat.format(w=24, fs=20, g=GRAY, d=GREEN_DARK, label="Duration",
                      align="center", border=sep, value=f"{elapsed:.0f}s")
    )

    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        '<body style="margin:0;padding:30px 20px;background:#E9EDEA;'
        "font-family:-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;\">"

        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"'
        ' style="max-width:880px;margin:0 auto;background:#ffffff;border-radius:14px;'
        'overflow:hidden;box-shadow:0 2px 14px rgba(0,0,0,.12);">'

        + f'<tr><td style="height:7px;background:{GREEN};font-size:0;line-height:0;">'
        + "&nbsp;</td></tr>"

        + '<tr><td style="padding:28px 28px 20px;">'
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"'
        + ' border="0"><tr><td style="vertical-align:middle;">'
        + '<img src="cid:logo" alt="COM7" width="126" style="display:block;border:0;'
        + 'height:auto;"></td>'
        + f'<td style="vertical-align:middle;text-align:right;color:{GRAY};font-size:14px;'
        + 'line-height:1.8;font-weight:600;">&#128197; ' + f"{now:%d %b %Y}"
        + "<br>&#128336; " + f"{now:%H:%M}" + " (UTC+7)</td></tr></table></td></tr>"

        + '<tr><td style="padding:0 28px 22px;">'
        + '<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
        + '<td style="vertical-align:middle;padding-right:12px;">'
        + '<img src="cid:sheets" alt="Google Sheets" width="30"'
        + ' style="display:block;border:0;height:auto;"></td>'
        + '<td style="vertical-align:middle;">'
        + f'<div style="font-size:23px;font-weight:700;color:{INK};letter-spacing:-.3px;'
        + 'line-height:1.25;">Data Ingestion Report</div>'
        + f'<div style="font-size:15px;color:{GRAY};margin-top:5px;font-weight:600;">'
        + "Google Sheet &#8594; S3 &nbsp;&#183;&nbsp; (EV7 &amp; GI Project)</div>"
        + "</td></tr></table></td></tr>"

        + '<tr><td style="padding:0 28px 24px;">'
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"'
        + f' style="background:{GREEN_TINT};border-radius:12px;">'
        + '<tr><td style="padding:20px 22px;">'
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"'
        + ' border="0" style="table-layout:fixed;"><tr>'
        + stats + "</tr></table>"
        + "</td></tr></table></td></tr>"

        + '<tr><td style="padding:0 28px 24px;">'
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"'
        + ' style="border-collapse:separate;border-spacing:0;border:1px solid #DFE4DF;'
        + 'border-radius:11px;">'
        + f'<tr><th style="{head}text-align:left;border-radius:10px 0 0 0;">Table</th>'
        + f'<th style="{head}text-align:left;">Source tab</th>'
        + f'<th style="{head}text-align:right;">Rows</th>'
        + f'<th style="{head}text-align:right;">Size</th>'
        + f'<th style="{head}text-align:center;border-radius:0 10px 0 0;">Status</th></tr>'
        + "".join(rows)
        + f'<tr><td style="{tot}border-radius:0 0 0 10px;font-weight:700;'
        + f'font-size:15px;color:{INK};">&#931;&nbsp; Total</td>'
        + f'<td style="{tot}"></td>'
        + f'<td style="{tot}text-align:right;'
        + f'{mono}font-weight:700;font-size:17px;color:{GREEN_DARK};">' + f"{total_rows:,}" + "</td>"
        + f'<td style="{tot}text-align:right;'
        + f'{mono}font-weight:700;font-size:16px;color:{GREEN_DARK};">'
        + human_size(total_bytes) + "</td>"
        + f'<td style="{tot}border-radius:0 0 10px 0;"></td></tr>'
        + "</table></td></tr>"

        + err_block

        + '<tr><td style="padding:20px 28px 6px;">'
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
        + meta_rows + "</table></td></tr>"

        + '<tr><td style="padding:20px 28px;background:#F7F9F7;'
        + 'border-top:1px solid #E9ECE9;">'
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"'
        + ' border="0"><tr>'
        + f'<td style="font-size:14px;color:{GRAY};">'
        + f'<b style="color:{INK};font-size:15px;">{TEAM}</b>'
        + f'<span style="color:{GRAY_SOFT};"> &#183; COM7</span><br>'
        + f'<span style="font-size:13px;color:{GRAY_SOFT};">'
        + "Automated message &#8212; please do not reply</span></td>"
        + f'<td style="text-align:right;font-size:13px;color:{GRAY_SOFT};">'
        + "ap-southeast-7 &#183; Bangkok<br>v" + VERSION + "</td>"
        + "</tr></table></td></tr>"

        + "</table></body></html>"
    )


# เรียงตาม schema กลางของแผนก · ของเดิมที่จำเป็นต่อท้าย
# ช่องที่ยังไม่มีข้อมูลปล่อยว่างไว้ก่อน (Step_Function_Name · Server_Name · Port · DB_Name)
# S3_row_count / Status_row_count ให้ Lambda นับแถวมาเติมทีหลัง
LOG_COLUMNS = [
    "Date_key",
    "Job_No",
    "Datetime_key",
    "Step_Function_Name",
    "Job_Type",
    "Source_Type",
    "Server_Name",
    "Port",
    "DB_Name",
    "Table_Name",
    "Sheet_Name",
    "Table_row count",
    "Size_MB",
    "S3_row_count",
    "Status_row_count",
    "Threat_scan_Malware",
    "Job_Start_Datetime",
    "Job_End_Datetime",
    "Job_status",
    "Duration_min",
    "Error_message",

    # ---- เพิ่มจากของเดิม ----
    "Run_status",         # ผลรวมทั้งรอบ (Job_status เป็นของแถวนี้)
    "Run_Duration_min",   # เวลาทั้งรอบ
    "Write_Mode",         # D-15 บังคับ
    "Column_count",       # D-15 บังคับ
    "Rows_Written",       # จำนวนแถวที่ writer เขียนจริง
    "Table_Duration_sec",     # เท่ากับ Duration_min แต่หน่วยวินาที อ่านง่ายกว่าตอน debug
    "Header_Hash",        # จับ schema drift ที่จำนวนคอลัมน์เท่าเดิม
    "Target_Bucket",
    "S3_Key",
    "Etag",
    "Source_Id",
    "Passes",
    "Job_Version",
]

JOB_TYPE = os.environ.get("JOB_TYPE", "Fullload")


def build_log_rows(ok, failed, runs, started_at, finished_at, elapsed, run_id):
    """log · หนึ่งแถวต่อหนึ่งตาราง (D-15) · เรียงตาม schema กลาง"""
    if not ok:
        run_status = "FAILED"
    elif failed:
        run_status = "PARTIAL"
    else:
        run_status = "SUCCESS"

    base = {
        "Date_key": f"{started_at:%Y%m%d}",
        "Job_No": run_id,
        "Datetime_key": started_at.isoformat(),
        "Step_Function_Name": "",     # ยังไม่ได้ใช้ Step Functions
        "Job_Type": JOB_TYPE,
        "Source_Type": "google_sheet",
        "Server_Name": "",            # ต้นทางเป็น HTTPS API ไม่มี server
        "Port": "",
        "DB_Name": "",
        "S3_row_count": "",           # Lambda นับแถวมาเติม
        "Status_row_count": "",
        "Threat_scan_Malware": "",    # ยังไม่มีบริการ scan
        "Run_status": run_status,
        "Run_Duration_min": round(elapsed / 60, 3),
        "Write_Mode": "rewrite",
        "Target_Bucket": S3_BUCKET,
        "Job_Version": VERSION,
    }

    def iso(dt):
        return dt.isoformat() if dt else ""

    by_label = {r["label"]: r for r in runs}

    def sid(x):
        return by_label.get(x["source"], {}).get("id", "")

    rows = []

    for x in ok:
        rows.append({**base,
                     "Table_Name": x["table"],
                     "Sheet_Name": x["tab"],
                     "Table_row count": x["rows"],
                     "Size_MB": round(x["bytes"] / 1048576, 3),
                     "Job_Start_Datetime": iso(x.get("tab_start")),
                     "Job_End_Datetime": iso(x.get("tab_end")),
                     "Job_status": "SUCCESS",
                     "Duration_min": round(x.get("tab_seconds", 0) / 60, 3),
                     "Error_message": "",
                     "Column_count": x["columns"],
                     "Rows_Written": x["rows_written"],
                     "Table_Duration_sec": x.get("tab_seconds", ""),
                     "Header_Hash": x.get("header_hash", ""),
                     "S3_Key": x["s3_key"],
                     "Etag": x.get("etag", ""),
                     "Source_Id": sid(x),
                     "Passes": x.get("pass_no", 1)})

    for x in failed:
        rows.append({**base,
                     "Table_Name": x["table"],
                     "Sheet_Name": x["tab"],
                     "Table_row count": "",
                     "Size_MB": "",
                     "Job_Start_Datetime": iso(x.get("tab_start")),
                     "Job_End_Datetime": iso(x.get("tab_end")),
                     "Job_status": "FAILED",
                     "Duration_min": (round(x["tab_seconds"] / 60, 3)
                                      if isinstance(x.get("tab_seconds"), (int, float)) else ""),
                     "Error_message": x["error"],
                     "Column_count": "",
                     "Rows_Written": "",
                     "Table_Duration_sec": x.get("tab_seconds", ""),
                     "Header_Hash": "",
                     "S3_Key": "",
                     "Etag": "",
                     "Source_Id": sid(x),
                     "Passes": x.get("passes", INGEST_PASSES)})

    return rows


def write_log(rows):
    """เขียน log CSV ลง S3 · partition year=/month=/day="""
    if not LOG_BUCKET:
        print("ไม่ได้ตั้ง LOG_BUCKET - ข้ามการเขียน log")
        return None

    if not rows:
        return None

    now = datetime.now(TH)
    key = (f"{LOG_PREFIX}/year={now:%Y}/month={now:%m}/day={now:%d}"
           f"/{rows[0]['Job_No']}.csv")

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=LOG_COLUMNS,
                            lineterminator=chr(10), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

    try:
        s3.put_object(
            Bucket=LOG_BUCKET,
            Key=key,
            # BOM ให้ Excel อ่านภาษาไทยถูก · Athena ข้ามไปพร้อม header
            Body=buf.getvalue().encode("utf-8-sig"),
            ContentType="text/csv; charset=utf-8",
        )
        uri = f"s3://{LOG_BUCKET}/{key}"
        print(f"LOG WRITTEN: {uri}  ({len(rows)} rows)")

        if lam:
            try:
                lam.invoke(
                    FunctionName=ROWCOUNT_LAMBDA,
                    InvocationType="Event",     # ไม่รอผล ไม่กินเวลา job นี้
                    Payload=json.dumps({"log_bucket": LOG_BUCKET,
                                        "log_key": key}).encode("utf-8"),
                )
                print("ROWCOUNT invoked:", ROWCOUNT_LAMBDA)
            except Exception as e:
                # นับไม่ได้ไม่ทำให้ ingest พัง ข้อมูลขึ้น S3 ไปแล้ว
                print("ROWCOUNT INVOKE FAILED:", e)

        return uri
    except Exception as e:
        print("LOG WRITE FAILED:", e)
        return None


def send_report(report, html=None):
    """ส่งรายงานผ่าน SES · ส่งไม่ได้ไม่ทำให้ job พัง"""
    if not (ses and SES_FROM and SES_TO):
        print("ไม่ได้ตั้ง SES_FROM / SES_TO - ข้ามการส่งอีเมล")
        return

    status = "PARTIAL" if "PARTIAL" in report[:400] else "SUCCESS"
    subject = f"[{status}] Google Sheet ingest - {datetime.now(TH):%d/%m/%Y %H:%M}"

    try:
        ses.send_raw_email(
            Source=SES_FROM,
            Destinations=SES_TO,
            RawMessage={"Data": build_mime(subject, report, html or report)},
        )
        print(f"SES: sent to {SES_TO} via {SES_REGION}")
    except Exception as e:
        print("SES SEND FAILED:", e)


def build_mime(subject, text, html):
    """multipart/related · โลโก้แนบเป็น inline อ้างด้วย cid:"""
    root = MIMEMultipart("related")
    root["Subject"] = subject
    root["From"] = SES_FROM
    root["To"] = ", ".join(SES_TO)

    alt = MIMEMultipart("alternative")
    root.attach(alt)
    alt.attach(MIMEText(text, "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))

    for path, cid in ((LOGO_FILE, "logo"), (LOGO_SHEET, "sheets"),
                      (LOGO_EV7, "ev7"), (LOGO_GI, "gi")):
        try:
            with open(path, "rb") as f:
                img = MIMEImage(f.read(), _subtype="png")
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline",
                           filename=os.path.basename(path))
            root.attach(img)
        except Exception as e:
            print(f"แนบรูป {cid} ไม่ได้:", e)

    return root.as_bytes()


def ingest_tab(run, tab, table, token, client_email):
    """ดึง 1 tab เขียนขึ้น S3 · คืน dict ผลลัพธ์ · พังก็ raise"""
    key = f"{run['prefix']}/{table}/data.csv"

    try:
        values = fetch_tab(run["id"], tab, token, client_email)

        if not values:
            raise Exception("sheet tab is empty")

        rows = len(values) - 1
        header = values[0]
        columns = len(header)
        # ลายนิ้วมือหัวตาราง · จับกรณีสลับ/เปลี่ยนชื่อคอลัมน์ที่จำนวนเท่าเดิม
        header_hash = hashlib.md5(
            chr(31).join(str(x) for x in header).encode("utf-8")).hexdigest()[:16]

        size, rows_written = write_csv(values, TMP_PATH)
        del values

        s3.upload_file(TMP_PATH, S3_BUCKET, key,
                       ExtraArgs={"ContentType": "text/csv"})
        head = s3.head_object(Bucket=S3_BUCKET, Key=key)

        # ไบต์ปลายทางต้องตรงกับไฟล์ที่เขียน ไม่งั้นอัปโหลดไม่ครบ
        s3_bytes = head["ContentLength"]
        if s3_bytes != size:
            raise Exception(f"อัปโหลดไม่ครบ: local {size} != S3 {s3_bytes}")

        return {"source": run["label"], "tab": tab, "table": table,
                "rows": rows, "rows_written": rows_written,
                "columns": columns, "bytes": size, "s3_key": key,
                "header_hash": header_hash,
                "etag": head["ETag"].strip('"')}

    finally:
        if os.path.exists(TMP_PATH):
            os.remove(TMP_PATH)


def jsonable(items):
    """แปลง datetime เป็น string · Lambda marshal ค่าที่ return เป็น JSON"""
    return [{k: (v.isoformat() if isinstance(v, datetime) else v)
             for k, v in x.items()}
            for x in items]


def lambda_handler(event, context):
    global CONTEXT
    CONTEXT = context
    started = time.time()
    started_at = datetime.now(TH)
    run_id = getattr(context, "aws_request_id", None) or f"{started_at:%Y%m%dT%H%M%S}"
    print(f"========== Lambda START  v{VERSION} ==========")
    print("run_id:", run_id)

    # event: {"sources": [...]} · {"tabs": [...]} · ใช้ร่วมกันได้
    ev = event or {}
    want_src = ev.get("sources")
    want_tab = ev.get("tabs")

    runs = []
    for src in SOURCES:
        if want_src and src["label"] not in want_src:
            continue
        tabs = {k: v for k, v in src["tabs"].items()
                if not want_tab or k in want_tab}
        if tabs:
            runs.append({**src, "tabs": tabs})

    if not runs:
        raise Exception("ไม่มีชีต/tab ให้ดึงตามที่ระบุใน event")

    for r in runs:
        print(f"Source: {r['label']:12} ({r['brand']}) -> {list(r['tabs'].keys())}")

    # เซ็น JWT ครั้งเดียว ใช้ได้ทุกชีต
    token, client_email = get_access_token()
    print("Google Authentication: SUCCESS |", client_email)

    # คิวงาน · tab ที่พังยกไปรอบถัดไป
    pending = [(run, tab, table)
               for run in runs for tab, table in run["tabs"].items()]

    done = {}       # (label, tab) -> ผลลัพธ์
    last_err = {}   # (label, tab) -> error ล่าสุด
    tries = {}      # (label, tab) -> ยิงไปกี่รอบ
    fail_time = {}  # (label, tab) -> (เริ่ม, จบ, วินาที) ของรอบล่าสุดที่พัง

    for pass_no in range(1, INGEST_PASSES + 1):
        if not pending:
            break

        if pass_no > 1:
            if time_left() < PASS_WAIT + 90:
                print(f"ข้าม pass {pass_no} - Lambda เหลือ {time_left():.0f}s ไม่พอ")
                break
            print(f"---------- pass {pass_no} · ลองใหม่ {len(pending)} tab "
                  f"(พัก {PASS_WAIT}s) ----------")
            time.sleep(PASS_WAIT)

        again = []
        shown = None

        for run, tab, table in pending:
            k = (run["label"], tab)
            tries[k] = pass_no

            if pass_no == 1 and shown != run["label"]:
                shown = run["label"]
                print(f"---------- {run['label']} ----------")

            t0 = time.time()
            tab_start = datetime.now(TH)

            try:
                rec = ingest_tab(run, tab, table, token, client_email)
                rec["pass_no"] = pass_no
                rec["tab_start"] = tab_start
                rec["tab_end"] = datetime.now(TH)
                rec["tab_seconds"] = round(time.time() - t0, 2)
                done[k] = rec
                last_err.pop(k, None)
                print(f"  OK   {tab:18} -> {table:22} "
                      f"{rec['rows']:>8} rows  {rec['bytes']:>10} bytes"
                      + (f"  (pass {pass_no})" if pass_no > 1 else ""))

            except Exception as e:
                # ตัดความยาว · exception อาจมีเนื้อข้อมูลติดมา
                last_err[k] = f"{type(e).__name__}: {e}"[:120]
                # เก็บเวลาของ tab ที่พังด้วย - เคส timeout อยากรู้ว่าค้างกี่วินาที
                fail_time[k] = (tab_start, datetime.now(TH), round(time.time() - t0, 2))
                again.append((run, tab, table))
                print(f"  FAIL {tab:18} -> {type(e).__name__}: {e}"
                      + ("  (จะลองใหม่)" if pass_no < INGEST_PASSES else ""))

        pending = again

    ok = list(done.values())
    failed = [{"source": run["label"], "tab": tab, "table": table,
               "error": last_err.get((run["label"], tab), "unknown"),
               "passes": tries.get((run["label"], tab), 0),
               "tab_start": fail_time.get((run["label"], tab), (None, None, ""))[0],
               "tab_end": fail_time.get((run["label"], tab), (None, None, ""))[1],
               "tab_seconds": fail_time.get((run["label"], tab), (None, None, ""))[2]}
              for run, tab, table in pending]

    saved = [x for x in ok if x.get("pass_no", 1) > 1]
    if saved:
        print("กู้คืนได้จากการลองใหม่:",
              [(x["source"], x["tab"], f"pass {x['pass_no']}") for x in saved])

    n = total_tabs(runs)
    total_rows = sum(x["rows"] for x in ok)
    total_bytes = sum(x["bytes"] for x in ok)

    print("---------- SUMMARY ----------")
    print(f"success : {len(ok)}/{n} tabs · {total_rows} rows · {len(runs)} spreadsheets")
    if failed:
        print(f"failed  : {[(x['source'], x['tab']) for x in failed]}")
    for pfx in sorted({r["prefix"] for r in runs}):
        print(f"S3      : s3://{S3_BUCKET}/{pfx}/")

    if not ok:
        # ล้มหมด · ส่งรายงานก่อนค่อยโยน error
        el = time.time() - started
        write_log(build_log_rows(ok, failed, runs, started_at,
                                 datetime.now(TH), el, run_id))
        send_report(build_report(ok, failed, runs, 0, 0, el),
                    build_html(ok, failed, runs, 0, 0, el))
        raise Exception(f"ทุก tab ล้มเหลว: {failed}")

    elapsed = time.time() - started

    write_log(build_log_rows(ok, failed, runs, started_at,
                             datetime.now(TH), elapsed, run_id))

    report = build_report(ok, failed, runs, total_rows, total_bytes, elapsed)
    html = build_html(ok, failed, runs, total_rows, total_bytes, elapsed)
    print(report)
    send_report(report, html)

    print("========== Lambda SUCCESS ==========")

    return {
        "run_id": run_id,
        "statusCode": 200 if not failed else 207,
        "message": "Success" if not failed else "Partial success",
        "sources": len(runs),
        "tabs_ok": len(ok),
        "tabs_failed": len(failed),
        "total_rows": total_rows,
        "results": jsonable(ok),
        "errors": jsonable(failed),
    }
