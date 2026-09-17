# -*- coding: utf-8 -*-
"""วาดภาพพื้นหลังหน้าละ 1 ไฟล์ — sidebar · หัวเรื่อง · แผง · เงา · ป้าย KPI

ทำไมต้องวาดเอง
  Power BI theme ทำ sidebar หรือแผงคร่อมหลาย visual ไม่ได้
  คุมงานตัวอักษรได้แค่ fontSize · เงาของมันหนาเกิน
  visual ชนิด image พิสูจน์แล้วว่าเขียนผ่านไฟล์แล้วขึ้น จึงใช้เป็นพื้นหลัง
  แล้วปิด title ของ Power BI ทิ้ง เพื่อคุมตัวอักษรเองทั้งหมด
"""
import os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
from layout import *                                             # noqa: F403

ROOT = r"C:\Projects\my-first-project"
OUT = os.path.join(ROOT, "Powerbi", "booking_npi.Report",
                   "StaticResources", "RegisteredResources")

F = lambda n, s: ImageFont.truetype(f"C:/Windows/Fonts/{n}", s)
BOLD, REG = "leelauib.ttf", "LeelawUI.ttf"
f_h1    = F(BOLD, 19)
f_h2    = F(REG, 12)
f_panel = F(BOLD, 12)
f_nav   = F(BOLD, 13)
f_rail  = F(REG, 11)
f_klab  = F(REG, 11)
f_kunit = F(REG, 10)
f_foot  = F(REG, 10)


def grad(size, a, b, horizontal=False):
    w, h = size
    n = w if horizontal else h
    g = Image.new("RGB", (w, 1) if horizontal else (1, h))
    px = g.load()
    for i in range(n):
        t = i / max(n - 1, 1)
        c = tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(3))
        px[(i, 0) if horizontal else (0, i)] = c
    return g.resize((w, h), Image.BILINEAR)


def logo_light():
    """โลโก้ต้นฉบับพื้นขาวทึบ — บน sidebar เข้มต้องทำพื้นโปร่ง + ตัว com เป็นขาว"""
    im = Image.open(os.path.join(ROOT, "logocom7.png")).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a < 8:
                continue
            if abs(r - g) < 26 and abs(g - b) < 26:                # โทนเทา ไม่ใช่เขียว
                px[x, y] = (255, 255, 255, 0 if min(r, g, b) > 232 else 255)
    w = 116
    return im.resize((w, round(w * im.height / im.width)), Image.LANCZOS)


def build(page):
    cfg = PAGES[page]
    im = grad((W, H), CANVAS_T, CANVAS_B)
    panels = [p for p, _ in cfg["panels"]]
    kpis = kpi_cells(len(cfg["kpi"]), cfg["hero"]) if cfg["kpi"] else []
    boxes = panels + [(x, y, x + w, y + h) for x, y, w, h in kpis]

    # ── เงานุ่มใต้ทุกแผง ────────────────────────────────────────────
    sh = Image.new("L", (W, H), 0)
    ds = ImageDraw.Draw(sh)
    for x0, y0, x1, y1 in boxes:
        ds.rounded_rectangle((x0 + 1, y0 + 3, x1 - 1, y1 + 4), 10, fill=38)
    im.paste(Image.new("RGB", (W, H), (124, 138, 156)),
             (0, 0), sh.filter(ImageFilter.GaussianBlur(8)))

    d = ImageDraw.Draw(im)
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        hero = cfg["hero"] and i == len(panels)            # เซลล์ KPI ใบแรก
        d.rounded_rectangle((x0, y0, x1, y1), 10,
                            fill=HERO_BG if hero else PANEL, outline=EDGE, width=1)
        if hero:
            d.rounded_rectangle((x0, y0 + 14, x0 + 3, y1 - 14), 2, fill=GREEN)

    # ── sidebar ────────────────────────────────────────────────────
    im.paste(grad((RAIL, H), RAIL_T, RAIL_B), (0, 0))
    lg = logo_light()
    im.paste(lg, (24, 26), lg)
    d.rectangle((24, 84, RAIL - 24, 85), fill=RAIL_LINE)

    d.text((24, 102), cfg["nav"], font=f_nav, fill=(255, 255, 255))
    d.rounded_rectangle((24, 126, 27, 138), 2, fill=GREEN)
    d.text((34, 124), "NPI Launch Week", font=f_rail, fill=RAIL_MUT)

    d.rectangle((24, 160, RAIL - 24, 161), fill=RAIL_LINE)
    d.text((24, 174), "ตัวกรอง", font=f_rail, fill=RAIL_MUT)

    for i, ln in enumerate(FOOTER.split("  ·  ")):
        d.text((24, H - 84 + i * 16), ln, font=f_foot, fill=(96, 112, 130))

    # ── หัวเรื่องบนพื้นที่เนื้อหา ─────────────────────────────────────
    d.text((CX0, 20), cfg["nav"], font=f_h1, fill=INK)
    d.text((CX0, 44), cfg["sub"], font=f_h2, fill=MUTED)

    # ── หัวข้อแต่ละแผง ──────────────────────────────────────────────
    for (x0, y0, x1, y1), title in cfg["panels"]:
        d.rounded_rectangle((x0 + 14, y0 + 15, x0 + 16, y0 + 27), 1, fill=GREEN)
        d.text((x0 + 24, y0 + 11), title, font=f_panel, fill=INK)
        d.rectangle((x0 + 14, y0 + 34, x1 - 14, y0 + 35), fill=RULE)

    # ── ป้ายบน/หน่วยล่างของการ์ด KPI ─────────────────────────────────
    for (lab, _, delta, unit), (x, y, w, h) in zip(cfg["kpi"], kpis):
        d.text((x + 16, y + 13), lab, font=f_klab, fill=INK2)
        d.text((x + w - 16, y + 14), unit, font=f_kunit, fill=(178, 188, 200),
               anchor="ra")
        if delta:
            d.rectangle((x + 16, y + 74, x + w - 16, y + 75), fill=RULE)
            d.text((x + 16, y + h - 24), "เทียบรุ่นก่อนหน้า", font=f_kunit,
                   fill=(178, 188, 200))

    p = os.path.join(OUT, f"bg_p{page}.png")
    im.save(p, optimize=True)
    print(f"  bg_p{page}.png  {os.path.getsize(p)/1024:5.0f} KB · แผง {len(panels)}"
          f" · KPI {len(kpis)}{' (มี hero)' if cfg['hero'] and kpis else ''}")


os.makedirs(OUT, exist_ok=True)
for n in sorted(PAGES):
    build(n)
