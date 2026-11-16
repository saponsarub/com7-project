# -*- coding: utf-8 -*-
"""EV7 — hourly email: vehicles outside Bangkok + vicinity (same look as the Google Sheet ingest report)

ใช้จาก outzone.py (คำสั่ง report / hourly) · ส่งผ่าน Gmail SMTP · ข้อความในอีเมลเป็นภาษาอังกฤษเป็นหลัก

env (ห้ามเขียนรหัสลงไฟล์)
  MAIL_USER          บัญชีผู้ส่ง เช่น xxx@gmail.com
  MAIL_APP_PASSWORD  App Password 16 ตัวของบัญชีนั้น (Google Account → Security → App passwords)
  MAIL_TO            ผู้รับ คั่นด้วย , ได้หลายคน
  MAIL_SMTP          default smtp.gmail.com:587
"""
import base64
import csv
import io
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "lambda" / "googlesheet-to-s3"          # โลโก้ชุดเดียวกับรายงาน Google Sheet
LOGOS = {"logo": ASSETS / "logocom7.png", "ev7": ASSETS / "ev7logo.png"}

TEAM = "Data Management Team"
VERSION = "1.1.0"

# สีจากโลโก้ COM7 (เหมือน lambda_function.py)
GREEN, GREEN_DARK, GREEN_TINT = "#58B040", "#357C27", "#EEF7EA"
GRAY, GRAY_SOFT, INK = "#5F6670", "#8A9099", "#1A1D21"
AMBER_DARK, RED = "#B15E06", "#B0261A"
FONT = "-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,Tahoma,sans-serif"
ZONE_TXT = "Bangkok + vicinity (Nonthaburi · Pathum Thani · Samut Prakan · Nakhon Pathom · Samut Sakhon)"


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def dt(d, year=False):
    if d is None:
        return "-"
    return f"{d.day} {d:%b}" + (f" {d:%Y}" if year else "") + f" {d:%H:%M}"


def dur(h):
    d, hh = divmod(int(h), 24)
    return f"{d} d {hh} h" if d else f"{hh} h"


def level(r, limit_h):
    if r["hours_out"] > limit_h:
        return f"&gt; {limit_h // 24} days", RED, "#FDF3F2"
    if r["hours_out"] >= 24:
        return "&gt; 1 day", AMBER_DARK, "#FFF6EA"
    return "&gt; 5 h", GREEN_DARK, "#F3F9F0"


