"""
fact_sales_enriched — สร้างตารางยอดขายระดับรายการ + ข้อมูลสินค้า/สาขา โดยดึงตรงจาก ITEC-MIS

แปลงมาจาก Glue job บน AWS (เลิกใช้แล้ว 2026-11) ให้ตรรกะเหมือนเดิมทุกขั้น:
    etl-bronze-to-silver-itec-item   → build_dim_item()  (ส่วน silver)
    etl-silver-to-gold-dim-item      → build_dim_item()  (ส่วน gold: brand / department / category)
    etl-dms-dim-branch-to-gold       → build_dim_branch()
    etl-dms-fact-sales-to-gold       → build_fact_month()
ต้นฉบับ: D:\\AWS_Backup\\603238661233_2026-10-30\\ap-southeast-7\\glue\\jobs\\<ชื่อ job>\\

ต่างจากของเดิม:
    ต้นทาง   S3 bronze (DMS)          → ITEC-MIS ตรง (profile itec_mis): rpt.dim_item_itec · rpt.dim_branch_itec · rpt.fact_sales_itec
    ปลายทาง  Iceberg บน S3            → Parquet แบ่งโฟลเดอร์ sale_year=/sale_month= (รอโหลดเข้า MySQL บนเครื่อง SSOT)
    reconcile ตัวเลขจาก DMS           → นับ count(*) ที่ต้นทางของเดือนนั้นแล้วเทียบกับที่อ่านได้
    รันทีละเดือน เขียนทับเฉพาะเดือนที่รัน (เหมือน overwritePartitions)

วิธีใช้ (ต้องตั้ง env MIS_USER / MIS_PWD):
    python scripts/itec/fact_sales_enriched.py                      # ทุกเดือนตั้งแต่ 2023-01 ถึงเดือนปัจจุบัน
    python scripts/itec/fact_sales_enriched.py --months-back 2      # รันซ้ำ 2 เดือนล่าสุด (ใช้รอบประจำวัน)
    python scripts/itec/fact_sales_enriched.py --since 2026-01 --until 2026-03
    python scripts/itec/fact_sales_enriched.py --dims-only          # สร้างแค่ dim_item / dim_branch
ผลลัพธ์ (ค่าเริ่มต้น scripts/itec/_out/gold/ — ไม่เข้า git):
    dim_item.parquet · dim_branch.parquet · fact_sales_enriched/sale_year=YYYY/sale_month=M/part.parquet
"""
import argparse
import datetime as dt
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import db  # noqa: E402

PROFILE = "itec_mis"
SRC_ITEM = "rpt.dim_item_itec"
SRC_BRANCH = "rpt.dim_branch_itec"
SRC_FACT = "rpt.fact_sales_itec"
FIRST_MONTH = "2023-01"  # rpt.fact_sales_itec เริ่ม ม.ค. 2023
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), "_out", "gold")
OUTLIER_THB = 1_000_000  # รายการเดียวเกิน 1 ล้านบาท = แจ้งเตือนใน log (ไม่กรอง)


# =============================================================================
# helpers
# =============================================================================
def pick(conds, choices, default):
    """เหมือน when(...).when(...).otherwise(...) ของ Spark — เงื่อนไขแรกที่จริงชนะ, null นับเป็นเท็จ"""
    conds = [pd.Series(c).fillna(False).astype(bool).to_numpy() for c in conds]
    default = default.to_numpy(dtype=object) if isinstance(default, pd.Series) else default
    return np.select(conds, choices, default=default)


def isin(s, *vals):
    return s.isin(vals)


def rlike(s, pattern):
    """Spark rlike = ค้นหาบางส่วน (search) ไม่ใช่ fullmatch · null → False"""
    return s.str.contains(pattern, regex=True, na=False)


def round_half_up(x, nd=2):
    """Spark round() ปัดแบบ HALF_UP ส่วน numpy ปัดแบบ banker's — ทำให้เหมือน Spark"""
    f = 10 ** nd
    return np.sign(x) * np.floor(np.abs(x) * f + 0.5) / f


def clean_str(s, nulls=("NULL", "")):
    """trim + แปลงค่าใน nulls เป็น null · สินค้าใช้แค่ 'NULL' (เหมือน silver เดิม) · สาขาใช้ '' """
    s = s.astype("string").str.strip()
    return s.mask(s.isin(list(nulls)))


