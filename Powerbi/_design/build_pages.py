# -*- coding: utf-8 -*-
"""วาง visual ลงบนแผงที่วาดไว้ใน bg_p*.png — พิกัดมาจาก layout.py ตัวเดียวกัน

หัวข้อทุกอันวาดลงภาพพื้นหลังไปแล้ว ที่นี่จึงไม่ใส่ title ให้ visual
theme ก็ปิด title ทิ้ง เพื่อคุมงานตัวอักษรเองทั้งหมด
"""
import json, io, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
from layout import PAGES, RAIL, W, H, inner, kpi_cells             # noqa: F403

os.chdir(r"C:\Projects\my-first-project\Powerbi")
E = "ci npi_iphone (2)"
PG = "booking_npi.Report/definition/pages"
SCH = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/1.4.0/schema.json"
PSCH = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
PMSCH = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"

PID = {1: "758740409d41497dd040", 2: "b2f41a90c7e5486d1a03",
       3: "c3d82b07f1964ae2b518", 4: "d4a19e6b35f0472c9d27"}

src = {"SourceRef": {"Entity": E}}
meas = lambda n: {"field": {"Measure": {"Expression": src, "Property": n}},
                  "queryRef": E + "." + n, "nativeQueryRef": n}
col = lambda n: {"field": {"Column": {"Expression": src, "Property": n}},
                 "queryRef": E + "." + n, "nativeQueryRef": n}
lit = lambda v: {"expr": {"Literal": {"Value": v}}}
LAB = {"labels": [{"properties": {"show": lit("true")}}]}
_z = [0]


def put(pid, name, box, v):
    x, y, w, h = (int(round(n)) for n in box)
    _z[0] += 1
    d = f"{PG}/{pid}/visuals/{name}"
    os.makedirs(d, exist_ok=True)
    io.open(d + "/visual.json", "w", encoding="utf-8", newline="\n").write(json.dumps(
        {"$schema": SCH, "name": name,
         "position": {"x": x, "y": y, "z": _z[0], "width": w, "height": h,
                      "tabOrder": _z[0]},
         "visual": v}, ensure_ascii=False, indent=2))


def V(pid, name, box, vtype, roles, objects=None):
    v = {"visualType": vtype,
         "query": {"queryState": {k: {"projections": p} for k, p in roles.items()}},
         "drillFilterOtherVisuals": True}
    if objects:
        v["objects"] = objects
    put(pid, name, box, v)


def card(pid, name, box, measure, size):
    """การ์ดตัวเลข — คุม fontSize รายใบ เพื่อให้ตัว hero ใหญ่กว่าเพื่อน"""
    V(pid, name, box, "card", {"Values": [meas(measure)]},
      {"labels": [{"properties": {"fontSize": lit(str(size))}}]})


def new_page(n):
    pid = PID[n]
    cfg = PAGES[n]
    shutil.rmtree(f"{PG}/{pid}", ignore_errors=True)
    os.makedirs(f"{PG}/{pid}")
    io.open(f"{PG}/{pid}/page.json", "w", encoding="utf-8", newline="\n").write(json.dumps(
        {"$schema": PSCH, "name": pid, "displayName": cfg["nav"],
         "displayOption": "FitToPage", "height": H, "width": W},
        ensure_ascii=False, indent=2))
    _z[0] = 0
    put(pid, "pagebg", (0, 0, W, H), {                      # z ต่ำสุด อยู่ใต้ทุกอัน
        "visualType": "image",
        "objects": {"general": [{"properties": {
            "imageUrl": {"expr": {"ResourcePackageItem": {
                "PackageName": "RegisteredResources", "PackageType": 1,
                "ItemName": f"bg_p{n}.png"}}},
            "imageScaling": lit("'Fit'")}}]},
        "drillFilterOtherVisuals": True})

    # ── การ์ด KPI: ค่าหลัก + ส่วนต่างเทียบรุ่นก่อน ──────────────────────
    cells = kpi_cells(len(cfg["kpi"]), cfg["hero"]) if cfg["kpi"] else []
    for i, ((lab, m, delta, unit), (x, y, w, h)) in enumerate(zip(cfg["kpi"], cells)):
        hero = cfg["hero"] and i == 0
        card(pid, f"kpi{i}", (x + 12, y + 30, w - 24, 44), m, 34 if hero else 24)
        if delta:
            card(pid, f"kpid{i}", (x + w - 92, y + h - 30, 78, 24), delta, 12)

    # ── ตัวกรองใน sidebar ──────────────────────────────────────────────
    top = 196
    for nm, c in cfg["filters"]:
        V(pid, nm, (20, top, RAIL - 40, 168), "slicer", {"Values": [col(c)]})
        top += 184
    return pid, cfg


# ═══ 1 · ภาพรวม ══════════════════════════════════════════════════════
pid, cfg = new_page(1)
p = [b for b, _ in cfg["panels"]]
V(pid, "colMix", inner(p[0]), "columnChart",
  {"Category": [col("Launch Cohort")], "Series": [col("clean_iPhone_submodel")],
   "Y": [meas("Bookings")]}, LAB)