def build_html(rows, summary, limit_h, test=False, max_rows=200):
    """rows: vehicles outside the zone > min_h (most hours first) · summary: header numbers"""
    now = datetime.now()
    mh = summary["min_h"]
    # no grid lines: zebra rows + rounded header row · every header centred
    cell = f"padding:14px 14px;font-size:16px;line-height:1.45;color:{INK};text-align:center;"
    num = cell + "white-space:nowrap;"
    head = (f"padding:14px 14px;font-size:14px;font-weight:700;color:#ffffff;letter-spacing:.03em;"
            f"background:{GREEN_DARK};text-align:center;vertical-align:middle;")
    body = []
    for i, r in enumerate(rows[:max_rows]):
        lab, col, tint = level(r, limit_h)
        bg = f"background:{tint};" if r["hours_out"] > limit_h else ("background:#F4F7F4;" if i % 2 else "")
        n_alert = r.get("alerts_sent")
        alert_td = (f'<td style="{num}{bg}"><span style="display:inline-block;min-width:34px;padding:4px 8px;border-radius:14px;'
                    f'background:{col};color:#ffffff;font-weight:700;font-size:15px;">{n_alert:,}</span></td>'
                    if n_alert is not None else f'<td style="{num}{bg}color:{GRAY_SOFT};">-</td>')
        atleast = "&ge; " if r.get("out_since_is_first_seen") else ""
        stale = (f'<div style="font-size:14px;color:{RED};margin-top:3px;font-weight:600;">&#9888;&#65039; No signal</div>'
                 if r.get("stale") else "")
        prov = esc(r.get("last_province") or "-")
        if r.get("last_lat") is not None:
            prov = (f'<a href="https://www.google.com/maps?q={r["last_lat"]:.5f},{r["last_lon"]:.5f}" '
                    f'style="color:{INK};text-decoration:underline;">{prov}</a>')
        body.append(
            "<tr>"
            + f'<td style="{cell}{bg}white-space:nowrap;font-weight:700;color:{GREEN_DARK};font-size:17px;">'
            + esc(r.get("plate") or r["vin"]) + "</td>"
            + f'<td style="{cell}{bg}">{prov}</td>'
            + f'<td style="{num}{bg}color:{GRAY};">{esc(dt(r["out_since"]))}</td>'
            + f'<td style="{num}{bg}font-weight:700;font-size:17px;">{atleast}{esc(dur(r["hours_out"]))}</td>'
            + f'<td style="{num}{bg}color:{GRAY};">{esc(dt(r.get("last_seen")))}{stale}</td>'
            + f'<td style="{cell}{bg}text-align:center;white-space:nowrap;">'
            + f'<span style="display:inline-block;padding:4px 12px;border-radius:14px;font-size:14px;'
            + f'font-weight:700;color:{col};border:1.5px solid {col};">{lab}</span></td>'
            + alert_td + "</tr>")
    if not rows:
        body.append(f'<tr><td colspan="7" style="{cell}text-align:center;color:{GRAY};padding:28px;">'
                    f"No vehicle has been outside the zone for more than {mh} h &#9989;</td></tr>")
    more = ""
    if len(rows) > max_rows:
        more = (f'<tr><td style="padding:0 28px 18px;font-size:15px;color:{GRAY};">'
                f"Showing {max_rows} of {len(rows):,} vehicles &#183; the full list is in the attached Excel file.</td></tr>")

    stat = ('<td width="25%" style="width:25%;text-align:center;border-left:{b};padding:0 8px;">'
            f'<div style="font-size:14px;color:{GRAY};font-weight:700;">' + '{label}</div>'
            '<div style="font-size:32px;font-weight:700;color:{c};margin-top:6px;">{v}</div></td>')
    sep = "1px solid #D6E6CE"
    stats = (stat.format(b="none", label="Vehicles with data", c=GREEN_DARK, v=f'{summary["cars"]:,}')
             + stat.format(b=sep, label=f"Outside &gt; {mh} h", c=AMBER_DARK, v=f'{summary["out"]:,}')
             + stat.format(b=sep, label=f"Over {limit_h // 24} days", c=RED, v=f'{summary["over"]:,}')
             + stat.format(b=sep, label="No signal", c=GRAY, v=f'{summary["stale"]:,}'))

    def meta(icon, label, value):
        return ('<tr><td style="padding:7px 0;width:30px;font-size:18px;vertical-align:top;">' + icon + "</td>"
                f'<td style="padding:7px 0;width:150px;color:{GRAY};font-size:15px;font-weight:700;vertical-align:top;">'
                + label + f'</td><td style="padding:7px 0;color:{INK};font-size:15px;line-height:1.5;">' + value + "</td></tr>")

    fresh = summary["data_to"]
    lag_h = (summary["as_of"] - fresh).total_seconds() / 3600 if fresh else None
    fresh_txt = esc(dt(fresh, True)) + (
        f' &nbsp;<span style="color:{RED};font-weight:700;">(not fresh &#183; {dur(lag_h)} behind)</span>'
        if lag_h is not None and lag_h > 2 else "")
    meta_rows = (meta("&#128225;", "GPS data up to", fresh_txt)
                 + meta("&#128205;", "Zone", ZONE_TXT)
                 + meta("&#128203;", "Included", f"Vehicles outside the zone continuously for more than {mh} h "
                        f"({summary['out']:,} of {summary['out_all']:,} currently outside)")
                 + meta("&#128207;", "Rule", f"The clock starts at the first GPS point outside the zone &#183; a vehicle is back "
                        f"after 2 points in a row inside &#183; red = over {limit_h} h ({limit_h // 24} days) &#183; "
                        "&ge; = never seen inside in the data, so the real time may be longer")
                 + meta("&#128260;", "Next run", esc(dt(summary["as_of"] + timedelta(hours=1)))))

    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        f'<body style="margin:0;padding:30px 16px;background:#E9EDEA;font-family:{FONT};">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"'
        ' style="max-width:980px;margin:0 auto;background:#ffffff;border-radius:14px;'
        'box-shadow:0 2px 14px rgba(0,0,0,.12);">'
        f'<tr><td style="height:7px;background:{GREEN};font-size:0;line-height:0;border-radius:14px 14px 0 0;">&nbsp;</td></tr>'
        # header: COM7 logo · title (same line) · EV7 logo + time
        + '<tr><td style="padding:26px 28px 22px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
        '<td style="vertical-align:middle;width:140px;padding-right:22px;border-right:2px solid #E3E8E3;">'
        '<img src="cid:logo" alt="COM7" width="130" style="display:block;border:0;height:auto;"></td>'
        '<td style="vertical-align:middle;padding-left:22px;">'
        f'<div style="font-size:28px;font-weight:700;color:{INK};line-height:1.25;">'
        f"Vehicles Outside Bangkok &amp; Vicinity &gt; {mh} h</div>"
        f'<div style="font-size:17px;color:{GRAY};margin-top:6px;font-weight:600;">'
        f"รถอยู่นอกเขต กทม. และปริมณฑล เกิน {mh} ชม. &#183; Hourly report &#183; EV7 Taxi</div></td>"
        f'<td style="vertical-align:middle;text-align:right;white-space:nowrap;color:{GRAY};font-size:15px;line-height:1.7;font-weight:600;">'
        '<img src="cid:ev7" alt="EV7" width="70" style="display:inline-block;border:0;height:auto;margin-bottom:4px;"><br>'
        f'{now:%d %b %Y}<br>{now:%H:%M} (UTC+7)</td>'
        "</tr></table></td></tr>"
        # stats
        + '<tr><td style="padding:0 28px 24px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"'
        f' style="background:{GREEN_TINT};border-radius:12px;"><tr><td style="padding:20px 20px;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="table-layout:fixed;"><tr>'
        + stats + "</tr></table></td></tr></table></td></tr>"
        # table
        + '<tr><td style="padding:0 28px 22px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"'
        ' style="border-collapse:separate;border-spacing:0;">'
        f'<tr><th style="{head}border-radius:10px 0 0 10px;">Plate</th>'
        f'<th style="{head}">Last province</th><th style="{head}">Left the zone</th><th style="{head}">Time outside</th>'
        f'<th style="{head}">Last GPS</th><th style="{head}">Level</th><th style="{head}border-radius:0 10px 10px 0;">Alerts<br>sent</th></tr>'
        + "".join(body) + "</table></td></tr>"
        + more
        + '<tr><td style="padding:6px 28px 16px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
        + meta_rows + "</table></td></tr>"
        f'<tr><td style="padding:20px 28px;background:#F7F9F7;border-top:1px solid #E9ECE9;border-radius:0 0 14px 14px;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td style="font-size:15px;color:{GRAY};"><b style="color:{INK};font-size:16px;">{TEAM}</b>'
        f'<span style="color:{GRAY_SOFT};"> &#183; COM7</span><br>'
        f'<span style="font-size:14px;color:{GRAY_SOFT};">Automated message &#8212; please do not reply</span></td>'
        f'<td style="text-align:right;font-size:14px;color:{GRAY_SOFT};">SSOT server &#183; Bangkok<br>v{VERSION}</td>'
        "</tr></table></td></tr></table></body></html>")