def log(msg):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


# =============================================================================
# dim_item  (silver itec_item + gold dim_item)
# =============================================================================
def build_dim_item():
    raw = db.query(PROFILE, f"SELECT ItemId, ItemName, CategoryName, SubCategoryName, [Model/Series], Brand FROM {SRC_ITEM}")
    log(f"[dim_item] source rows: {len(raw):,}")
    df = pd.DataFrame({
        "item_id": clean_str(raw["ItemId"], ("NULL",)),
        "item_name": clean_str(raw["ItemName"], ("NULL",)),
        "category_name": clean_str(raw["CategoryName"], ("NULL",)),
        "sub_category_name": clean_str(raw["SubCategoryName"], ("NULL",)),
        "model_series": clean_str(raw["Model/Series"], ("NULL",)),
        "brand": clean_str(raw["Brand"], ("NULL",)),
    })

    # ---- silver ----
    df["brand_clean"] = df["brand"].str.upper().str.strip().str.replace(r"\s+", " ", regex=True)
    df["base_item_id"] = df["item_id"].str.replace(r"(D7|-FA|-D|D)$", "", regex=True)
    iid = df["item_id"]
    df["is_valid_item_id"] = ~(rlike(iid, r'["\s]') | (iid.str.len() < 3).fillna(False) | rlike(iid, "[\u0E00-\u0E7F]"))  # \u0E2D\u0E31\u0E01\u0E29\u0E23\u0E44\u0E17\u0E22 (\u0E43\u0E2A\u0E48\u0E15\u0E31\u0E27\u0E2D\u0E31\u0E01\u0E29\u0E23\u0E08\u0E23\u0E34\u0E07 \u0E40\u0E1E\u0E23\u0E32\u0E30 pyarrow regex \u0E44\u0E21\u0E48\u0E23\u0E31\u0E1A \u)
    cat = df["category_name"]
    df["is_demo"] = (df["item_name"].str.startswith("D7@").fillna(False)
                     | cat.str.contains("Demo", regex=False).fillna(False) | (cat == "BTB Demo").fillna(False))
    df["is_service"] = isin(cat, "Service", "Smile") | (df["brand_clean"] == "SERVICE").fillna(False)
    df["is_promo"] = isin(cat, "Promo Operator", "Reserve")
    df["product_status"] = pick([df.is_demo, df.is_service, df.is_promo], ["DEMO", "SERVICE", "PROMO"], "ACTIVE")
    df["category_clean"] = cat.str.upper().str.strip()
    df["sub_category_clean"] = df["sub_category_name"].str.upper().str.strip()
    df["item_name_clean"] = df["item_name"].str.replace(r"^D7@ ?", "", regex=True)

    # silver dedup: ACTIVE > DEMO > SERVICE > PROMO แล้วข้อมูลครบกว่า
    df["_prio"] = df["product_status"].map({"ACTIVE": 1, "DEMO": 2, "SERVICE": 3, "PROMO": 4}).fillna(5)
    df["_score"] = df[["brand", "model_series", "category_name", "sub_category_name"]].notna().sum(axis=1)
    n0 = len(df)
    df = df.sort_values(["_prio", "_score"], ascending=[True, False], kind="stable").drop_duplicates("item_id")
    log(f"[dim_item] silver dedup: {n0:,} → {len(df):,}")

    # ---- gold: brand ----
    b = df["brand_clean"]
    df["brand_std"] = pick([
        isin(b, "APPLE", "APPLE SERVICE"), rlike(b, r"^TRUE.IPHONE|^TRUE.IPAD"),
        b == "SAMSUNG", b == "TRUE-SAMSUNG", b == "TRUE_SAMSUNG",
        isin(b, "XIAOMI", "TRUE-XIAOMI", "TRUE_XIAOMI"), isin(b, "OPPO", "TRUE-OPPO", "TRUE_OPPO"),
        isin(b, "VIVO", "TRUE-VIVO", "TRUE_VIVO"), isin(b, "REALME", "TRUE-REALME", "TRUE_REALME"),
        isin(b, "HUAWEI", "TRUE-HUAWEI", "TRUE_HUAWEI"), isin(b, "HONOR", "TRUE-HONOR"), isin(b, "HP", "HYPER X"),
        b == "ASUS", b == "ACER", b == "LENOVO", b == "DELL", b == "MSI", b == "GIGABYTE", b == "SONY", b == "LG",
        b == "MICROSOFT", b == "INTEL", b == "LOGITECH", b == "JBL", b == "CORSAIR", b == "KINGSTON", b == "WESTERN",
        b == "TOSHIBA", b == "PHILIPS", b == "BELKIN", b == "FOX", b == "ANITECH", b == "ELECOM",
        isin(b, "NEOLUTION", "NUBWO"), b == "KING KONG", b == "CASE CLUB", b == "TECHPRO",
        isin(b, "TRUEMOVE", "TRUE", "TRUEMOVEH"), b == "AIS", b == "DTAC", b == "COM7",
        isin(b, "NULL", "-", "XX", "OTHER") | b.isna(),
    ], [
        "Apple", "Apple", "Samsung", "Samsung", "Samsung", "Xiaomi", "Oppo", "Vivo", "Realme", "Huawei", "Honor", "HP",
        "Asus", "Acer", "Lenovo", "Dell", "MSI", "Gigabyte", "Sony", "LG", "Microsoft", "Intel", "Logitech", "JBL",
        "Corsair", "Kingston", "Western Digital", "Toshiba", "Philips", "Belkin", "Fox", "Anitech", "Elecom",
        "Neolution", "King Kong", "Case Club", "TechPro", "TrueMove", "AIS", "DTAC", "COM7", "Unknown",
    ], b)
    s = df["brand_std"]
    df["brand_group"] = pick([
        s == "Apple", s == "Samsung", s == "HP", s == "Lenovo", s == "Dell", s == "Asus", s == "Acer",
        isin(s, "Sony", "JBL"), s == "Xiaomi", isin(s, "Oppo", "Realme", "Vivo"), isin(s, "TrueMove", "AIS", "DTAC"),
    ], ["Apple", "Samsung", "HP", "Lenovo", "Dell", "Asus", "Acer", "Sony", "Xiaomi", "BBK Electronics", "Telco"], "Other")

    # ---- gold: department (L1) / category (L2) ----
    c = df["category_clean"]
    df["department"] = pick([
        isin(c, "NOTEBOOK", "PREMIUM NOTEBOOK", "DESKTOP", "MAC"),
        isin(c, "GRAPHIC CARD", "MAINBOARD", "CPU", "RAM FOR PC", "COMPUTER CASES", "COOLING SYSTEM", "POWER SUPPLY",
             "INTERNAL HARDDRIVE", "SOLID STATE DRIVE INTERNAL (SSD)", "OPTICAL DRIVE", "FLASH DRIVE AND MEMORY CARD"),
        isin(c, "SMARTPHONE", "PREMIUM SMARTPHONE", "IPHONE"),
        isin(c, "IPAD", "TABLET SMARTPHONE"),
        isin(c, "HEADPHONE", "SPEAKER", "AUDIO & VISUAL"),
        isin(c, "GAMING GEAR", "CONSOLE AND GAMING GADGET"),
        isin(c, "MONITOR", "PRINTER", "NETWORK", "SOFTWARE"),
        isin(c, "CASES", "BEBEPHONE", "SMARTPHONE ACC", "FILM FOR MOBILE AND TABLET", "MOBILE CABLE", "BAG", "CASE CLUB",
             "APPLE CASE & PROTECTION", "APPLE ACC FOR WATCH", "APPLE"),
        isin(c, "MOUSE & KEYBOARDS", "KEYBOARD", "IT ACCESSORIES", "ADAPTER", "POWER BANK", "EXTERNAL HARDDRIVE"),
        isin(c, "CAMERA", "SMARTWATCH", "APPLE WATCH", "GADGET", "SMART LIVING", "XIAOMI ECO", "SMALL APPLIANCE",
             "HOME APPLIANCE", "HEALTH & SPORT", "OUTDOOR ACTIVITIES"),
    ], ["Computing", "PC Components", "Mobile", "Tablet", "Audio", "Gaming", "Peripherals", "Accessories",
        "IT Accessories", "Lifestyle & IoT"], "Other")
    df["category"] = pick([
        isin(c, "NOTEBOOK", "PREMIUM NOTEBOOK"), c == "DESKTOP", c == "MAC", isin(c, "SMARTPHONE", "PREMIUM SMARTPHONE"),
        c == "IPHONE", c == "IPAD", c == "TABLET SMARTPHONE", c == "HEADPHONE", c == "SPEAKER", c == "AUDIO & VISUAL",
        c == "GAMING GEAR", c == "CONSOLE AND GAMING GADGET", c == "MONITOR", c == "PRINTER", c == "NETWORK",
        c == "CAMERA", isin(c, "SMARTWATCH", "APPLE WATCH"),
        isin(c, "CASES", "BEBEPHONE", "CASE CLUB", "APPLE CASE & PROTECTION"),
        isin(c, "SMARTPHONE ACC", "FILM FOR MOBILE AND TABLET", "MOBILE CABLE"),
        isin(c, "MOUSE & KEYBOARDS", "KEYBOARD"),
        isin(c, "GRAPHIC CARD", "MAINBOARD", "CPU", "RAM FOR PC"),
        isin(c, "COMPUTER CASES", "COOLING SYSTEM", "POWER SUPPLY"),
        isin(c, "INTERNAL HARDDRIVE", "EXTERNAL HARDDRIVE", "SOLID STATE DRIVE INTERNAL (SSD)", "FLASH DRIVE AND MEMORY CARD"),
        isin(c, "POWER BANK", "ADAPTER"), isin(c, "XIAOMI ECO", "SMART LIVING", "GADGET"),
        isin(c, "SMALL APPLIANCE", "HOME APPLIANCE"), c == "BAG", c == "SOFTWARE",
    ], ["Notebook", "Desktop", "Mac", "Smartphone", "iPhone", "iPad", "Tablet", "Headphone", "Speaker", "Audio & Visual",
        "Gaming Gear", "Console & Gaming", "Monitor", "Printer", "Network", "Camera", "Smartwatch", "Phone Case",
        "Phone Accessories", "Mouse & Keyboard", "PC Core Components", "PC Case & Cooling", "Storage",
        "Power & Charging", "Smart Living", "Home Appliance", "Bag", "Software"], c)

    out = pd.DataFrame({
        "item_id": df["item_id"], "base_item_id": df["base_item_id"], "item_name": df["item_name_clean"],
        "department": df["department"], "category": df["category"], "sub_category": df["sub_category_clean"],
        "model_series": df["model_series"], "brand": df["brand_std"], "brand_group": df["brand_group"],
        "product_status": df["product_status"], "is_valid_item_id": df["is_valid_item_id"].astype(bool),
    })
    for col in out.columns.drop("is_valid_item_id"):
        out[col] = out[col].astype("string")

    # gold dedup (กันไว้ — silver unique อยู่แล้ว): ACTIVE ก่อน, id ถูกต้องก่อน, ข้อมูลครบกว่า, ชื่อ
    out["_a"] = (out["product_status"] != "ACTIVE").astype(int)
    out["_v"] = (~out["is_valid_item_id"]).astype(int)
    out["_s"] = (((out["brand"].notna()) & (out["brand"] != "Unknown")).astype(int)
                 + ((out["department"].notna()) & (out["department"] != "Other")).astype(int)
                 + out["model_series"].notna().astype(int) + out["sub_category"].notna().astype(int))
    out = (out.sort_values(["_a", "_v", "_s", "item_name"], ascending=[True, True, False, True], na_position="last", kind="stable")
              .drop_duplicates("item_id").drop(columns=["_a", "_v", "_s"]).reset_index(drop=True))
    if out["item_id"].duplicated().any():
        raise ValueError("dim_item still has duplicate item_id")
    log(f"[dim_item] rows: {len(out):,} · status: {out.product_status.value_counts().to_dict()}")
    return out


