# -*- coding: utf-8 -*-
"""สร้างไฟล์ส่งมอบ 5 ชุด สำหรับที่ปรึกษาคลังสินค้า

    python scripts/fo/wh_report.py

ผลลัพธ์ -> scripts/fo/_out/Warehouse_Data_2025-2026.xlsx  (6 ชีต)
เอกสารประกอบ -> COM7-Knowledge-Base/06_Project/Warehouse Consultant Data Request.md
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import wh_common as W
import wh_movement as M
import wh_others as O

CAT = ["ITEC_Category", "ITEC_SubCategory",
       "FO_GroupCategory", "FO_CategoryName", "FO_SubCategoryName"]


# อักขระควบคุมที่ openpyxl ปฏิเสธ — เจอจริงในชื่อสินค้า เช่น "**** Lomography Fisheye2"
BAD = dict.fromkeys(list(range(0, 9)) + [11, 12] + list(range(14, 32)), None)


def clean(d):
    """ล้างอักขระควบคุมออกจากทุกคอลัมน์ข้อความ ไม่งั้น Excel เขียนไม่ผ่าน

    ⚠️ pandas 3 ใช้ dtype ชื่อ "str" ไม่ใช่ "object" — เช็ก == object จะข้ามทุกคอลัมน์
    """
    d = d.copy()
    for c in d.columns:
        if pd.api.types.is_numeric_dtype(d[c]) or pd.api.types.is_datetime64_any_dtype(d[c]):
            continue
        d[c] = d[c].map(lambda v: v.translate(BAD) if isinstance(v, str) else v)
    return d


def roll(d, by, val):
    """ยุบถึงระดับหมวด — ระดับสินค้ารายตัวมีเป็นล้านแถว Excel ไม่รับ"""
    g = d.groupby(by, dropna=False).agg(**val).reset_index()
    return g.sort_values(by)


def main():
    t0 = time.time()
    W.OUT.mkdir(exist_ok=True)
    sheets = {}

    for kind, label in (("inbound", "1_Daily_Inbound"), ("outbound", "2_Daily_Outbound")):
        print(f"\n■ {label}", flush=True)
        d = M.build(kind)
        doc = "PO_Count" if kind == "inbound" else "SO_Count"
        g = roll(d, ["Date", "BU", "BU_Name", "Warehouse", "Warehouse_Name",
                     "Source", "MovementType"] + CAT,
                 {"Qty": ("Qty", "sum"), doc: ("DocCount", "sum"),
                  "Lines": ("Lines", "sum"), "SKU": ("ItemId_FO", "nunique")})
        print(f"   {len(g):,} แถว · Qty รวม {g.Qty.sum():,.0f}", flush=True)
        sheets[label] = g

    print("\n■ 3_Monthly_Stock", flush=True)
    s = O.stock()
    g = roll(s, ["YearMonth", "BU", "BU_Name", "Warehouse", "Warehouse_Name",
                 "Source"] + CAT,
             {"Qty": ("Qty", "sum"), "SKU": ("ItemId_FO", "nunique")})
    g = g[g.Qty != 0]
    print(f"   {len(g):,} แถว", flush=True)
    sheets["3_Monthly_Stock"] = g

    print("\n■ 4_Supplier", flush=True)
    v = O.vendor()
    sheets["4_Supplier"] = v[["BU", "BU_Name", "Warehouse", "Warehouse_Name",
                              "VendorCode", "VendorName", "VendorDefaultSite",
                              "PO_Count", "SKU", "Lines", "Qty", "Cost",
                              "FirstDate", "LastDate"]]
    print(f"   {len(v):,} แถว · {v.VendorCode.nunique()} ราย", flush=True)

    print("\n■ 5_Product_Master", flush=True)
    p = O.product()
    keep = ["ItemId_FO", "ItemId_ITEC", "BU", "BU_Name", "ItemName_FO",
            "ItemName_ITEC", "Brand_ITEC"] + CAT + [
            "Width", "Height", "Depth", "GrossWidth", "GrossHeight", "GrossDepth",
            "NetWeight", "TaraWeight", "UnitVolume"]
    p = p[[c for c in keep if c in p.columns]]
    # 🔴 ขนาด/น้ำหนักใน D365FO ว่างเปล่าทั้งระบบ (ตรวจ 360,823 แถว เจอไม่เป็นศูนย์ 2 แถว)
    #    คงคอลัมน์ไว้เพื่อให้เห็นว่าฟิลด์มีอยู่จริง แต่ยังไม่มีใครกรอก
    got = (p[["Width", "Height", "Depth", "NetWeight"]].fillna(0) != 0).any(axis=1)
    print(f"   {len(p):,} แถว · มีขนาด/น้ำหนักจริง {got.sum():,} "
          f"({got.mean()*100:.1f}%)  <- ฟิลด์ว่างทั้งระบบ", flush=True)
    sheets["5_Product_Master"] = p

    # ── ชีตอธิบาย ────────────────────────────────────────────────────
    notes = pd.DataFrame({
        "หัวข้อ": [
            "ช่วงเวลา", "บริษัทและคลัง", "", "", "", "", "",
            "🔴 Adept ม.ค.-มิ.ย. 2025", "", "",
            "แหล่งข้อมูล com7 ปี 2025", "แหล่งข้อมูล com7 ปี 2026",
            "แหล่งข้อมูล Double7 / Adept", "หมวดสินค้า", "",
            "🔴 MovementType", "", "Qty ขาเข้า", "Qty ขาออก", "สต็อกสิ้นเดือน", "",
            "ผู้ขาย — ต้นทาง", "ขนาด/น้ำหนัก", "ข้อควรระวัง", "", "จัดทำ"],
        "รายละเอียด": [
            "2025-01-01 ถึง 2026-08-31",
            "COM7  คลัง 4  = ID4 : คลังสินค้า (สำนักงานใหญ่)",
            "COM7  คลัง 77 = ID77 : E-Commerce Warehouse",
            "Double7 คลัง 79006 = WHOLESALE ADEPT YA (คลังหลักตามที่ระบุ)",
            "Double7 คลัง 79001 = Warehouse (กลาง) — ใหญ่กว่า 79006 ราว 83 เท่า ใส่ไว้ให้พิจารณา",
            "Adept คลัง 72008 = ADEPT YAS  (เปิดใช้ ก.ค. 2025)",
            "Adept คลัง 72006 = ADEPTWH-ONLINE  (เปิดใช้ มี.ค. 2026)",
            "ไม่มีข้อมูลโดยตั้งใจ — ช่วงนั้น Adept ใช้คลังชื่อ Realme ซึ่งปิดไปแล้ว (เคลื่อนไหวล่าสุด 2026-05-18)",
            "ผู้ขอยืนยันให้ตัดคลัง Realme ออก เพราะเป็นคลังในอดีต ไม่มีอยู่แล้ว",
            "ผลคือ Adept เริ่มมีข้อมูลตั้งแต่ ก.ค. 2025 — กราฟจะขาดครึ่งปีแรก ไม่ใช่ข้อมูลหาย",
            "ITEC — Transaction_ITEC_tracking (รับเข้า มี PO) · Transaction_ITEC (จ่ายออก)",
            "D365 F&O — PROJECT_1.dbo.Transaction_FO",
            "D365 F&O — PROJECT_1.dbo.Transaction_FO ทั้ง 2 ปี",
            "ใส่ให้ 2 ชุด ITEC_* และ FO_* ทุกแถว ไม่ว่าข้อมูลมาจากระบบไหน",
            "แปลงรหัสข้ามระบบด้วย ITEC-ITEMNO <-> FO-ITEMNO จาก Transaction_FO (ผูกกัน 1:1)",
            "คลังกลางไม่ได้ขายให้ลูกค้า แต่โอนไปสาขา — ITEC สาขา 4 มี Transfer-Out 8.4 ล้านแถว แต่ Sales 0 แถว",
            "จึงแยกเป็น PO ซื้อเข้า / SO ขาย / Transfer โอน — ถ้านับแค่ PO+SO ของที่ผ่านคลังจะหายไปเกือบ 90%",
            "PO ซื้อเข้า = ซื้อจากผู้ขาย · Transfer โอน = รับโอนจากคลัง/สาขาอื่น",
            "SO ขาย = ขายให้ลูกค้าโดยตรง · Transfer โอน = โอนออกไปสาขา",
            "com7 ปี 2025 = rpt.onhandendmonth_itec (ตัวเลขที่ระบบบันทึกไว้จริง)",
            "ที่เหลือ = ไล่สะสม QTY ตั้งแต่แถวแรกของฐาน ตัดรายการปิดบัญชีถัวเฉลี่ยออก",
            "ฐานข้อมูลนี้ไม่มีที่อยู่/ประเทศของผู้ขาย (ว่างทุกแถว) จึงให้คลังปลายทางแทน",
            "🔴 ไม่มีข้อมูลในระบบใดเลย — ITEC ไม่มีคอลัมน์ · D365FO มีคอลัมน์แต่ว่างเปล่า 360,821 จาก 360,823 แถว",
            "หมวดฝั่ง FO ไม่ใช่ลำดับชั้นจริง — 345 จาก 487 หมวดชี้ไปหลายกลุ่ม",
            "com7 จัดสินค้า demo ทุกชนิดไว้ใต้กลุ่ม iPhone",
            f"ทีมข้อมูล · {time.strftime('%Y-%m-%d')}"]})
    sheets["0_อ่านก่อน"] = notes

    p = W.OUT / "Warehouse_Data_2025-2026.xlsx"
    with pd.ExcelWriter(p, engine="openpyxl") as xw:
        for name in ["0_อ่านก่อน", "1_Daily_Inbound", "2_Daily_Outbound",
                     "3_Monthly_Stock", "4_Supplier", "5_Product_Master"]:
            clean(sheets[name]).to_excel(xw, sheet_name=name, index=False)
    print(f"\nเขียน {p}  ({p.stat().st_size/1024/1024:.1f} MB · {time.time()-t0:.0f} วิ)")


if __name__ == "__main__":
    main()
