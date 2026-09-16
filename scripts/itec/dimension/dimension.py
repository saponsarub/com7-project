# -*- coding: utf-8 -*-
"""เครื่องยนต์จัดหมวดสินค้า ITEC — อ่านกฎจาก rules.yaml แล้วออก 5 คอลัมน์ตาม SQL

    ItemName + CategoryName + SubCategoryName
            │
            ├─► Item_Type      สินค้านี้คืออะไร        Case · Notebook · Charger
            ├─► Item_Host      ใช้กับเครื่องตระกูลไหน   Smart Phone · Tablet · Notebook
            └─► Item_Platform  แบรนด์/รุ่น             iPhone · Galaxy · Asus
                       │
                       ▼  compose() — กฎล้วน ไม่มี ML
            Sale_Type · Product_Dimension · Product_Purpose
            Main_Product_Dimension · Sub_Product_Dimension

⚠️ ห้ามแก้ rules.yaml ด้วยมือ — มันถูกเขียนทับจาก Cell 3 ของ itec_dimension.ipynb

เอกสาร: COM7-Knowledge-Base/05_ETL/ITEC Dimension Pipeline.md
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass          # Jupyter/Colab ไม่มีเมธอดนี้

HERE = Path(__file__).parent
OUT = HERE / "_out"
OUT.mkdir(exist_ok=True)
RULES_FILE = HERE / "rules.yaml"

TEXT_COLS = ["ItemName", "CategoryName", "SubCategoryName"]
ALIASES = {
    "itemid": "ItemId", "item_id": "ItemId",
    "itemname": "ItemName", "item_name": "ItemName", "name": "ItemName",
    "categoryname": "CategoryName", "category": "CategoryName", "category_name": "CategoryName",
    "subcategoryname": "SubCategoryName", "sub_category": "SubCategoryName",
    "subcategory": "SubCategoryName", "sub_category_name": "SubCategoryName",
    "brand": "Brand", "model/series": "ModelSeries", "model_series": "ModelSeries",
}

OUTPUTS = ["Sale_Type", "Product_Dimension", "Product_Purpose",
           "Main_Product_Dimension", "Sub_Product_Dimension"]


# ════════════════════════════════════════════════════════ เตรียมข้อความ ══
def normalize_columns(df):
    """CSV ที่ export มาตั้งชื่อคอลัมน์ไม่เหมือนกัน · map ให้เป็นชื่อกลางก่อน"""
    ren = {c: ALIASES[c.strip().lower().replace(" ", "")]
           for c in df.columns
           if c.strip().lower().replace(" ", "") in ALIASES
           and ALIASES[c.strip().lower().replace(" ", "")] not in df.columns}
    df = df.rename(columns=ren)
    for col in TEXT_COLS + ["Brand"]:
        if col not in df.columns:
            df[col] = ""
    return df


def normalize(s):
    """พิมพ์เล็ก · ตัดอักขระพิเศษ · ยุบช่องว่าง

    ก-๛ ต้องเขียนเป็นอักษรไทยจริง ห้ามใช้ escape แบบ backslash-u
    เพราะ pandas 3 ใช้ Arrow/RE2 ซึ่งไม่รองรับ และ \\w ของ RE2 เป็น ASCII ล้วน
    ถ้าไม่ใส่ ก-๛ ภาษาไทยจะถูกลบทิ้งทั้งหมดโดยไม่มี error
    """
    return (s.fillna("").astype(str).str.lower()
             .str.replace(r"[^\w\s/&+.\-ก-๛]", " ", regex=True)
             .str.replace(r"\s+", " ", regex=True)
             .str.strip())


# ════════════════════════════════════════════════════════════ อ่านกฎ ══
def load_rules(path=RULES_FILE):
    import yaml
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    def tab(key):
        return [(r["label"], r["words"], r.get("whole_word", False))
                for r in d.get(key, [])]

    # use_context True = ให้ดู CategoryName ด้วย (ใช้เฉพาะกฎที่ context เชื่อได้จริง)
    dis = [(r["from"], r["words"], r["to"], r.get("whole_word", False),
            r.get("use_context", False)) for r in d.get("disambiguate", [])]
    host_from_platform = d.get("host_from_platform", {})
    host_from_type = d.get("host_from_type", {})
    # CategoryName -> [Item_Type, Item_Host]  ใช้เป็นชั้นสุดท้ายก่อนตก Unknown
    cat_map = {k.strip().lower(): v for k, v in d.get("category_map", {}).items()}
    # category ที่เชื่อได้มากกว่าชื่อสินค้า -> ทับผลจากชื่อไปเลย
    cat_force = {k.strip().lower(): v for k, v in d.get("category_force", {}).items()}
    type_from_platform = d.get("type_from_platform", {})
    # ตารางประกอบ Main/Sub — ย้ายมาอยู่ใน rules.yaml เพื่อให้แก้ได้จาก Cell 3
    compose_tbl = {
        "main_of_type": d.get("main_of_type", {}),
        "acc_suffix": d.get("acc_suffix", {}),
        "acc_hosts": set(d.get("acc_hosts", [])),
        "not_product": set(d.get("not_product", [])),
    }
    return (tab("types"), tab("hosts"), tab("platforms"), dis, host_from_platform,
            host_from_type, cat_map, cat_force, type_from_platform, compose_tbl)


(TYPES, HOSTS, PLATFORMS, DISAMBIGUATE, HOST_FROM_PLATFORM, HOST_FROM_TYPE,
 CATEGORY_MAP, CATEGORY_FORCE, TYPE_FROM_PLATFORM, COMPOSE) = (
    load_rules() if RULES_FILE.exists() else ([], [], [], [], {}, {}, {}, {}, {}, {}))


def reload_rules():
    """เรียกหลังโน้ตบุ๊กเขียน rules.yaml ใหม่"""
    global TYPES, HOSTS, PLATFORMS, DISAMBIGUATE, HOST_FROM_PLATFORM
    global HOST_FROM_TYPE, CATEGORY_MAP, CATEGORY_FORCE, TYPE_FROM_PLATFORM, COMPOSE
    (TYPES, HOSTS, PLATFORMS, DISAMBIGUATE, HOST_FROM_PLATFORM, HOST_FROM_TYPE,
     CATEGORY_MAP, CATEGORY_FORCE, TYPE_FROM_PLATFORM, COMPOSE) = load_rules()
    return len(TYPES), len(HOSTS), len(PLATFORMS), len(DISAMBIGUATE), len(CATEGORY_MAP)


def _pattern(words, whole_word=False):
    body = "|".join(re.escape(w) for w in words)
    # ขอบเขตคำเขียนเองแทน \b เพราะ \b ไม่ทำงานกับอักษรไทย
    return rf"(?:(?<![a-z0-9])(?:{body})(?![a-z0-9]))" if whole_word else body


def _first(s, table, default):
    return next((label for label, kw, ww in table
                 if re.search(_pattern(kw, ww), s)), default)


# ⚠️ ช่องว่างที่ไม่ใช่ space ธรรมดา — ในข้อมูลจริงมี \xa0 (non-breaking space) ปนอยู่
#    "Apple\xa0Watch Nike+ Series 4" · "HP\xa0ML110\xa0Gen9\xa0Hot\xa0Plug"
#    Python re มองว่า \s ครอบคลุมพวกนี้ แต่ pandas 3 ใช้ RE2 ซึ่ง \s เป็น ASCII ล้วน
#    ถ้าไม่แปลงทิ้งก่อน keyword "apple watch" จะไม่ match และผลสองทางจะไม่ตรงกัน
#    (บั๊กตระกูลเดียวกับที่ \w ทำภาษาไทยหายใน normalize)
_WS_CHARS = " \t\r\n     　​"
_WS_MAP = {ord(ch): " " for ch in _WS_CHARS}


def _squash(text):
    """ทำความสะอาดข้อความ 1 ค่า — ต้องให้ผลเหมือน _clean() ทุกประการ"""
    return re.sub(r"\s+", " ", str(text).translate(_WS_MAP).lower()).strip()


def _clean(series):
    """เวอร์ชันทั้งคอลัมน์ของ _squash()"""
    return (series.fillna("").astype(str).str.translate(_WS_MAP)
                  .str.lower().str.replace(r"\s+", " ", regex=True).str.strip())


# ══════════════════════════════════════════════════════════ จัดหมวด ══
def classify(name, context="", category="", with_flag=False):
    """คืน (Item_Type, Item_Host, Item_Platform)

    ลำดับการตัดสิน — บนสุดเชื่อได้มากสุด
      1. ชื่อสินค้า          ตรงกับ TYPES              <- แม่นสุด
      2. context             CategoryName+SubCategory ที่มีคำตรงกับ TYPES
      3. CATEGORY_MAP        จับคู่ CategoryName ตรง ๆ  <- ชั้นกันตก
      4. Unknown

    ชั้น 3 มีไว้สำหรับของที่ชื่อบอกอะไรไม่ได้เลย เช่น
        "CS@ Roborock H7"        CategoryName = Smart Living   -> SmartHome
        "BB@ Apple iTunes Gift"  CategoryName = GIFT IDEAS     -> Merchandise
    ยอมเชื่อ category เดิมไปก่อนดีกว่าปล่อยเป็น Unknown
    """
    # ยุบช่องว่างก่อนเสมอ — "POWER  SUPPLY" 2 เว้นวรรค และ Apple+NBSP+Watch เคยหลุดทั้งคู่
    s = _squash(name)
    c = _squash(context)

    t = _first(s, TYPES, "Unknown")
    h = _first(s, HOSTS, "")
    p = _first(s, PLATFORMS, "Generic")

    if c:
        if t == "Unknown":
            t = _first(c, TYPES, "Unknown")
        if not h:
            h = _first(c, HOSTS, "")
        if p == "Generic":
            p = _first(c, PLATFORMS, "Generic")

    key = _squash(category)
    used_cat = False

    # ชั้น 3 · จับคู่ CategoryName ตรง ๆ — ใช้เมื่อชื่อกับ context บอกไม่ได้เลย
    cm = CATEGORY_MAP.get(key)
    if cm:
        if t == "Unknown" and cm[0]:
            t = cm[0]
            used_cat = True          # แถวนี้เชื่อ category เดิม -> ควรตรวจเป็นพิเศษ
        if not h and len(cm) > 1 and cm[1]:
            h = cm[1]

    # ชั้น 4 · เดาจากแบรนด์ — "Apple iPhone 14 128GB Blue" ไม่มีคำว่า smartphone
    if t == "Unknown" and p in TYPE_FROM_PLATFORM:
        t = TYPE_FROM_PLATFORM[p]

    # ⭐ CATEGORY_FORCE · ทับผลจากชื่อ
    #    เช่น APPLE SERVICE เป็นแคตตาล็อกอะไหล่ทั้งก้อน "Bottom Speaker, iPhone 16"
    #    ชื่อมีคำว่า Speaker แต่มันคืออะไหล่ ไม่ใช่ลำโพงที่ขาย
    cf = CATEGORY_FORCE.get(key)
    if cf:
        t = cf[0] if isinstance(cf, (list, tuple)) else cf
        used_cat = True

    # DISAMBIGUATE ปกติดูเฉพาะ "ชื่อสินค้า"
    #   เคยดู context ทุกกฎ แล้วเคสมือถือที่ CategoryName = "Bag" กลายเป็น Bag ทั้งกอง
    # แต่บางกฎ context เชื่อได้จริงและจำเป็น จึงเปิด use_context เป็นราย ๆ ไป
    #   "CASE NEO 747-BS 450W 24PIN" ชื่อไม่มีคำว่า atx/tower เลย
    #   ต้องพึ่ง CategoryName = "PC Case & Cooling" ถึงจะรู้ว่าเป็นเคสคอม
    both = s + " | " + c
    for old, kw, new, ww, use_ctx in DISAMBIGUATE:
        if t == old and re.search(_pattern(kw, ww), both if use_ctx else s):
            t = new
            break

    # ⭐ ตัวเครื่องเป็น host ของตัวเองเสมอ — ทับค่าที่เดาจากชื่อ
    #    "Microsoft Tablet Surface Pro4 Core i5" มีคำว่า Tablet อยู่ในชื่อ
    #    แต่ Item_Type ตัดสินแล้วว่าเป็น Notebook -> host ต้องเป็น Notebook ตาม
    #    ไม่งั้นได้ Type=Notebook แต่ Host=Tablet ซึ่งขัดกันเอง
    if t in HOST_FROM_TYPE:
        h = HOST_FROM_TYPE[t]
    # เดาจากแบรนด์เป็นทางสุดท้าย — iPhone ต้องเป็นมือถือ, iPad ต้องเป็นแท็บเล็ต
    elif not h and p in HOST_FROM_PLATFORM:
        h = HOST_FROM_PLATFORM[p]
    return (t, h, p, used_cat) if with_flag else (t, h, p)


def _first_vec(text, table, default):
    """หากฎแรกที่ตรง — ทำทั้งคอลัมน์รวดเดียว

    เทียบกับ _first() ที่วิ่งทีละแถว: อันนี้ยิง regex ทีละกฎแต่ครอบคลุมทุกแถว
    216,009 แถว x 96 กฎ  ->  96 รอบ แทนที่จะเป็น 20 ล้านครั้ง
    """
    out = pd.Series(default, index=text.index, dtype=object)
    todo = pd.Series(True, index=text.index)
    for label, kw, ww in table:
        if not todo.any():
            break
        hit = todo & text.str.contains(_pattern(kw, ww), regex=True, na=False)
        out[hit] = label
        todo &= ~hit
    return out


def add_columns(df, col="ItemName", context_cols=("CategoryName", "SubCategoryName"), verbose=True):
    """เติม Item_Type / Item_Host / Item_Platform / by_category

    ทำทั้งคอลัมน์รวดเดียว ไม่วนทีละแถว — เร็วกว่าเดิมประมาณ 10 เท่า
    ผลลัพธ์ต้องเท่ากับ classify() ทุกแถว (Cell 4 ในโน้ตบุ๊กเช็คให้อยู่แล้ว)
    """
    def log(m):
        if verbose:
            print(f"  {m}", flush=True)

    name = _clean(df[col])
    cols = [c for c in context_cols if c in df.columns]
    # ⚠️ ห้ามใช้ .agg(" ".join, axis=1) — มันวิ่งทีละแถว ช้ากว่าบวกสตริงตรง ๆ 400 เท่า
    ctx = _clean(df[cols[0]]) if cols else pd.Series("", index=df.index)
    for c in cols[1:]:
        ctx = ctx + " " + _clean(df[c])
    cat_key = _clean(df["CategoryName"]) if "CategoryName" in df.columns else pd.Series("", index=df.index)

    log("① จับ Item_Type / Host / Platform จากชื่อสินค้า ...")
    t = _first_vec(name, TYPES, "Unknown")
    h = _first_vec(name, HOSTS, "")
    pl = _first_vec(name, PLATFORMS, "Generic")

    log("② ชื่อบอกไม่ได้ -> ไปดู CategoryName + SubCategoryName ...")
    m = t == "Unknown"
    if m.any():
        t[m] = _first_vec(ctx[m], TYPES, "Unknown")
    m = h == ""
    if m.any():
        h[m] = _first_vec(ctx[m], HOSTS, "")
    m = pl == "Generic"
    if m.any():
        pl[m] = _first_vec(ctx[m], PLATFORMS, "Generic")

    log("③ ยังไม่ได้ -> CATEGORY_MAP + เดาจากแบรนด์ ...")
    cm_t = cat_key.map(lambda k: (CATEGORY_MAP.get(k) or ["", ""])[0])
    cm_h = cat_key.map(lambda k: (CATEGORY_MAP.get(k) or ["", ""])[1]
                       if len(CATEGORY_MAP.get(k) or []) > 1 else "")
    use_cm = (t == "Unknown") & (cm_t != "")
    t[use_cm] = cm_t[use_cm]
    by_cat = use_cm.copy()
    fill_h = (h == "") & (cm_h != "")
    h[fill_h] = cm_h[fill_h]

    m = (t == "Unknown") & pl.isin(TYPE_FROM_PLATFORM)
    t[m] = pl[m].map(TYPE_FROM_PLATFORM)

    # CATEGORY_FORCE ทับผลจากชื่อ — APPLE SERVICE เป็นแคตตาล็อกอะไหล่ทั้งก้อน
    if CATEGORY_FORCE:
        cf = cat_key.map(lambda k: (CATEGORY_FORCE.get(k) or [""])[0])
        m = cf != ""
        t[m] = cf[m]
        by_cat |= m

    log("④ แก้ความกำกวม (DISAMBIGUATE) ...")
    both = name + " | " + ctx
    changed = pd.Series(False, index=df.index)
    for old, kw, new, ww, use_ctx in DISAMBIGUATE:
        tgt = both if use_ctx else name
        m = (~changed) & (t == old) & tgt.str.contains(_pattern(kw, ww), regex=True, na=False)
        t[m] = new
        changed |= m

    log("⑤ ตัวเครื่องเป็น host ของตัวเอง ...")
    m = t.isin(HOST_FROM_TYPE)
    h[m] = t[m].map(HOST_FROM_TYPE)
    m = (~m) & (h == "") & pl.isin(HOST_FROM_PLATFORM)
    h[m] = pl[m].map(HOST_FROM_PLATFORM)

    df["Item_Type"] = t.to_numpy(dtype=object)
    df["Item_Host"] = h.to_numpy(dtype=object)
    df["Item_Platform"] = pl.to_numpy(dtype=object)
    df["by_category"] = by_cat.to_numpy()
    return df


# ═══════════════════════════════════════ ประกอบเป็นคอลัมน์ผลลัพธ์ ══
# ⚠️ ตารางที่ใช้ประกอบย้ายไปอยู่ใน Cell 3 ของโน้ตบุ๊กแล้ว (main_of_type / acc_suffix
#    / acc_hosts / not_product) โค้ดตรงนี้แค่เอามาใช้ ไม่มีค่าฝังไว้

def compose(df, taxonomy="extended"):
    """เติมคอลัมน์ผลลัพธ์จาก Item_Type / Item_Host

    Main  อุปกรณ์เสริมที่รู้ host -> host เป็น Main   (เคสมือถือ -> Smart Phone)
          นอกนั้นใช้ main_of_type
    Sub   ต่อท้าย host หรือใช้ Item_Type -> คำนวณจาก Main เสมอ จึงไม่ขัดกันเอง
    """
    MAIN = COMPOSE.get("main_of_type", {})
    ACC = COMPOSE.get("acc_suffix", {})
    ACC_HOSTS = COMPOSE.get("acc_hosts", set())
    NOT_PRODUCT = COMPOSE.get("not_product", set())

    t = df["Item_Type"].to_numpy(dtype=object)
    h = df["Item_Host"].to_numpy(dtype=object)
    txt = (normalize(df["ItemName"]) + " | " + normalize(df["CategoryName"])
           + " | " + normalize(df["SubCategoryName"])).to_numpy(dtype=object)

    def has(pat):
        return pd.Series(txt).str.contains(pat, regex=True).to_numpy()

    promo = has(r"promo|โปรโมชั่น|ส่วนลด|รายการส่งเสริมการขาย") | (t == "Telecom")
    df["IS_Promotion"] = promo                      # 🆕 คอลัมน์ boolean แยกต่างหาก
    df["Sale_Type"] = np.where(promo, "Promotion Sale", "Normal Sale")
    df["Product_Dimension"] = np.where(
        has(r"demo|เครื่องโชว์|ตัวโชว์|display test"), "Demo Product", "Normal Product")
    df["Product_Purpose"] = np.where(
        has(r"gaming|rog|tuf|predator|nitro|legion|omen|เกมมิ่ง"),
        "Gaming", "Ordinary")

    # ทำทั้งคอลัมน์รวดเดียว ไม่วน for ทีละแถว
    ts = pd.Series(t, index=df.index)
    hs = pd.Series(h, index=df.index)
    pu = df["Product_Purpose"].astype(str)

    # 1) อุปกรณ์เสริมที่รู้ว่าใช้กับเครื่องอะไร -> host เป็น Main
    is_acc = ts.isin(ACC) & hs.isin(ACC_HOSTS)
    main = pd.Series(np.where(is_acc, hs, ts.map(MAIN).fillna("Others")), index=df.index)

    sub = main.copy()
    sub[is_acc] = hs[is_acc] + " " + ts[is_acc].map(ACC)
    rest = ~is_acc
    m1 = rest & main.isin(["PC", "Notebook"])
    sub[m1] = pu[m1] + "-" + main[m1]
    m2 = rest & main.isin(["Smart Phone", "Tablet", "Smart Watch", "HeadSet&Earpiece"])
    sub[m2] = main[m2] + " Main&Other"
    # เก็บรายละเอียดไว้ที่ Sub — IT Accessories จะได้ยังรู้ว่าเป็น RAM หรือ CPU
    m3 = rest & main.isin(["IT Accessories", "Mouse&Keyboard", "Others"]) & (ts != "Unknown")
    sub[m3] = ts[m3]

    df["Main_Product_Dimension"] = main.to_numpy(dtype=object)
    df["Sub_Product_Dimension"] = sub.to_numpy(dtype=object)
    # 🆕 ไม่ใช่สินค้าขายจริง — บริการ/อะไหล่/รายการที่แยกไม่ได้
    # เช็คทั้ง Main และ Item_Type — SparePart ถูกยุบเข้า IT Accessories แล้ว
    # ถ้าเช็คแต่ Main อะไหล่จะกลายเป็นสินค้าขายจริง
    df["IS_Product"] = ~(main.isin(NOT_PRODUCT) | ts.isin(NOT_PRODUCT)).to_numpy()
    return df


def run(df, taxonomy="extended"):
    """ทางลัด: normalize คอลัมน์ → จัดหมวด → ประกอบคอลัมน์ผลลัพธ์"""
    df = normalize_columns(df)
    df = add_columns(df)
    df = compose(df, taxonomy)
    return df


def health(df):
    """ตัวเลขสุขภาพของกฎ — ยิ่งกองที่แยกไม่ได้เล็ก ยิ่งดี"""
    n = len(df)
    return pd.DataFrame([
        {"ตัวชี้วัด": "Item_Type = Unknown", "แถว": int((df.Item_Type == "Unknown").sum()),
         "%": round((df.Item_Type == "Unknown").mean() * 100, 1), "เป้า": "< 10%"},
        {"ตัวชี้วัด": "Item_Host = ว่าง", "แถว": int((df.Item_Host == "").sum()),
         "%": round((df.Item_Host == "").mean() * 100, 1), "เป้า": "< 40%"},
        {"ตัวชี้วัด": "Main = Others (แยกไม่ได้)",
         "แถว": int((df.Main_Product_Dimension == "Others").sum()),
         "%": round((df.Main_Product_Dimension == "Others").mean() * 100, 1),
         "เป้า": "< 10%"},
        {"ตัวชี้วัด": "เชื่อ CategoryName เดิม (by_category)",
         "แถว": int(df.get("by_category", pd.Series(False, index=df.index)).sum()),
         "%": round(float(df.get("by_category", pd.Series(False, index=df.index)).mean()) * 100, 1),
         "เป้า": "ยิ่งน้อยยิ่งดี"},
        {"ตัวชี้วัด": "Item_Platform = Generic", "แถว": int((df.Item_Platform == "Generic").sum()),
         "%": round((df.Item_Platform == "Generic").mean() * 100, 1), "เป้า": "—"},
        {"ตัวชี้วัด": "รวมทั้งหมด", "แถว": n, "%": 100.0, "เป้า": "—"},
    ])
