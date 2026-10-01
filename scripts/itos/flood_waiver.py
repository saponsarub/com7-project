# -*- coding: utf-8 -*-
"""ITOS — ลูกหนี้ที่อยู่ในเขตน้ำท่วม (สำหรับ waive เบี้ยปรับ)

    python scripts/itos/flood_waiver.py

═══════════════════════════════════════════════════════════════════════
 แหล่งข้อมูล
═══════════════════════════════════════════════════════════════════════
ทุกตารางอยู่ในฐาน ILOAN_DATASOURCE ที่เข้าถึงผ่าน linked server ของ k2
(43.254.133.123) · linked server ตัวนี้ข้ามฐานไม่ได้ ใช้ได้แค่ฐานนี้ฐานเดียว

    ITOS_COLLECTION_DETAIL      ยอดหนี้ · เบี้ยปรับ · ชื่อ-เบอร์ลูกค้า
    ITOS_COLLECTION_PORTFOLIO   เพศ · อายุ · อาชีพ · รายได้ · credit score
    COLLECTION_S_ADDRESS        ⭐ ที่อยู่แบบ "รหัส" 4 ประเภทต่อสัญญา
    HP_COMMON_PROVINCE          77 จังหวัด   (รหัส 2 หลัก)
    HP_COMMON_DISTRICT          928 อำเภอ    (รหัส 4 หลัก)
    HP_COMMON_SUBDISTRICT       7,437 ตำบล   (รหัส 6 หลัก)

    'C:\\Users\\Sapon.S\\Downloads\\penalty wave.xlsx' tab 'เขตน้ำท่วม'
    พื้นที่อุทกภัย 29 จังหวัด / 203 อำเภอ-เขต

═══════════════════════════════════════════════════════════════════════
 กับดักที่เจอ — อ่านก่อนแก้โค้ด
═══════════════════════════════════════════════════════════════════════
1. ⚠️ **ชื่อคอลัมน์ใน COLLECTION_S_ADDRESS หลอก**
       ADDR_PROVINCE  = รหัสจังหวัด 2 หลัก   ✔ ตรงชื่อ
       ADDR_AMPHUR    = รหัส**อำเภอ** 4 หลัก  ✔ ตรงชื่อ
       ADDR_DISTRICT  = รหัส**ตำบล** 6 หลัก   ✘ ชื่อบอกอำเภอ แต่เก็บตำบล
   และเก็บเป็น "รหัส" ไม่ใช่ชื่อ — join ด้วย NAME_THA จะได้ NULL ทั้ง 658,768 แถว

2. ⚠️ **ADDR_TYPE** ไม่มีตาราง master ถอดรหัสให้ · ถอดจากการเทียบข้อมูลจริง
       AD01 = ที่อยู่ปัจจุบัน   AD02 = ตามทะเบียนบ้าน
       AD03 = ที่ทำงาน         AD04 = ที่อยู่จัดส่ง
   (ยืนยันโดยเทียบกับ CUSTOMER_ADDRESS_CURRENT / _REGISTER ของสัญญาเดียวกัน)

3. ⚠️ **ที่อยู่ข้อความใน ITOS_COLLECTION_DETAIL ว่าง 50,352 จาก 329,078 แถว**
   (15.3%) เพราะ ITOS_STAGE_ADDRESS ที่เป็นต้นทางมีแค่ 278,726 สัญญา
   COLLECTION_S_ADDRESS ครอบคลุม **ทั้ง 329,078** จึงใช้ตัวนี้เป็นหลัก
   แล้วเอาการแกะข้อความมาเป็นตัวสอบทานแทน

4. ⚠️ **(สัญญา, ADDR_TYPE) ซ้ำได้** 836 คู่มี 2 แถว — ต้องเลือกแถวเดียว
   ใช้ ADDR_ID มากสุด (ล่าสุด)

5. ⚠️ **ห้ามใส่ WITH (NOLOCK)** — ตารางผ่าน linked server เป็น external table
   จะได้ error 46915 *"Table hints are not supported on queries that
   reference external tables"*

6. ⚠️ **กรองวันด้วย CREATE_DATE ไม่ใช่ EXTRACT_DATE**

   ตารางนี้ถูก **โหลดทับใหม่ทั้งตารางทุกวัน** (full snapshot replace)
       CREATE_DATE  = วันที่โหลด snapshot   → ทั้ง 329,078 แถวเป็นวันเดียวกัน
       EXTRACT_DATE = cohort วันที่เปิดสัญญา → กระจาย 2026-01-27 ถึงวันล่าสุด

   หลักฐานว่า EXTRACT_DATE เป็น cohort ไม่ใช่วันดึงข้อมูล
       · 1 CONTRACT_ID โผล่แค่ 1 EXTRACT_DATE เสมอ
       · PAID_NUMBER_OF_PERIOD เฉลี่ยไล่จาก 10.0 งวด (ม.ค.) ลงมา 0.09 (ก.ย.)
       · สถานะ OD6 มีแต่ในเดือน ม.ค.–ส.ค. เดือน ก.ย. ไม่มีเลย
   → กรอง EXTRACT_DATE = วันล่าสุด จะได้แค่สัญญาที่เพิ่งเปิดวันนั้น
     ซึ่งยังไม่ถึงงวดแรก **เบี้ยปรับ 0 บาททั้งหมด** — ไม่มีอะไรให้ waive

   ⚠️ ตัวเลขเปลี่ยนทุกวันเพราะโหลดทับ · ถ้าดึงตอนเช้าอาจยังเป็น snapshot
      ของเมื่อวาน (เคยเจอ: ดึง 12:52 ได้ CREATE_DATE = 09-28/29 · ดึง 17:10
      ได้ 09-30) → เช็ค CREATE_DATE ที่ได้จริงก่อนใช้ตัวเลขทุกครั้ง

═══════════════════════════════════════════════════════════════════════
 ข้อผิดพลาดในไฟล์ K2 เดิม (penalty wave.xlsx) ที่ไม่ทำซ้ำ
═══════════════════════════════════════════════════════════════════════
A. จับคู่อำเภอโดย**ไม่ดูจังหวัด** → 'เฉลิมพระเกียรติ' ของนครราชสีมา ·
   สระบุรี · นครศรีธรรมราช ติด Y ตามของบุรีรัมย์ที่ท่วมจริง (21 แถว)
   'จอมทอง' ของเชียงใหม่ ติด Y ตามเขตจอมทอง กทม.
   → ที่นี่จับคู่เป็น "รหัสอำเภอ" ซึ่งไม่ซ้ำกันทั้งประเทศ
B. ฝั่ง current **ไม่ได้คำนวณใหม่ ลอกคำตอบฝั่ง register มา** —
   1,766 แถวที่ที่อยู่สองฝั่งต่างกัน ได้ผล Map เหมือนกันหมดทุกช่อง
   (Map_district ผิด 743 แถว · Map_province ผิด 625 แถว)
   → ที่นี่คำนวณสองฝั่งแยกกันจริง
C. tab 'เขตน้ำท่วม' หัวช่องเขียน 'กรุงเทพมหานคร 50 เขต' แต่ลิสต์มา 48 เขต
   ขาด **เขตบางกอกน้อย** และ **เขตบางกอกใหญ่**
   → ยึดตามรายชื่อที่ลิสต์จริง (48) และรายงานตัวเลขของ 2 เขตที่ขาดไว้ให้ตัดสินใจ

═══════════════════════════════════════════════════════════════════════
 เงื่อนไขและรูปแบบผลลัพธ์ — ตาม wave_flood.ipynb
═══════════════════════════════════════════════════════════════════════
    CAST(CREATE_DATE AS date) = '<AS_OF>'      snapshot ของวันนั้น
    NUMBER_OF_OD_INSTALLMENT  > 0              เฉพาะเคสติด OD
    CONTRACT_STATUS_DESC <> 'Write Off'        ตัดหนี้สูญออก
    CONTRACT_STATUS_ID   <> 'CLS'              ตัดสัญญาที่ปิดแล้วออก

คอลัมน์ผล Map ใช้ความหมายเดียวกับ notebook
    Map_province_REGISTER  ชื่อจังหวัดถ้าอยู่ในรายชื่อน้ำท่วม · ไม่อยู่ = 'N'
    Map_district_REGISTER  ชื่ออำเภอถ้าอยู่ในรายชื่อ · ไม่อยู่ = 'N'
    Summary_REGISTER       True เมื่อตรงทั้งจังหวัดและอำเภอ
    (และชุดเดียวกันสำหรับ _CURRENT)

ต่างจาก notebook 2 จุด — ทั้งสองจุดทำให้ผลถูกขึ้น ไม่ได้เปลี่ยนเกณฑ์
  1. notebook ใช้ `if province in x` / `if district in x` ค้น substring ใน
     ที่อยู่ข้อความ · ที่นี่ join ด้วยรหัสจาก COLLECTION_S_ADDRESS
     → ครอบคลุมเคสที่ที่อยู่ข้อความว่าง (997 จาก 12,284 = 8.1%) ด้วย
  2. substring match หยุดที่จังหวัดแรกที่เจอในลำดับ dict · ถ้าที่อยู่มีชื่อ
     จังหวัดปนมาสองชื่อ (เช่นชื่อหมู่บ้าน/ถนน) จะได้ผลตามลำดับ dict ไม่ใช่
     ตามจังหวัดจริง · การ join ด้วยรหัสไม่มีปัญหานี้
  → สคริปต์รันวิธีของ notebook ควบไปด้วย แล้วรายงานจุดที่ต่างกันในชีต
    'สอบทาน_substring' ให้ตรวจได้

⚠️ ผลลัพธ์มี PII (ชื่อ · ที่อยู่ · เบอร์โทร) — .gitignore บล็อก xlsx/csv ไว้แล้ว
"""
import re
import sys
import unicodedata
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass
warnings.filterwarnings("ignore")

