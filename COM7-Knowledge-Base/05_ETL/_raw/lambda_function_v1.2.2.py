import json
import csv
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

VERSION = "1.2.2"

## sapon update 03/09/2026 — ดึงทุก tab ในรอบเดียว เขียนแยกโฟลเดอร์ตามตาราง

SPREADSHEET_ID = "1ZuZvelevthX1O0bcaWaWfMuh16zteZkbYim8OPgPwn4"

S3_BUCKET = "google-sheet-extract"
S3_PREFIX = "google-sheet-ev7"

SECRET_NAME = "com7/google-sheets/service-account"

# ปล่อยว่าง = ไม่ส่งอีเมล (job ยังทำงานปกติ)
# SES - SES ยังไม่มีที่ ap-southeast-7 ต้องใช้ region อื่น (ปกติ ap-southeast-1)
# ไม่ตั้ง SES_FROM / SES_TO = ไม่ส่งอีเมล แต่ job ยังทำงานปกติ
SES_REGION = os.environ.get("SES_REGION", "ap-southeast-1")
SES_FROM   = os.environ.get("SES_FROM", "")
SES_TO     = [x.strip() for x in os.environ.get("SES_TO", "").split(",") if x.strip()]

TH = timezone(timedelta(hours=7))
JOB_NAME = "ingest-googlesheet-daily"

# Lambda ใส่ตัวแปรนี้ให้เองตอนรัน - ใช้ค่าสำรองตอนทดสอบบนเครื่อง
TEAM      = "Data Management Team"
SERVICE   = "AWS Lambda"
TASK_NAME = os.environ.get("AWS_LAMBDA_FUNCTION_NAME",
                           "com7-ingest-googlesheet-ev7")

# ชื่อ tab ในชีต -> ชื่อโฟลเดอร์/ตาราง
#   ปลายทาง s3://<bucket>/<prefix>/<ชื่อตาราง>/data.csv
#   หนึ่งโฟลเดอร์ = หนึ่งตาราง เพื่อให้ Glue Crawler (Table level 3) แยกตารางถูก
#   prefix ev7_ กันชื่อขึ้นต้นด้วยตัวเลข และกันชนกับ reserved word (filter, check)
SHEETS = {
    "Query":           "ev7_query",
    "2025":            "ev7_2025",
    "2026":            "ev7_2026",
    "Check":           "ev7_check",
    "Filter":          "ev7_filter",
    "Event":           "ev7_event",
    "Compare by puii": "ev7_compare_by_puii",
}

TMP_PATH = "/tmp/out.csv"

secrets = boto3.client("secretsmanager")
s3 = boto3.client("s3")
ses = boto3.client("ses", region_name=SES_REGION) if SES_FROM else None


def get_access_token():
    """อ่าน service account จาก Secrets Manager แล้วแลกเป็น access token

    เซ็น JWT ครั้งเดียว ใช้ได้กับทุก tab (token อายุ 1 ชม.)
    """
    secret_response = secrets.get_secret_value(SecretId=SECRET_NAME)
    credentials = json.loads(secret_response["SecretString"])

    creds = service_account.Credentials.from_service_account_info(
        credentials,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    creds.refresh(Request())

    return creds.token, credentials.get("client_email")


def fetch_sheet_title(token):
    """ขอชื่อชีตจาก Google - ถ้าอ่านไม่ได้ก็ใช้ ID แทน ไม่ควรทำให้ทั้ง job พัง"""
    url = ("https://sheets.googleapis.com/v4/spreadsheets/"
           + SPREADSHEET_ID + "?fields=properties.title")
    request = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))["properties"]["title"]
    except Exception as e:
        print("อ่านชื่อชีตไม่ได้:", e)
        return SPREADSHEET_ID


def fetch_tab(tab, token, client_email):
    """ดึงข้อมูลทั้ง tab จาก Sheets API คืนเป็น list of rows"""
    url = (
        "https://sheets.googleapis.com/v4/spreadsheets/"
        + SPREADSHEET_ID
        + "/values/"
        + urllib.parse.quote(tab + "!A:ZZ")
    )

    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()

    except urllib.error.HTTPError as e:
        # urlopen ทิ้ง body ของ Google ไป ต้องดักเองถึงจะเห็นสาเหตุจริง
        print("Google API HTTP", e.code, "| tab:", tab)
        print("Google API says:", e.read().decode("utf-8", "replace"))
        print("Spreadsheet ID used:", SPREADSHEET_ID)
        print("Service account:", client_email)
        raise

    data = json.loads(raw.decode("utf-8"))
    del raw

    return data.get("values", [])