# =============================================================================
# dim_branch
# =============================================================================
def build_dim_branch():
    raw = db.query(PROFILE, f"SELECT Branch, BranchName, Region, Province, BranchType FROM {SRC_BRANCH}")
    log(f"[dim_branch] source rows: {len(raw):,}")
    df = pd.DataFrame({
        "branch_id": pd.to_numeric(raw["Branch"], errors="coerce").astype("Int64"),
        "branch_name": clean_str(raw["BranchName"], ("",)),
        "region": clean_str(raw["Region"], ("",)),
        "province": clean_str(raw["Province"], ("",)),
        "channel": clean_str(raw["BranchType"], ("",)),  # BranchType = รูปแบบร้าน / แบรนด์ร้าน
    })
    df["province"] = df["province"].mask(df["province"].isin(["กรุงเทพฯ", "กรุงเทพ", "กรุงเทพมหานคร"]), "Bangkok")
    df["_s"] = df[["branch_name", "region", "province", "channel"]].notna().sum(axis=1)
    n0 = len(df)
    df = (df.sort_values(["_s", "branch_name"], ascending=[False, True], na_position="last", kind="stable")
            .drop_duplicates("branch_id").drop(columns="_s").sort_values("branch_id").reset_index(drop=True))
    log(f"[dim_branch] dedup: {n0:,} → {len(df):,}")
    if df["branch_name"].notna().sum() == 0:
        raise ValueError("every branch_name is NULL — check the source columns")
    return df