import db
import pandas as pd

# วันของ snapshot ที่จะใช้ — ระบุทาง argv ได้  เช่น
#     python scripts/itos/flood_waiver.py 2026-10-01
# ⚠️ ตารางต้นทางโหลดทับทุกคืน (รอบ ~23:10) เก็บแค่ snapshot เดียว
#    ย้อนวันไม่ได้ · ถ้าใส่วันที่ไม่มีในตาราง จะได้ 0 แถว
AS_OF = sys.argv[1] if len(sys.argv) > 1 else "2026-09-30"
HERE = Path(__file__).resolve().parent
OUT = HERE / "_out"
CACHE_FMT = "_cache_itos_{}.parquet"
XLS = r"C:\Users\Sapon.S\Downloads\penalty wave.xlsx"
T = "ILOAN_DATASOURCE.ILOAN_DATASOURCE.dbo"

# เขตที่หัวตารางบอกว่ารวมอยู่ (กทม. 50 เขต) แต่ไม่ได้ลิสต์ชื่อมา
BKK_MISSING = ["บางกอกน้อย", "บางกอกใหญ่"]


# ══════════════════════════════════════════════════════════════════════
#  เทียบชื่อสถานที่ — ใช้เฉพาะตอนแปลงรายชื่อน้ำท่วม 203 แถว เป็นรหัส
# ══════════════════════════════════════════════════════════════════════
def norm(s):
    """คีย์เทียบชื่อ — ตัดคำนำหน้า ช่องว่าง วรรณยุกต์ แตกสระอำ

    ต้องแตก ำ เป็น ํ + า **ก่อน** ตัดวรรณยุกต์ ไม่งั้นสองฝั่งได้คีย์ต่างกัน
    """
    s = unicodedata.normalize("NFC", str(s)).strip()
    s = re.sub(r"^(จังหวัด|กิ่งอำเภอ|อำเภอ|เขต|ตำบล|แขวง|จ\.|อ\.|ต\.)", "", s).strip()
    s = s.replace("\u0E33", "\u0E4D\u0E32")
    s = re.sub(r"[\u0E47-\u0E4E]", "", s)
    return re.sub(r"[\s\-\.]", "", s)