def build_text(rows, summary, limit_h):
    mh = summary["min_h"]
    out = [f"EV7 · Vehicles outside Bangkok & vicinity > {mh} h · {dt(summary['as_of'], True)}",
           f"Outside > {mh} h: {summary['out']:,} · over {limit_h // 24} days: {summary['over']:,}", ""]
    for r in rows[:50]:
        out.append(f"- {r.get('plate') or r['vin']} · {r.get('last_province') or '-'} · {dur(r['hours_out'])}")
    return "\n".join(out)


def build_xlsx(rows, summary, limit_h, dummy=False):
    """Excel แนบท้ายอีเมล · รวมผู้ติดต่อ (คนขับ/เจ้าของรถ) · dummy=True = ข้อมูลผู้ติดต่อสมมติ"""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook(); ws = wb.active; ws.title = "Outside zone"
    tag = " (DUMMY)" if dummy else ""
    ws.append([f"EV7 · Vehicles outside Bangkok & Vicinity > {summary['min_h']} h · as of {dt(summary['as_of'], True)}"
               + (" · contact data is DUMMY for testing" if dummy else "")])
    ws["A1"].font = Font(bold=True, size=13, color="B0261A" if dummy else "1A1D21")
    cols = ["Plate", "VIN", f"Contact name{tag}", f"Phone{tag}", f"Email{tag}", "Last province",
            "Left the zone", "Hours outside", "Time outside", "Last GPS", "No signal", "Level", "Map", "Alerts sent"]
    ws.append([]); ws.append(cols)
    hdr = 3
    for c in range(1, len(cols) + 1):
        x = ws.cell(row=hdr, column=c)
        x.font = Font(bold=True, color="FFFFFF"); x.fill = PatternFill("solid", fgColor="357C27")
        x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for r in rows:
        lab = level(r, limit_h)[0].replace("&gt;", ">")
        maps = (f'https://www.google.com/maps?q={r["last_lat"]:.5f},{r["last_lon"]:.5f}' if r.get("last_lat") is not None else "")
        ws.append([r.get("plate"), r.get("vin"), r.get("contact_name"), r.get("contact_phone"),
                   r.get("contact_email"), r.get("last_province"), r["out_since"], round(r["hours_out"], 1),
                   ("≥ " if r.get("out_since_is_first_seen") else "") + dur(r["hours_out"]), r.get("last_seen"),
                   "Yes" if r.get("stale") else "", lab, maps, r.get("alerts_sent")])
        if maps:
            ws.cell(row=ws.max_row, column=13).hyperlink = maps
    widths = [11, 20, 24, 15, 30, 24, 17, 13, 14, 17, 10, 11, 16, 11]
    for k, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(k)].width = w
    for row in ws.iter_rows(min_row=hdr + 1):
        for x in row:
            x.alignment = Alignment(horizontal="center", vertical="center")
        row[6].number_format = row[9].number_format = "dd mmm yyyy hh:mm"
    ws.freeze_panes = ws.cell(row=hdr + 1, column=2)
    ws.auto_filter.ref = f"A{hdr}:{get_column_letter(len(cols))}{ws.max_row}"
    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue()