# =============================================================================
# fact_sales_enriched (1 เดือน)
# =============================================================================
FACT_COLS = ["sales_id", "sales_datetime", "sale_date", "end_month_date", "sale_year", "sale_month",
             "branch_id", "branch_name", "region", "province", "channel",
             "product_id", "serial_no", "item_name", "brand", "brand_group", "department", "category", "sub_category",
             "sales_officer_id", "sales_qty", "cost_amt", "sale_amt", "gp_amt", "gp_pct", "margin_amt", "margin_pct",
             "status", "is_return", "is_zero_revenue", "is_negative_margin"]


def build_fact_month(cn, start, end, dim_item, dim_branch):
    cur = cn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {SRC_FACT} WHERE SalesCrDatetime >= ? AND SalesCrDatetime < ?", start, end)
    expected = cur.fetchone()[0]
    raw = pd.read_sql(
        f"""SELECT SalesId, SalesBranch, ItemId, SerialNo, SalesQty, SalesAmount, CostAmount, GPAmount, [GP %] AS GPPct,
                   Status, SalesCrDatetime, SalesOfficerId
            FROM {SRC_FACT} WHERE SalesCrDatetime >= ? AND SalesCrDatetime < ?""",
        cn, params=[start, end])
    if len(raw) != expected:  # แทน reconcile ของ DMS: อ่านไม่ครบ = ไม่เขียนทับ
        raise ValueError(f"row count mismatch {start:%Y-%m}: source {expected:,}, read {len(raw):,}")
    if raw.empty:
        return raw

    df = pd.DataFrame({
        "sales_id": raw["SalesId"].astype("Int64"),
        "branch_id": raw["SalesBranch"].astype("Int64"),
        "product_id": raw["ItemId"].astype("string").str.strip(),
        "serial_no": raw["SerialNo"].astype("string"),
        "sales_qty": raw["SalesQty"].astype("Int64"),
        "sale_amt": raw["SalesAmount"].astype(float),
        "cost_amt": raw["CostAmount"].astype(float),
        "gp_amt": raw["GPAmount"].astype(float),
        "gp_pct": raw["GPPct"].astype(float),
        "status": raw["Status"].astype("Int64"),
        "sales_datetime": pd.to_datetime(raw["SalesCrDatetime"]),
        "sales_officer_id": raw["SalesOfficerId"].astype("Int64"),
    })
    d = df["sales_datetime"]
    df["sale_date"] = d.dt.normalize()
    df["sale_year"] = d.dt.year.astype("Int64")
    df["sale_month"] = d.dt.month.astype("Int64")
    df["end_month_date"] = (d.dt.normalize() + pd.offsets.MonthEnd(0))

    sale, cost, qty = df["sale_amt"], df["cost_amt"], df["sales_qty"].astype(float)
    df["margin_amt"] = round_half_up(sale - cost, 2)
    # margin_pct: ยอดขาย 0 และทุน 0 = 0% จริง · ยอดขาย 0 แต่มีทุน = ไม่มีตัวหาร → null · ทุน null → null
    pct = round_half_up((sale - cost) / sale.where(sale != 0) * 100, 2)
    df["margin_pct"] = np.where(sale != 0, pct, np.where((sale == 0) & (cost == 0), 0.0, np.nan))
    df["is_return"] = ((qty < 0) | (sale < 0)).fillna(False)
    df["is_zero_revenue"] = ((sale == 0) & (qty > 0)).fillna(False)
    df["is_negative_margin"] = ((df["margin_amt"] < 0) & ~df["is_return"] & (sale > 0)).fillna(False)

    item_cols = ["item_id", "item_name", "brand", "brand_group", "department", "category", "sub_category"]
    df = df.merge(dim_item[item_cols], how="left", left_on="product_id", right_on="item_id").drop(columns="item_id")
    df = df.merge(dim_branch, how="left", on="branch_id")
    if len(df) != expected:  # dim ซ้ำจะทำให้ยอดเบิ้ล
        raise ValueError(f"join fan-out {start:%Y-%m}: {expected:,} → {len(df):,}")
    return df[FACT_COLS]