# ══════════════════════════════════════════════════════════════════════
#  รายชื่อเขตน้ำท่วม -> รหัสอำเภอ
# ══════════════════════════════════════════════════════════════════════
def read_flood():
    """แตก tab 'เขตน้ำท่วม' เป็น 1 แถว = 1 อำเภอ

    ต้นฉบับ 29 แถว · คอลัมน์ 3 เป็นรายชื่ออำเภอคั่นด้วยจุลภาค
    ช่อง 'ภาค' เป็น merge cell จึงต้อง ffill
    ช่องจังหวัดของ กทม. เขียน 'กรุงเทพมหานคร 50 เขต' ต้องตัดท้ายทิ้ง
    """
    f = pd.read_excel(XLS, sheet_name="เขตน้ำท่วม", dtype=str)
    f.columns = ["ภาค", "จังหวัด", "อำเภอ"]
    f["ภาค"] = f["ภาค"].ffill()
    rows = []
    for _, r in f.iterrows():
        prov = re.sub(r"\s*\d+\s*เขต\s*$", "", str(r["จังหวัด"])).strip()
        for dis in str(r["อำเภอ"]).split(","):
            dis = dis.strip()
            if dis:
                rows.append((r["ภาค"], prov, dis))
    return pd.DataFrame(rows, columns=["ภาค", "จังหวัด", "อำเภอ"]), f


def flood_to_codes(F):
    """แปลง (จังหวัด, อำเภอ) 203 คู่ เป็นรหัสอำเภอ 4 หลักของ HP_COMMON

    ทำครั้งเดียวกับ 203 แถว ตรวจได้ด้วยตา — ต่างจากการ match ชื่อ 658,768 แถว
    """
    p = db.query("k2", f"SELECT PROVINCE_CODE, NAME_THA FROM {T}.HP_COMMON_PROVINCE")
    d = db.query("k2", f"""SELECT DISTRICT_CODE, PROVINCE_CODE, NAME_THA
                           FROM {T}.HP_COMMON_DISTRICT""")
    p["k"] = p.NAME_THA.map(norm)
    d["k"] = d.NAME_THA.map(norm)
    F = F.copy()
    F["k"] = F["จังหวัด"].map(norm)
    F = F.merge(p[["PROVINCE_CODE", "k"]], on="k", how="left").drop(columns="k")
    F["k"] = F["อำเภอ"].map(norm)
    F = F.merge(d[["DISTRICT_CODE", "PROVINCE_CODE", "k"]],
                on=["PROVINCE_CODE", "k"], how="left").drop(columns="k")
    return F, p, d