V(pid, "lineDay", inner(p[1]), "lineChart",
  {"Category": [col("Launch Day")], "Series": [col("Launch Cohort")],
   "Y": [meas("Bookings")]})
V(pid, "tbl", inner(p[2]), "tableEx",
  {"Values": [col("Launch Cohort"), meas("Bookings Pro Only"), meas("Bookings YoY %"),
              meas("Value M Pro Only"), meas("Value YoY %"), meas("Avg Price"),
              meas("Pro Max Share %"), meas("Completion %")]})

# ═══ 2 · พื้นที่ · สาขา ═══════════════════════════════════════════════
pid, cfg = new_page(2)
p = [b for b, _ in cfg["panels"]]
V(pid, "barRegion", inner(p[0]), "barChart",
  {"Category": [col("book_region_en")], "Series": [col("Launch Cohort")],
   "Y": [meas("Bookings")]})
V(pid, "barBrand", inner(p[1]), "barChart",
  {"Category": [col("book_shop_brand")], "Series": [col("Launch Cohort")],
   "Y": [meas("Bookings")]})
V(pid, "tblProv", inner(p[2]), "tableEx",
  {"Values": [col("book_province"), meas("Bookings"), meas("Value M"), meas("Avg Price"),
              meas("Branches"), meas("Pending Pickup"), meas("Completion %")]})

# ═══ 3 · สินค้า · ราคา ════════════════════════════════════════════════
pid, cfg = new_page(3)
p = [b for b, _ in cfg["panels"]]
V(pid, "colSub", inner(p[0]), "columnChart",
  {"Category": [col("Launch Cohort")], "Series": [col("clean_iPhone_submodel")],
   "Y": [meas("Bookings")]}, LAB)
V(pid, "colMem", inner(p[1]), "columnChart",
  {"Category": [col("device_memory")], "Series": [col("Launch Cohort")],
   "Y": [meas("Bookings")]})
V(pid, "barColor", inner(p[2]), "barChart",
  {"Category": [col("device_color")], "Y": [meas("Bookings")]})
V(pid, "barPay", inner(p[3]), "barChart",
  {"Category": [col("installment_type")], "Series": [col("Launch Cohort")],
   "Y": [meas("Bookings")]})
V(pid, "tblSub", inner(p[4], top=36), "tableEx",
  {"Values": [col("clean_iPhone_submodel"), meas("Bookings"), meas("Value M"),
              meas("Avg Price")]})

# ═══ 4 · วันรับเครื่อง ════════════════════════════════════════════════
pid, cfg = new_page(4)
p = [b for b, _ in cfg["panels"]]
V(pid, "pkRegion", inner(p[0]), "barChart",
  {"Category": [col("book_region_en")], "Series": [col("Launch Cohort")],
   "Y": [meas("Pending Pickup")]}, LAB)
V(pid, "pkDay", inner(p[1]), "columnChart",
  {"Category": [col("Launch Day")], "Series": [col("Launch Cohort")],
   "Y": [meas("Bookings")]})
V(pid, "pkBranch", inner(p[2]), "tableEx",
  {"Values": [col("book_cleanbranchname"), col("book_region_en"), col("book_shop_brand"),
              meas("Bookings"), meas("Pending Pickup"), meas("Completion %")]})

io.open(f"{PG}/pages.json", "w", encoding="utf-8", newline="\n").write(json.dumps(
    {"$schema": PMSCH, "pageOrder": [PID[n] for n in (1, 2, 3, 4)],
     "activePageName": PID[1]}, ensure_ascii=False, indent=2))

# ── ตรวจว่าทุก visual อยู่ในกรอบที่ควรอยู่ ──────────────────────────────
bad = []
for n, pid in PID.items():
    cfg = PAGES[n]
    ok = [b for b, _ in cfg["panels"]]
    ok += [(x, y, x + w, y + h) for x, y, w, h in
           (kpi_cells(len(cfg["kpi"]), cfg["hero"]) if cfg["kpi"] else [])]
    ok += [(0, 0, RAIL, H)]                                     # sidebar
    vs = sorted(os.listdir(f"{PG}/{pid}/visuals"))
    for v in vs:
        q = json.load(io.open(f"{PG}/{pid}/visuals/{v}/visual.json",
                              encoding="utf-8"))["position"]
        if v == "pagebg":
            continue
        r = (q["x"], q["y"], q["x"] + q["width"], q["y"] + q["height"])
        if not any(a <= r[0] and b <= r[1] and r[2] <= c and r[3] <= e
                   for a, b, c, e in ok):
            bad.append(f"หน้า{n}/{v}{r}")
    print(f"  หน้า {n} {cfg['nav']:16} {len(vs):2} visual")
print("หลุดกรอบ:", bad or "ไม่มี")