def write_month(df, out_dir, y, m):
    part = os.path.join(out_dir, "fact_sales_enriched", f"sale_year={y}", f"sale_month={m}")
    os.makedirs(part, exist_ok=True)
    tmp = os.path.join(part, "part.parquet.tmp")
    df.to_parquet(tmp, index=False, compression="snappy")
    os.replace(tmp, os.path.join(part, "part.parquet"))  # เขียนทับเฉพาะเดือนนี้ และไม่ทิ้งไฟล์ครึ่งๆ


# =============================================================================
# main
# =============================================================================
def month_range(since, until):
    cur = pd.Period(since, "M")
    last = pd.Period(until, "M")
    while cur <= last:
        yield cur
        cur += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", help="เดือนแรก YYYY-MM (ค่าเริ่มต้น 2023-01)")
    ap.add_argument("--until", help="เดือนสุดท้าย YYYY-MM (ค่าเริ่มต้น เดือนปัจจุบัน)")
    ap.add_argument("--months-back", type=int, help="รันซ้ำ N เดือนล่าสุด (แทน --since)")
    ap.add_argument("--out", default=os.environ.get("SSOT_GOLD_DIR", DEFAULT_OUT), help="โฟลเดอร์ผลลัพธ์")
    ap.add_argument("--dims-only", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    until = a.until or dt.date.today().strftime("%Y-%m")
    since = a.since or ((pd.Period(until, "M") - (a.months_back - 1)).strftime("%Y-%m") if a.months_back else FIRST_MONTH)
    log(f"source ITEC-MIS ({PROFILE}) → {a.out}")

    dim_item = build_dim_item()
    dim_branch = build_dim_branch()
    dim_item.to_parquet(os.path.join(a.out, "dim_item.parquet"), index=False)
    dim_branch.to_parquet(os.path.join(a.out, "dim_branch.parquet"), index=False)
    if a.dims_only:
        return

    cn = db.connect(PROFILE, timeout=1800)
    total = no_item = no_branch = 0
    for p in month_range(since, until):
        t0 = time.time()
        start = p.start_time.to_pydatetime()
        end = (p + 1).start_time.to_pydatetime()
        df = build_fact_month(cn, start, end, dim_item, dim_branch)
        if df.empty:
            log(f"[fact] {p} — no rows")
            continue
        write_month(df, a.out, p.year, p.month)
        ni, nb = int(df["brand"].isna().sum()), int(df["branch_name"].isna().sum())
        total += len(df); no_item += ni; no_branch += nb
        log(f"[fact] {p} rows {len(df):,} · sale {df.sale_amt.sum():,.0f} · no item {ni:,} · no branch {nb:,} · {time.time() - t0:.0f}s")
        # ต้นทางมีรายการราคาผิดปกติ (เช่น SOCIALCARE001 ต.ค. 2026 = 830,510 ล้านบาท 1 แถว) — ไม่กรองทิ้ง
        # เพื่อให้ตรงกับ pipeline เดิม แต่แจ้งไว้ให้ระวังเวลารวมยอด
        odd = df[df["sale_amt"].abs() > OUTLIER_THB]
        if len(odd):
            log(f"   ⚠ {len(odd)} rows with |sale_amt| > {OUTLIER_THB:,.0f} THB · sum {odd.sale_amt.sum():,.0f} · "
                f"top: {', '.join(odd.nlargest(3, 'sale_amt').product_id.astype(str))}")
    cn.close()
    if total:
        log(f"[DONE] {total:,} rows · no dim_item match {no_item / total:.1%} · no dim_branch match {no_branch / total:.1%}")


if __name__ == "__main__":
    main()