# ══════════════════════════════════════════════════════════════════════
#  ดึงข้อมูล — join ด้วยรหัสทั้งหมด ไม่มีการเทียบชื่อ
# ══════════════════════════════════════════════════════════════════════
SQL_MAIN = f"""
SELECT  d.CREATE_DATE, d.EXTRACT_DATE, d.CONTRACT_ID, d.CONTRACT_NUMBER,
        d.CONTRACT_STATUS_ID, d.CONTRACT_STATUS_DESC,
        d.PRODUCT_ID, d.UPDATE_DATE, d.PRODUCT_TYPE,
        d.TOTAL_OUTSTANDING, d.TOTAL_PRINCIPAL, d.TOTAL_INTEREST, d.TOTAL_VAT,
        d.NUMBER_OF_PERIOD, d.INSTALLMENT_PER_PERIOD,
        d.PAID_TOTAL_OUTSTANDING, d.PAID_TOTAL_PRINCIPAL,
        d.PAID_TOTAL_INTEREST, d.PAID_TOTAL_VAT, d.PAID_NUMBER_OF_PERIOD,
        d.PERIOD_DUE_DATE, d.LAST_REPAY_DATE,
        d.REMAINING_OUTSTANDING, d.REMAINING_PRINCIPAL,
        d.REMAINING_INTEREST, d.REMAINING_VAT, d.REMAINING_PERIOD,
        d.INVOICE_NUMBER, d.INVOICE_DATE,
        d.NUMBER_OF_OD_INSTALLMENT, d.OD_AMOUNT, d.PENALTY_AMT,
        d.COLLECT_AMT, d.TOTAL_FOLLOW_UP_AMOUNT,
        d.IS_FIRST_DUE, d.IS_LAST_DUE,
        d.PAID_TOTAL_OUTSTANDING_TO_DUE, d.PAID_TOTAL_PRINCIPAL_TO_DUE,
        d.PAID_TOTAL_INTEREST_TO_DUE, d.PAID_TOTAL_VAT_TO_DUE,
        d.ASSIGN_TO_TEAM, d.ASSIGN_TO_TEAM_DESC,
        d.CUSTOMER_NAME, d.CUSTOMER_BIRTH_DATE, d.CUSTOMER_PHONE_NUM,
        d.CUSTOMER_OCCUPATION,
        d.CUSTOMER_ADDRESS_REGISTER, d.CUSTOMER_ADDRESS_CURRENT,
        d.PRODUCT_NAME, d.PRODUCT_MODEL, d.PRODUCT_SERIAL_NO,
        p.GENDER, p.AGE, p.OCCUPATION_DESC, p.MARITAL_STATUS,
        p.INCOME, p.CREDIT_SCORING
FROM        {T}.ITOS_COLLECTION_DETAIL    d
LEFT JOIN   {T}.ITOS_COLLECTION_PORTFOLIO p
       ON   p.EXTRACT_DATE = d.EXTRACT_DATE AND p.CONTRACT_ID = d.CONTRACT_ID
WHERE       CAST(d.CREATE_DATE AS date) = '{AS_OF}'
  AND       d.NUMBER_OF_OD_INSTALLMENT > 0
  AND       d.CONTRACT_STATUS_DESC NOT IN ('Write Off')
  AND       d.CONTRACT_STATUS_ID <> 'CLS'
"""

# ⚠️ **อย่ารวมทุก join ไว้ใน query เดียว** — เคยเขียนเป็น query เดียวที่ join
#    COLLECTION_S_ADDRESS + HP_COMMON_* ทั้ง 6 ตารางในทีเดียว แล้วค้างเกิน 10 นาที
#    เพราะ linked server ทำ remote nested loop ทีละแถว
#    ดึงแยกทีละตารางแล้วมา join ใน pandas เสร็จใน ~2 นาที
SQL_ADDR = f"""
SELECT  ADDR_CONTRACTNO, ADDR_TYPE, ADDR_ID,
        ADDR_PROVINCE, ADDR_AMPHUR, ADDR_DISTRICT, ADDR_ZIPCODE
FROM    {T}.COLLECTION_S_ADDRESS
WHERE   ADDR_TYPE IN ('AD01', 'AD02')
"""


def pull(force=False):
    """ดึงข้อมูลแล้ว cache — ตารางต้นทางโหลดครั้งเดียว ไม่มีอัปเดต

    ดึง 5 ครั้งแยกกัน แล้ว join ใน pandas · ดูเหตุผลที่คอมเมนต์ SQL_ADDR
    """
    if (OUT / CACHE_FMT.format(AS_OF)).exists() and not force:
        print(f"อ่าน cache {CACHE_FMT.format(AS_OF)}", flush=True)
        return pd.read_parquet(OUT / CACHE_FMT.format(AS_OF))

    OUT.mkdir(parents=True, exist_ok=True)
    print("ดึงสัญญา + ข้อมูลลูกค้า ...", flush=True)
    d = db.query("k2", SQL_MAIN, timeout=1800)
    print(f"  {len(d):,} สัญญา", flush=True)

    print("ดึงที่อยู่ (AD01 ปัจจุบัน · AD02 ทะเบียนบ้าน) ...", flush=True)
    a = db.query("k2", SQL_ADDR, timeout=1800)
    print(f"  {len(a):,} แถว", flush=True)

    print("ดึง master ภูมิศาสตร์ ...", flush=True)
    hp_p = db.query("k2", f"SELECT PROVINCE_CODE, NAME_THA FROM {T}.HP_COMMON_PROVINCE")
    hp_d = db.query("k2", f"SELECT DISTRICT_CODE, NAME_THA FROM {T}.HP_COMMON_DISTRICT")
    hp_s = db.query("k2", f"""SELECT SUBDISTRICT_CODE, NAME_THA
                              FROM {T}.HP_COMMON_SUBDISTRICT""")
    print(f"  {len(hp_p)} จังหวัด · {len(hp_d)} อำเภอ · {len(hp_s)} ตำบล", flush=True)

    # 836 คู่ (สัญญา, ประเภท) มี 2 แถว — เอา ADDR_ID ล่าสุด
    a = (a.sort_values("ADDR_ID")
         .drop_duplicates(["ADDR_CONTRACTNO", "ADDR_TYPE"], keep="last"))

    for code, side in [("AD02", "REG"), ("AD01", "CUR")]:
        x = a[a.ADDR_TYPE.eq(code)].rename(columns={
            "ADDR_PROVINCE": f"{side}_PROVINCE_CODE",
            "ADDR_AMPHUR":   f"{side}_DISTRICT_CODE",     # ⚠️ AMPHUR = อำเภอ
            "ADDR_DISTRICT": f"{side}_SUBDISTRICT_CODE",  # ⚠️ DISTRICT = ตำบล
            "ADDR_ZIPCODE":  f"{side}_ZIPCODE"})
        cols = [f"{side}_{c}" for c in ("PROVINCE_CODE", "DISTRICT_CODE",
                                        "SUBDISTRICT_CODE", "ZIPCODE")]
        d = d.merge(x[["ADDR_CONTRACTNO"] + cols],
                    left_on="CONTRACT_NUMBER", right_on="ADDR_CONTRACTNO",
                    how="left").drop(columns="ADDR_CONTRACTNO")
        for lv, m, key in [("PROVINCE", hp_p, "PROVINCE_CODE"),
                           ("DISTRICT", hp_d, "DISTRICT_CODE"),
                           ("SUBDISTRICT", hp_s, "SUBDISTRICT_CODE")]:
            d = d.merge(m.rename(columns={key: f"{side}_{key}",
                                          "NAME_THA": f"{side}_{lv}"}),
                        on=f"{side}_{key}", how="left")

    d.to_parquet(OUT / CACHE_FMT.format(AS_OF), index=False)
    print(f"รวมแล้ว {len(d):,} แถว · เซฟ cache", flush=True)
    return d