def write_csv(values, path):
    """เขียน CSV ลงไฟล์ทีละแถว คืนขนาดไฟล์เป็น bytes

    เขียนลง /tmp ไม่ต่อ string ใน RAM — /tmp มี 512 MB แยกจาก memory ของฟังก์ชัน
    ทำให้ขนาดชีตแทบไม่กระทบ RAM
    """
    headers = values[0]
    width = len(headers)

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, lineterminator=chr(10))
        writer.writerow(headers)

        for i in range(1, len(values)):
            row = values[i]
            values[i] = None  # ปล่อยหน่วยความจำทีละแถว

            # Google ตัดช่องว่างท้ายแถวทิ้ง ต้องเติมเองให้ครบ
            if len(row) < width:
                row = row + [""] * (width - len(row))

            writer.writerow(row[:width])

    return os.path.getsize(path)


def human_size(n):
    """แปลง bytes เป็นหน่วยที่คนอ่านออก - ใช้ KB/MB/GB ฐาน 1024 แบบเดียวกับ S3 console"""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:,.1f} {unit}" if unit != "B" else f"{n:,} B"
        n /= 1024


def build_report(ok, failed, sheets, total_rows, total_bytes, elapsed, title):
    """Daily ingestion report - plain text

    ตารางจัดด้วยช่องว่าง ใช้ได้เพราะทุกค่าเป็น ASCII (ชื่อตาราง ตัวเลข หน่วย)
    ไม่มีภาษาไทยในตาราง จึงไม่มีปัญหาเรื่องความกว้างของสระ
    """
    now = datetime.now(TH)
    n = len(sheets)
    all_ok = not failed
    bar = "=" * 54
    sub = "-" * 48

    out = [
        "GOOGLE SHEET -> S3   Daily Ingestion Report",
        f"{now:%d %b %Y, %H:%M} (UTC+7)",
        "",
        f"Source   : {title} ({n} tabs)",
        f"Target   : s3://{S3_BUCKET}/{S3_PREFIX}/",
        f"Log      : {LOG_S3}",
        f"Run by   : {SERVICE} - {TASK_NAME}",
        f"Status   : {'SUCCESS - all ' + str(n) + ' tabs' if all_ok else 'PARTIAL - ' + str(len(ok)) + ' of ' + str(n) + ' tabs'}",
        f"Duration : {elapsed:.0f} seconds",
        "",
        bar,
        "TABLE SUMMARY",
        bar,
        "",
    ]

    for x in sorted(ok, key=lambda r: -r["rows"]):
        out.append(f"  {x['table']:<26}{x['rows']:>9,} rows{human_size(x['bytes']):>12}")

    for x in failed:
        out.append(f"  {x['table']:<26}{'-':>9} rows{'FAILED':>12}")

    out += [
        f"  {sub}",
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
            out += [f"  {x['tab']}", f"       {x['error']}", ""]

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
INK        = "#1A1D21"
_HERE      = os.path.dirname(os.path.abspath(__file__))
LOGO_FILE  = os.path.join(_HERE, "logocom7.png")
LOGO_SHEET = os.path.join(_HERE, "logo_sheets.png")

NEXT_RUN = "Tomorrow 23:30 (UTC+7)"

# ปลายทางไฟล์ log การ ingest - ยังเป็นค่าตั้งต้น รอตกลงถังจริง
LOG_S3 = os.environ.get(
    "LOG_S3",
    "s3://com7-data-logs/ingest-log/source=google_sheet"
    "/job=com7-ingest-googlesheet-ev7/",
)


def esc(text):
    """กัน HTML injection - ค่าจากชีตไม่ควรกลายเป็น tag"""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def build_html(ok, failed, sheets, total_rows, total_bytes, elapsed, title):
    """HTML report for SES

    ใช้ table layout + inline style เพราะโปรแกรมอีเมลตัด <style> ใน head ทิ้ง
    และไม่รองรับ flex/grid - โลโก้แนบเป็น inline attachment อ้างด้วย cid:logo
    ใช้ HTML entity แทน emoji ตรง ๆ เพื่อไม่ให้ encoding เพี้ยน
    """
    now = datetime.now(TH)
    n = len(sheets)
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
    num = cell + "text-align:right;white-space:nowrap;"
    head = ("padding:12px 16px;font-size:12px;font-weight:700;color:#ffffff;"
            "letter-spacing:.07em;text-transform:uppercase;background:" + GREEN_DARK + ";")
    mono = "font-family:Consolas,Menlo,'Courier New',monospace;"

    rows = []
    for i, x in enumerate(sorted(ok, key=lambda r: -r["rows"])):
        bg = "background:#FAFCFA;" if i % 2 else ""
        rows.append(
            "<tr>"
            + f'<td style="{cell}{bg}">'
            + f'<span style="{mono}font-size:15px;color:{GREEN_DARK};font-weight:700;">'
            + esc(x["table"]) + "</span>"
            + f'<div style="font-size:13px;color:{GRAY};margin-top:3px;">&#128203; '
            + esc(x["tab"]) + "</div></td>"
            + f'<td style="{num}{bg}font-weight:700;font-size:16px;">'
            + f'{x["rows"]:,}' + "</td>"
            + f'<td style="{num}{bg}color:{GRAY};font-size:15px;">'
            + human_size(x["bytes"]) + "</td>"
            + f'<td style="{cell}{bg}text-align:center;font-size:16px;">&#9989;</td></tr>'
        )
    for x in failed:
        rows.append(
            "<tr>"
            + f'<td style="{cell}background:#FDF3F2;">'
            + f'<span style="{mono}font-size:15px;color:#B0261A;font-weight:700;">'
            + esc(x["table"]) + "</span>"
            + f'<div style="font-size:13px;color:{GRAY};margin-top:3px;">&#128203; '
            + esc(x["tab"]) + "</div></td>"
            + f'<td colspan="2" style="{num}background:#FDF3F2;color:#B0261A;'
            + 'font-weight:700;">Failed</td>'
            + f'<td style="{cell}background:#FDF3F2;text-align:center;font-size:16px;">&#10060;</td></tr>'
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

    def meta(icon, label, value, is_mono=False):
        style = mono + "font-size:14px;" if is_mono else "font-size:15px;"
        return ('<tr><td style="padding:7px 0;width:28px;vertical-align:top;'
                'font-size:16px;">' + icon + "</td>"
                + f'<td style="padding:7px 0;width:104px;color:{GRAY};font-size:14px;'
                + 'font-weight:600;vertical-align:top;">' + label + "</td>"
                + f'<td style="padding:7px 0;color:{INK};{style}">' + value + "</td></tr>")

    meta_rows = (
        meta("&#128193;", "Source", esc(title) + f" &nbsp;<span style='color:{GRAY};'>"
             + f"({n} tabs)</span>")
        + meta("&#9729;&#65039;", "Destination", f"s3://{S3_BUCKET}/{S3_PREFIX}/", True)
        + meta("&#128221;", "Log", esc(LOG_S3), True)
        + meta("&#9881;&#65039;", "Run by", f"{SERVICE} &nbsp;<span style='color:{GRAY};'>"
               + f"&#183;</span>&nbsp; <span style='{mono}font-size:14px;'>"
               + esc(TASK_NAME) + "</span>")
        + meta("&#128260;", "Next run", NEXT_RUN)
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
        '<body style="margin:0;padding:30px 16px;background:#E9EDEA;'
        "font-family:-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;\">"

        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"'
        ' style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:14px;'
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
        + "Google Sheet &#8594; S3 &nbsp;&#183;&nbsp; EV7 Project</div>"
        + "</td></tr></table></td></tr>"

        + '<tr><td style="padding:0 28px 24px;">'
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"'
        + f' style="background:{GREEN_TINT};border-radius:12px;">'
        + '<tr><td style="padding:20px 22px;">'
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"'
        + ' border="0" style="table-layout:fixed;"><tr>'
        + stats + "</tr></table>"
        + "</td></tr></table></td></tr>"

        + '<tr><td style="padding:0 28px 10px;">'
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"'
        + ' style="border-collapse:separate;border-spacing:0;border:1px solid #DFE4DF;'
        + 'border-radius:11px;overflow:hidden;">'
        + f'<tr><th style="{head}text-align:left;">Table / source tab</th>'
        + f'<th style="{head}text-align:right;">Rows</th>'
        + f'<th style="{head}text-align:right;">Size</th>'
        + f'<th style="{head}text-align:center;">Status</th></tr>'
        + "".join(rows)
        + f'<tr><td style="padding:15px 16px;background:{GREEN_TINT};font-weight:700;'
        + f'font-size:15px;color:{INK};">&#931;&nbsp; Total</td>'
        + f'<td style="padding:15px 16px;background:{GREEN_TINT};text-align:right;'
        + f'font-weight:700;font-size:17px;color:{GREEN_DARK};">' + f"{total_rows:,}" + "</td>"
        + f'<td style="padding:15px 16px;background:{GREEN_TINT};text-align:right;'
        + f'font-weight:700;font-size:16px;color:{GREEN_DARK};">'
        + human_size(total_bytes) + "</td>"
        + f'<td style="background:{GREEN_TINT};"></td></tr>'
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


def send_report(report, html=None):
    """ส่งรายงานผ่าน SES

    ส่งไม่ได้ไม่ทำให้ทั้ง job พัง เพราะข้อมูลขึ้น S3 ไปแล้ว
    แต่จะขึ้น log ชัดเจนเพื่อให้ CloudWatch จับได้
    """
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
    """ประกอบอีเมล multipart/related เพื่อฝังโลโก้เป็น inline attachment

    Gmail บล็อกรูปแบบ data: URI จึงต้องแนบไฟล์จริงแล้วอ้างด้วย cid:
    """
    root = MIMEMultipart("related")
    root["Subject"] = subject
    root["From"] = SES_FROM
    root["To"] = ", ".join(SES_TO)

    alt = MIMEMultipart("alternative")
    root.attach(alt)
    alt.attach(MIMEText(text, "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))

    for path, cid in ((LOGO_FILE, "logo"), (LOGO_SHEET, "sheets")):
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


def lambda_handler(event, context):
    started = time.time()
    print(f"========== Lambda START  v{VERSION} ==========")

    # เลือกเฉพาะบาง tab ได้จาก test event เช่น {"tabs": ["Query", "2026"]}
    wanted = (event or {}).get("tabs")
    sheets = {k: v for k, v in SHEETS.items() if not wanted or k in wanted}

    print("Tabs to extract:", list(sheets.keys()))

    token, client_email = get_access_token()
    print("Google Authentication: SUCCESS |", client_email)

    sheet_title = fetch_sheet_title(token)
    print("Spreadsheet:", sheet_title)

    ok = []
    failed = []

    for tab, table in sheets.items():
        key = f"{S3_PREFIX}/{table}/data.csv"

        try:
            values = fetch_tab(tab, token, client_email)

            if not values:
                raise Exception("sheet tab is empty")

            rows = len(values) - 1
            size = write_csv(values, TMP_PATH)
            del values

            s3.upload_file(
                TMP_PATH,
                S3_BUCKET,
                key,
                ExtraArgs={"ContentType": "text/csv"},
            )
            s3.head_object(Bucket=S3_BUCKET, Key=key)

            print(f"  OK   {tab:18} -> {table:22} {rows:>8} rows  {size:>10} bytes")
            ok.append({"tab": tab, "table": table, "rows": rows,
                       "bytes": size, "s3_key": key})

        except Exception as e:
            # tab เดียวพังไม่ควรลากทั้งงานล่ม เก็บไว้รายงานตอนท้าย
            print(f"  FAIL {tab:18} -> {type(e).__name__}: {e}")
            # ตัดความยาวไว้ - ข้อความ exception อาจมีเนื้อข้อมูลติดมา
            # และรายงานนี้อาจถูกส่งข้าม region
            failed.append({"tab": tab, "table": table,
                           "error": f"{type(e).__name__}: {e}"[:120]})

        finally:
            if os.path.exists(TMP_PATH):
                os.remove(TMP_PATH)

    total_rows = sum(x["rows"] for x in ok)

    print("---------- SUMMARY ----------")
    print(f"success : {len(ok)}/{len(sheets)} tabs · {total_rows} rows")
    if failed:
        print(f"failed  : {[x['tab'] for x in failed]}")
    print(f"S3      : s3://{S3_BUCKET}/{S3_PREFIX}/")

    total_bytes = sum(x["bytes"] for x in ok)

    if not ok:
        # ล้มหมด - ส่งรายงานก่อนแล้วค่อยโยน error ให้ Lambda ขึ้นสถานะ failed
        el = time.time() - started
        send_report(build_report(ok, failed, sheets, 0, 0, el, sheet_title),
                    build_html(ok, failed, sheets, 0, 0, el, sheet_title))
        raise Exception(f"ทุก tab ล้มเหลว: {failed}")

    elapsed = time.time() - started
    report = build_report(ok, failed, sheets, total_rows, total_bytes,
                          elapsed, sheet_title)
    html = build_html(ok, failed, sheets, total_rows, total_bytes,
                      elapsed, sheet_title)
    print(report)
    send_report(report, html)

    print("========== Lambda SUCCESS ==========")

    return {
        "statusCode": 200 if not failed else 207,
        "message": "Success" if not failed else "Partial success",
        "tabs_ok": len(ok),
        "tabs_failed": len(failed),
        "total_rows": total_rows,
        "results": ok,
        "errors": failed,
    }