def build_csv(rows):
    buf = io.StringIO()
    cols = ["plate", "vin", "car_id", "last_province", "out_since", "out_since_is_first_seen", "hours_out",
            "last_seen", "stale", "last_lat", "last_lon"]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
    w.writeheader(); w.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")         # BOM ให้ Excel อ่านไทยถูก


def preview(html, path):
    """แทน cid: ด้วย data URI เพื่อเปิดดูในเบราว์เซอร์"""
    for cid, p in LOGOS.items():
        if p.exists():
            html = html.replace(f"cid:{cid}", "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode())
    Path(path).write_text(html, encoding="utf-8")
    return path


def send(subject, text, html, attachments=()):
    user, pwd = os.environ.get("MAIL_USER"), (os.environ.get("MAIL_APP_PASSWORD") or "").replace(" ", "")   # Google แสดงรหัสเป็น 4 กลุ่มมีช่องว่าง
    to = [x.strip() for x in os.environ.get("MAIL_TO", "").split(",") if x.strip()]
    if not (user and pwd and to):
        raise SystemExit("ยังไม่ได้ตั้ง MAIL_USER / MAIL_APP_PASSWORD / MAIL_TO")
    root = MIMEMultipart("mixed")
    root["Subject"], root["From"], root["To"] = subject, f"EV7 Monitor <{user}>", ", ".join(to)
    rel = MIMEMultipart("related"); root.attach(rel)
    alt = MIMEMultipart("alternative"); rel.attach(alt)
    alt.attach(MIMEText(text, "plain", "utf-8")); alt.attach(MIMEText(html, "html", "utf-8"))
    for cid, p in LOGOS.items():
        if p.exists():
            img = MIMEImage(p.read_bytes(), _subtype="png")
            img.add_header("Content-ID", f"<{cid}>"); img.add_header("Content-Disposition", "inline", filename=p.name)
            rel.attach(img)
    for name, data in attachments:
        part = MIMEApplication(data, Name=name); part["Content-Disposition"] = f'attachment; filename="{name}"'
        root.attach(part)
    host, port = (os.environ.get("MAIL_SMTP", "smtp.gmail.com:587").split(":") + ["587"])[:2]
    with smtplib.SMTP(host, int(port), timeout=60) as s:
        s.starttls(); s.login(user, pwd); s.send_message(root)
    return to