# ══════════════════════════════════════════════════════════════════════
#  ติดธง
# ══════════════════════════════════════════════════════════════════════
def annotate(d, F):
    """ติดธงเขตน้ำท่วม — เทียบด้วย "รหัสอำเภอ" 4 หลัก ไม่ใช่ชื่อ

    เกณฑ์ "อยู่ในเขตน้ำท่วม" = รหัสอำเภอตรงกับในรายชื่อ
    จังหวัดตรงอย่างเดียวไม่นับ เพราะบางจังหวัดท่วมไม่ทั้งจังหวัด
    (นครราชสีมา ท่วมแค่ปากช่อง 1 อำเภอ จาก 32 อำเภอ)
    """
    pset = set(F.PROVINCE_CODE.dropna())
    dset = set(F.DISTRICT_CODE.dropna())
    reg = dict(zip(F.DISTRICT_CODE, F["ภาค"]))

    for side, tag in [("REG", "REGISTER"), ("CUR", "CURRENT")]:
        inp = d[f"{side}_PROVINCE_CODE"].isin(pset)
        ind = d[f"{side}_DISTRICT_CODE"].isin(dset)
        # ความหมายตาม notebook: ใส่ "ชื่อ" เมื่ออยู่ในรายชื่อน้ำท่วม · ไม่อยู่ = 'N'
        d[f"Map_province_{tag}"] = d[f"{side}_PROVINCE"].where(inp, "N")
        d[f"Map_district_{tag}"] = d[f"{side}_DISTRICT"].where(ind, "N")
        d[f"Summary_{tag}"] = inp & ind
        d[f"ภาค_{tag}"] = d[f"{side}_DISTRICT_CODE"].map(reg)

    r = d["Summary_REGISTER"]
    c = d["Summary_CURRENT"]
    d["ตรงกับที่อยู่"] = "ไม่อยู่ในเขตน้ำท่วม"
    d.loc[r & ~c, "ตรงกับที่อยู่"] = "ทะเบียนบ้าน"
    d.loc[~r & c, "ตรงกับที่อยู่"] = "ปัจจุบัน"
    d.loc[r & c, "ตรงกับที่อยู่"] = "ทั้งสองที่"
    d["เข้าเกณฑ์_waive"] = (r | c).map({True: "Y", False: "N"})
    d["ภาคน้ำท่วม"] = d["ภาค_REGISTER"].where(r, d["ภาค_CURRENT"].where(c))
    return d


# ══════════════════════════════════════════════════════════════════════
#  วิธีของ notebook — ค้น substring ในที่อยู่ข้อความ (ไว้สอบทาน)
# ══════════════════════════════════════════════════════════════════════
def substring_map(d, F):
    """ทำซ้ำ map_location() ของ wave_flood.ipynb เพื่อเทียบผล

    ตรรกะเดิมเป๊ะ ๆ: ไล่ dict จังหวัด ถ้าชื่อจังหวัดเป็น substring ของที่อยู่
    ก็ไล่หาอำเภอในจังหวัดนั้น · เจอแล้วหยุด (return ทันที)
    """
    dd = {}
    for _, row in F.iterrows():
        dd.setdefault(row["จังหวัด"], []).append(row["อำเภอ"])

    def m(x):
        if not isinstance(x, str):
            return "N", "N", False
        for prov, dists in dd.items():
            if prov in x:
                for dis in dists:
                    if dis in x:
                        return prov, dis, True
                return prov, "N", False
        return "N", "N", False

    for tag, col in [("REGISTER", "CUSTOMER_ADDRESS_REGISTER"),
                     ("CURRENT", "CUSTOMER_ADDRESS_CURRENT")]:
        res = d[col].apply(m)
        d[f"sub_province_{tag}"] = res.apply(lambda t: t[0])
        d[f"sub_district_{tag}"] = res.apply(lambda t: t[1])
        d[f"sub_Summary_{tag}"] = res.apply(lambda t: t[2])
    return d


# ลำดับคอลัมน์ตาม wave_flood.ipynb cell [6] แล้วต่อด้วยบล็อกที่อยู่/ผล Map
COLS = [
    "CREATE_DATE", "EXTRACT_DATE", "CONTRACT_ID", "CONTRACT_NUMBER",
    "CONTRACT_STATUS_DESC",
    "PRODUCT_NAME", "PRODUCT_MODEL", "PRODUCT_SERIAL_NO",
    "TOTAL_OUTSTANDING", "TOTAL_PRINCIPAL", "TOTAL_INTEREST", "TOTAL_VAT",
    "NUMBER_OF_PERIOD", "INSTALLMENT_PER_PERIOD",
    "PAID_TOTAL_OUTSTANDING", "PAID_TOTAL_PRINCIPAL", "PAID_TOTAL_INTEREST",
    "PAID_TOTAL_VAT", "PAID_NUMBER_OF_PERIOD",
    "PERIOD_DUE_DATE", "LAST_REPAY_DATE",
    "REMAINING_OUTSTANDING", "REMAINING_PRINCIPAL", "REMAINING_INTEREST",
    "REMAINING_VAT", "REMAINING_PERIOD",
    "INVOICE_NUMBER", "INVOICE_DATE",
    "NUMBER_OF_OD_INSTALLMENT", "OD_AMOUNT", "PENALTY_AMT", "COLLECT_AMT",
    "TOTAL_FOLLOW_UP_AMOUNT",
    "CUSTOMER_NAME", "CUSTOMER_PHONE_NUM",
    "CUSTOMER_ADDRESS_REGISTER", "CUSTOMER_ADDRESS_CURRENT",
    # ── ที่อยู่ตามทะเบียนบ้าน (AD02) แยกระดับ + ผล Map ──
    "REG_PROVINCE", "REG_DISTRICT", "REG_SUBDISTRICT", "REG_ZIPCODE",
    "Map_province_REGISTER", "Map_district_REGISTER", "Summary_REGISTER",
    # ── ที่อยู่ปัจจุบัน (AD01) แยกระดับ + ผล Map ──
    "CUR_PROVINCE", "CUR_DISTRICT", "CUR_SUBDISTRICT", "CUR_ZIPCODE",
    "Map_province_CURRENT", "Map_district_CURRENT", "Summary_CURRENT",
    # ── สรุปว่าตรงกับที่อยู่ไหน ──
    "ตรงกับที่อยู่", "เข้าเกณฑ์_waive", "ภาคน้ำท่วม",
    # ── รหัสภูมิศาสตร์ (ไว้ join ต่อ) ──
    "REG_PROVINCE_CODE", "REG_DISTRICT_CODE", "REG_SUBDISTRICT_CODE",
    "CUR_PROVINCE_CODE", "CUR_DISTRICT_CODE", "CUR_SUBDISTRICT_CODE",
    # ── ข้อมูลประกอบ ──
    "CONTRACT_STATUS_ID", "PRODUCT_ID", "PRODUCT_TYPE", "UPDATE_DATE",
    "ASSIGN_TO_TEAM", "ASSIGN_TO_TEAM_DESC",
    "CUSTOMER_BIRTH_DATE", "CUSTOMER_OCCUPATION", "OCCUPATION_DESC",
    "GENDER", "AGE", "MARITAL_STATUS", "INCOME", "CREDIT_SCORING",
]


def money(x):
    return f"{x:,.2f}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # ── 1. รายชื่อเขตน้ำท่วม -> รหัส ──
    F, raw_flood = read_flood()
    F, hp_p, hp_d = flood_to_codes(F)
    print(f"เขตน้ำท่วม: {F['จังหวัด'].nunique()} จังหวัด · {len(F)} อำเภอ/เขต")
    print(f"  แปลงเป็นรหัสจังหวัดได้ {F.PROVINCE_CODE.notna().sum()}/{len(F)}")
    print(f"  แปลงเป็นรหัสอำเภอได้   {F.DISTRICT_CODE.notna().sum()}/{len(F)}")
    miss = F[F.DISTRICT_CODE.isna()]
    if len(miss):
        print("  ⚠️ หารหัสไม่เจอ:")
        print(miss[["จังหวัด", "อำเภอ"]].to_string(index=False))

    # กทม. — หัวตารางบอก 50 เขต แต่ลิสต์มา 48
    bkk = hp_d[hp_d.PROVINCE_CODE.eq(hp_p.loc[hp_p.NAME_THA.eq("กรุงเทพมหานคร"),
                                              "PROVINCE_CODE"].iloc[0])]
    bkk_gap = bkk[bkk.NAME_THA.isin(BKK_MISSING)]
    print(f"  กทม.: ลิสต์ {F['จังหวัด'].eq('กรุงเทพมหานคร').sum()} เขต "
          f"จากทั้งหมด {len(bkk)} เขต · ขาด {BKK_MISSING}")

    # ── 2. ดึงข้อมูล + ติดธง ──
    d = pull()
    d = annotate(d, F)
    n = len(d)

    # ⚠️ ตารางต้นทางถูกโหลดทับทุกวัน — ยืนยันว่าได้ snapshot ของวันที่ตั้งใจจริง
    cds = sorted(set(pd.to_datetime(d.CREATE_DATE).dt.date.astype(str)))
    print(f"\nCREATE_DATE ที่ได้จริง: {cds}")
    if cds != [AS_OF]:
        print(f"  ⚠️ ไม่ตรงกับ AS_OF = {AS_OF} — snapshot ยังไม่อัปเดตหรือเปลี่ยนไปแล้ว")

    print(f"\n── ประชากรตามเงื่อนไข ({n:,} สัญญา) ──")
    print("  CREATE_DATE = %s · ติด OD · ไม่ใช่ Write Off · ไม่ใช่ CLS" % AS_OF)
    print(d.groupby(["CONTRACT_STATUS_ID", "CONTRACT_STATUS_DESC"])
          .size().to_string())

    print(f"\n── ความครบของที่อยู่ ──")
    for side, lab in [("REG", "ทะเบียนบ้าน (AD02)"), ("CUR", "ปัจจุบัน (AD01)")]:
        for lv, nm in [("PROVINCE", "จังหวัด"), ("DISTRICT", "อำเภอ"),
                       ("SUBDISTRICT", "ตำบล")]:
            s = d[f"{side}_{lv}"].notna()
            print(f"  {lab:<20} {nm:<8} {s.sum():>7,} / {n:,} ({s.mean():>7.2%})")
    tx = d.CUSTOMER_ADDRESS_REGISTER.notna()
    print(f"  ที่อยู่ข้อความ (วิธี notebook) ใช้ได้ {tx.sum():,} / {n:,} "
          f"= {tx.mean():.2%}  → ขาด {(~tx).sum():,} ราย")

    # ── 3. ผลลัพธ์ ──
    print(f"\n{'='*70}\n ผลเขตน้ำท่วม — {n:,} เคสติด OD\n{'='*70}")
    print(d["ตรงกับที่อยู่"].value_counts().to_string())
    w = d[d["เข้าเกณฑ์_waive"].eq("Y")].copy()
    print(f"\n  เข้าเกณฑ์ waive        {len(w):>7,} ราย  ({len(w)/n:.2%})")
    print(f"    เบี้ยปรับที่จะ waive  {money(w.PENALTY_AMT.fillna(0).sum()):>15} บาท")
    print(f"    ยอดค้างชำระ          {money(w.OD_AMOUNT.fillna(0).sum()):>15} บาท")
    print(f"    ยอดคงเหลือ           {money(w.REMAINING_OUTSTANDING.fillna(0).sum()):>15} บาท")
    print(f"    มีเบี้ยปรับ > 0       {w.PENALTY_AMT.fillna(0).gt(0).sum():>7,} ราย")

    # ผลของ 2 เขต กทม. ที่หัวตารางบอกว่ารวม แต่ไม่ได้ลิสต์
    gap = d[d.REG_DISTRICT_CODE.isin(bkk_gap.DISTRICT_CODE)
            | d.CUR_DISTRICT_CODE.isin(bkk_gap.DISTRICT_CODE)]
    print(f"\n  ถ้านับ {'/'.join(BKK_MISSING)} ด้วย จะเพิ่มอีก {len(gap):,} ราย"
          f" · เบี้ยปรับ {money(gap.PENALTY_AMT.fillna(0).sum())} บาท")

    # ── 4. สอบทาน 2 ชั้น ──
    print(f"\n── สอบทาน 1: รหัส vs แกะที่อยู่ข้อความ ──")
    x = cross_check(d)

    print(f"\n── สอบทาน 2: รหัส vs วิธี substring ของ notebook ──")
    d = substring_map(d, F)
    diff = d[(d.Summary_REGISTER != d.sub_Summary_REGISTER)
             | (d.Summary_CURRENT != d.sub_Summary_CURRENT)].copy()
    for tag in ["REGISTER", "CURRENT"]:
        same = (d[f"Summary_{tag}"] == d[f"sub_Summary_{tag}"])
        print(f"  {tag:<9} ตรงกัน {same.sum():,}/{n:,} ({same.mean():.2%})")
    hasaddr = d.CUSTOMER_ADDRESS_REGISTER.notna()
    print(f"  ต่างกันทั้งหมด {len(diff):,} ราย")
    print(f"    · เพราะที่อยู่ข้อความว่าง  {len(diff[~hasaddr.reindex(diff.index)]):,}")
    print(f"    · มีที่อยู่แต่ผลไม่ตรง     {len(diff[hasaddr.reindex(diff.index)]):,}")
    sub_w = d[d.sub_Summary_REGISTER | d.sub_Summary_CURRENT]
    print(f"  วิธี notebook จะได้ {len(sub_w):,} ราย · เบี้ยปรับ "
          f"{money(sub_w.PENALTY_AMT.fillna(0).sum())} บาท")
    print(f"  วิธีรหัส (ใช้จริง)  {len(w):,} ราย · เบี้ยปรับ "
          f"{money(w.PENALTY_AMT.fillna(0).sum())} บาท")

    # ── 5. สรุปรายจังหวัด / อำเภอ ──
    w["จังหวัด"] = w.REG_PROVINCE.where(w.Summary_REGISTER, w.CUR_PROVINCE)
    w["อำเภอ"] = w.REG_DISTRICT.where(w.Summary_REGISTER, w.CUR_DISTRICT)
    w["_มีเบี้ยปรับ"] = w.PENALTY_AMT.fillna(0).gt(0)
    # ⚠️ ต้องใช้ string literal เป็นคีย์ ห้ามใช้ dict(ค้างชำระ=...) หรือ agg(ค้างชำระ=...)
    #    Python normalize ชื่อ keyword เป็น NFKC → ำ (U+0E33) แตกเป็น ํ + า
    #    หัวคอลัมน์จะดูเหมือนเดิมแต่ filter/ค้นหาใน Excel ไม่เจอ
    agg = {"ลูกหนี้":       ("CONTRACT_ID", "count"),
           "มีเบี้ยปรับ":   ("_มีเบี้ยปรับ", "sum"),
           "เบี้ยปรับ":     ("PENALTY_AMT", "sum"),
           "ยอดค้าง":       ("OD_AMOUNT", "sum"),
           "คงเหลือ":       ("REMAINING_OUTSTANDING", "sum")}
    prov_summ = (w.groupby(["ภาคน้ำท่วม", "จังหวัด"], dropna=False).agg(**agg)
                 .reset_index().sort_values("ลูกหนี้", ascending=False))
    dist_summ = (w.groupby(["ภาคน้ำท่วม", "จังหวัด", "อำเภอ"], dropna=False)
                 .agg(**agg).reset_index()
                 .sort_values("ลูกหนี้", ascending=False))

    # ── 6. เขียนไฟล์ ──
    mt = F[["ภาค", "จังหวัด", "อำเภอ", "PROVINCE_CODE", "DISTRICT_CODE"]].copy()
    mt["Map1"] = "Y"
    mt["Map2"] = "Y"

    SUBC = ["CONTRACT_NUMBER", "CONTRACT_STATUS_DESC", "PENALTY_AMT",
            "REG_PROVINCE", "REG_DISTRICT",
            "sub_province_REGISTER", "sub_district_REGISTER",
            "Summary_REGISTER", "sub_Summary_REGISTER",
            "CUSTOMER_ADDRESS_REGISTER",
            "CUR_PROVINCE", "CUR_DISTRICT",
            "sub_province_CURRENT", "sub_district_CURRENT",
            "Summary_CURRENT", "sub_Summary_CURRENT",
            "CUSTOMER_ADDRESS_CURRENT"]

    xf = OUT / f"Penalty_wave_ITOS_{AS_OF}.xlsx"
    print(f"\nเขียน {xf.name} ...", flush=True)
    with pd.ExcelWriter(xf, engine="openpyxl") as xw:
        # ชีตหลัก — เคสติด OD ทั้งหมด ติดธงแล้ว (เทียบได้กับ df ใน notebook)
        d[COLS].to_excel(xw, sheet_name="data", index=False)
        # รายชื่อที่เข้าเกณฑ์ waive
        w[COLS].sort_values("PENALTY_AMT", ascending=False).to_excel(
            xw, sheet_name="waive", index=False)
        prov_summ.to_excel(xw, sheet_name="สรุปจังหวัด", index=False)
        dist_summ.to_excel(xw, sheet_name="สรุปอำเภอ", index=False)
        raw_flood.to_excel(xw, sheet_name="เขตน้ำท่วม", index=False)
        mt.to_excel(xw, sheet_name="map table", index=False)
        diff[SUBC].to_excel(xw, sheet_name="สอบทาน_substring", index=False)
        x.head(20000).to_excel(xw, sheet_name="สอบทาน_ที่อยู่ข้อความ", index=False)
    print(f"  {xf.stat().st_size/1e6:.1f} MB · {len(d):,} แถวในชีต data")

    cf = OUT / f"Penalty_wave_ITOS_waive_{AS_OF}.csv"
    w[COLS].to_csv(cf, index=False, encoding="utf-8-sig")
    print(f"เขียน {cf.name} ({len(w):,} แถว)")
    print("\nเสร็จ — ไฟล์อยู่ที่", OUT)


def cross_check(d):
    """เทียบธงที่ได้จากรหัส กับธงที่ได้จากการแกะที่อยู่ข้อความ

    ไม่ได้ใช้ตัดสินผล — ใช้จับว่าฝั่งไหนผิด ถ้าตัวเลขสองทางต่างกันมาก
    ต้องกลับไปดู เพราะแปลว่ามีสมมติฐานข้อใดข้อหนึ่งพัง
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_txt", HERE / "_addr_text.py")
    if not (HERE / "_addr_text.py").exists():
        print("  ข้าม (ไม่มี _addr_text.py)")
        return pd.DataFrame()
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    parse = m.make_parser()
    sub = d[d.CUSTOMER_ADDRESS_REGISTER.notna()].copy()
    for side, txt in [("REG", "CUSTOMER_ADDRESS_REGISTER"), ("CUR", "CUSTOMER_ADDRESS_CURRENT")]:
        res = sub[txt].map(parse)
        sub[f"{side}_txt_prov"] = res.map(lambda t: t[0])
        sub[f"{side}_txt_dist"] = res.map(lambda t: t[1])
    for side in ["REG", "CUR"]:
        a = sub[f"{side}_PROVINCE"].fillna("")
        b = sub[f"{side}_txt_prov"].fillna("")
        okp = (a.map(norm) == b.map(norm))
        a2 = sub[f"{side}_DISTRICT"].fillna("")
        b2 = sub[f"{side}_txt_dist"].fillna("")
        okd = (a2.map(norm) == b2.map(norm))
        print(f"  {side}: จังหวัดตรงกัน {okp.sum():,}/{len(sub):,} ({okp.mean():.2%})"
              f" · อำเภอตรงกัน {okd.sum():,}/{len(sub):,} ({okd.mean():.2%})")
        sub[f"{side}_ตรงกัน"] = (okp & okd).map({True: "Y", False: "N"})
    bad = sub[(sub.REG_ตรงกัน.eq("N")) | (sub.CUR_ตรงกัน.eq("N"))]
    print(f"  ไม่ตรงกันอย่างน้อยฝั่งหนึ่ง {len(bad):,} แถว")
    return bad[["CONTRACT_NUMBER",
                "REG_PROVINCE", "REG_DISTRICT", "REG_txt_prov", "REG_txt_dist",
                "CUSTOMER_ADDRESS_REGISTER",
                "CUR_PROVINCE", "CUR_DISTRICT", "CUR_txt_prov", "CUR_txt_dist",
                "CUSTOMER_ADDRESS_CURRENT"]]


if __name__ == "__main__":
    main()
