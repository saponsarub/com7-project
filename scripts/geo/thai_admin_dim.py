# -*- coding: utf-8 -*-
"""สร้างตาราง dimension ที่อยู่ไทย — รหัส + ชื่อไทย + ชื่ออังกฤษ + ภาค

    python scripts/geo/thai_admin_dim.py

ใช้ 2 แหล่งประกบกัน โดยมีลำดับความสำคัญชัดเจน

    ★ ตัวตั้ง   ชื่อจังหวัดอำเภอตำบล.pdf (ราชบัณฑิตยสภา)
                ชื่อไทย + อังกฤษ ครบทุกแถว · 77 / 928 / 7,426
                -> ต้องรัน thai_admin_from_pdf.py ก่อน

      ตัวเสริม  provincecode.pdf
                เอามาเฉพาะ "รหัส" 2/4/6 หลัก
                ตัวไหนจับคู่ไม่ได้ -> ปล่อย NULL ไม่เดา

ทำไมสลับด้าน: ไฟล์รหัสเก่ากว่า ขาดบึงกาฬ และมีรายการที่ยุบไปแล้วปนอยู่
ถ้าใช้เป็นตัวตั้งจะได้ตารางที่ชื่ออังกฤษโหว่ 23% และมีแถวที่เลิกใช้แล้ว

ผลลัพธ์ใน _out/
    dim_province.csv · dim_district.csv · dim_subdistrict.csv
    thai_admin_dim.xlsx        รวมทุกชีต + ชีตที่จับคู่ไม่ได้
    thai_admin_dim.sql         CREATE TABLE + FK

═══════════════════════════════════════════════════════════════════════
 ⚠️ กับดักของ provincecode.pdf
═══════════════════════════════════════════════════════════════════════

① ฟอนต์ BrowaliaNew เก็บวรรณยุกต์/สระไว้ใน Private Use Area (U+F7xx)
   ถ้าไม่แปลงกลับ จะได้ "ไมมีขอมูล" แทน "ไม่มีข้อมูล"
   ตรวจกับคำที่รู้คำตอบแล้วได้ตารางแปลงด้านล่าง

② ไม่มีอักขระช่องว่างเลยทั้งเล่ม — แยกคอลัมน์ด้วยพิกัดไม่ได้เสถียร
   แต่รหัสเป็นตัวเลขล้วน ชื่อเป็นไทยล้วน จึงแยกด้วย "ชนิดอักขระ" แทน
   รูปแบบคงที่เสมอ  เลข2 ไทย เลข4 ไทย เลข6 ไทย

③ สระอำเขียนแบบแยกส่วน  ํ + า  ต้องประกอบกลับเป็น ำ

④ มีแถว "ไม่มีข้อมูล" รหัส 00 / 0000 / 000000 เป็นค่า placeholder
   และรหัสลงท้าย 99 คือตำบลที่ยุบ/เปลี่ยนชื่อ — เก็บไว้ แต่ทำธงบอก
═══════════════════════════════════════════════════════════════════════
"""
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import pdfplumber

HERE = Path(__file__).resolve().parent
OUT = HERE / "_out"
CODE_PDF = r"C:\Users\Sapon.S\Downloads\provincecode.pdf"
RCODE_XLS = r"C:\Users\Sapon.S\Downloads\rcode.xlsx"
RCODE2_PDF = r"C:\Users\Sapon.S\Downloads\rcode2.pdf"

# ── ตารางแปลง Private Use Area -> อักขระไทยจริง ────────────────────────
# ตรวจยืนยันกับคำที่รู้คำตอบทุกตัว เช่น
#   ไมมี -> ไม่มี · ขอมูล -> ข้อมูล · ราษฎร -> ราษฎร์
#   ปอม -> ป้อม · บางกะป -> บางกะปิ · ตีนเปด -> ตีนเป็ด · โตะ -> โต๊ะ
PUA = {
    "\uF700": "\u0E4D", "\uF701": "\u0E34", "\uF702": "\u0E35",
    "\uF703": "\u0E36", "\uF704": "\u0E37",
    "\uF705": "\u0E48", "\uF706": "\u0E49", "\uF707": "\u0E4A",
    "\uF708": "\u0E4B", "\uF709": "\u0E4C",
    "\uF70A": "\u0E48", "\uF70B": "\u0E49", "\uF70C": "\u0E4A",
    "\uF70D": "\u0E4B", "\uF70E": "\u0E4C",
    "\uF70F": "\u0E0D",                       # ญ ไม่มีเชิง
    "\uF710": "\u0E31", "\uF711": "\u0E47", "\uF712": "\u0E47",
    "\uF713": "\u0E48", "\uF714": "\u0E49", "\uF715": "\u0E4A",
    "\uF716": "\u0E4B", "\uF717": "\u0E4C",
    "\uF718": "\u0E3A", "\uF719": "\u0E10",   # ฐ ไม่มีฐาน
}

DIGIT = re.compile(r"[0-9]+")
THAI = re.compile(r"[ก-๛]")


# วรรณยุกต์/ทัณฑฆาต ต้องอยู่หลังสระบน-ล่างเสมอ
TONE = "็่้๊๋์๎"
BELOW = "ิีึืุูัฺํ"
SWAP = re.compile("([%s])([%s])" % (TONE, BELOW))


def fix(t):
    """แปลง PUA กลับเป็นอักขระไทย + ประกอบสระอำ + จัดลำดับสระ/วรรณยุกต์

    ⚠️ ไฟล์นี้วางวรรณยุกต์ก่อนสระในบางคำ เช่นได้ "กาฬสินธ์ุ"
       ที่ถูกคือ "กาฬสินธุ์" — สระล่างมาก่อน ทัณฑฆาตมาหลัง
    """
    for a, b in PUA.items():
        t = t.replace(a, b)
    t = t.replace("ํา", "ำ")
    for _ in range(2):                    # สลับซ้ำเผื่อซ้อนหลายชั้น
        t = SWAP.sub(lambda m: m.group(2) + m.group(1), t)
    return t.strip()


RC2_LINE = re.compile(r"^(\d{4})\s+(\d{6})\s+(.*)$")
RC2_SPLIT = re.compile(r"(?:ตํ?าบล|แขวง)")


def read_rcode2(path=RCODE2_PDF):
    """ทะเบียนผู้มีสิทธิเลือกตั้งผู้แทนเกษตรกร — มีรหัสตำบล 6 หลัก

    รูปแบบคงที่ทั้งเล่ม
        1001 100102 เขตพระนคร แขวงวังบูรพาภิรมย์ 6 6 12
        4511 451110 อำเภอสุวรรณภูมิ ตำบลน้ำคำ 500 612 1112
        <รหัสอำเภอ> <รหัสตำบล> <ชื่ออำเภอ> <ชื่อตำบล> <ชาย> <หญิง> <รวม>

    ⚠️ ไฟล์แทรกช่องว่างระหว่างตัวอักษรแทบทุกตัว  "เ ข ต พ ร ะ น ค ร"
       ชื่อสถานที่ไทยไม่มีช่องว่างอยู่แล้ว จึงลบช่องว่างทิ้งทั้งหมดได้
    ⚠️ ใช้ Thai PUA เหมือน provincecode.pdf — norm() แปลงให้แล้ว
    ⚠️ ตัวเลขจำนวนคนท้ายบรรทัดก็ถูกแทรกช่องว่าง ต้องลบตัวเลขทิ้งก่อนตัดชื่อ
    """
    rows = []
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        for pi, pg in enumerate(pdf.pages, 1):
            if pi % 50 == 0 or pi == total:
                print(f"  อ่านหน้า {pi}/{total}", flush=True)
            for ln in (pg.extract_text() or "").split("\n"):
                m = RC2_LINE.match(ln.strip())
                if not m:
                    continue
                dc, sc, rest = m.groups()
                rest = re.sub(r"[0-9,\-]", "", rest).replace(" ", "")
                parts = RC2_SPLIT.split(rest)
                if len(parts) < 2:
                    continue
                rows.append((dc, sc, parts[-1]))
    d = pd.DataFrame(rows, columns=["district_code", "subdistrict_code", "nm"])
    d = d.drop_duplicates("subdistrict_code")
    d["k"] = d.nm.map(norm)
    return d[["district_code", "k", "subdistrict_code"]] \
        .drop_duplicates(["district_code", "k"])


def read_rcode(path=RCODE_XLS):
    """ทำเนียบท้องที่ กรมการปกครอง (ข้อมูล 1 ก.ย. 2566) — ใหม่กว่า PDF

    รหัส 4 หลัก · 2 ตัวแรกคือรหัสจังหวัดมาตรฐาน
        3800 = จังหวัดบึงกาฬ      -> province_code 38
        3801 = อำเภอเมืองบึงกาฬ   -> district_code 3801

    ⚠️ ในไฟล์ปนสำนักทะเบียนเทศบาล 1,573 แถว ซึ่งไม่ใช่อำเภอ ต้องกรองทิ้ง
    ⚠️ มีแถวที่จำหน่ายแล้ว 187 แถว ดูคอลัมน์วันที่จำหน่าย (0 = ยังใช้อยู่)
    ⚠️ ชื่อเขตของ กทม. ขึ้นต้นด้วย "ท้องถิ่นเขต" ต้องตัดออกก่อนเทียบ
    """
    d = pd.read_excel(path, sheet_name=0, dtype=str, skiprows=4)
    d.columns = ["code", "name_th", "name_en", "cancel"]
    d = d.dropna(subset=["code"])
    d["code"] = d.code.astype(str).str.strip()
    d = d[d.code.str.fullmatch(r"\d{4}")]
    d = d[d.cancel.fillna("0").astype(str).str.strip().isin(["0", "0.0"])]

    prov = d[d.code.str[2:] == "00"].copy()
    prov["province_code"] = prov.code.str[:2]
    prov["k"] = prov.name_th.map(norm)

    dist = d[(d.code.str[2:] != "00")
             & d.name_th.str.match(r"(ท้องถิ่นเขต|อำเภอ|กิ่งอำเภอ)")].copy()
    dist["province_code"] = dist.code.str[:2]
    dist["k"] = dist.name_th.map(norm)
    return (prov[["k", "province_code"]].drop_duplicates("k"),
            dist[["k", "province_code", "code"]]
            .drop_duplicates(["k", "province_code"])
            .rename(columns={"code": "district_code"}))


def read_codes(path=CODE_PDF):
    """อ่านไฟล์รหัส -> DataFrame 6 คอลัมน์

    แยกคอลัมน์ด้วย "ชนิดอักขระ" ไม่ใช่พิกัด เพราะไฟล์นี้ไม่มีช่องว่างเลย
    """
    rows = []
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        for pi, pg in enumerate(pdf.pages, 1):
            if pi % 50 == 0 or pi == total:
                print(f"  อ่านหน้า {pi}/{total}", flush=True)
            lines = defaultdict(list)
            for c in pg.chars:
                lines[round(c["top"])].append(c)
            for k in sorted(lines):
                cs = sorted(lines[k], key=lambda c: c["x0"])
                txt = fix("".join(c["text"] for c in cs))
                if txt.startswith("รหัส"):           # หัวตาราง
                    continue
                # สลับ เลข/ไทย เป็นชุด ๆ
                parts, cur, kind = [], [], None
                for ch in txt:
                    k2 = "d" if ch.isdigit() else ("t" if THAI.match(ch) else None)
                    if k2 is None:
                        continue
                    if k2 != kind and cur:
                        parts.append("".join(cur))
                        cur = []
                    kind, _ = k2, cur.append(ch)
                if cur:
                    parts.append("".join(cur))
                if len(parts) == 6 and all(p.isdigit() for p in parts[::2]):
                    rows.append(parts)
    df = pd.DataFrame(rows, columns=[
        "province_code", "province_name_th", "district_code",
        "district_name_th", "subdistrict_code", "subdistrict_name_th"])
    # ⚠️ ไฟล์รหัสเก็บคำนำหน้าไว้ ("เขตพระนคร") แต่ไฟล์ชื่อตัดออกแล้ว ("พระนคร")
    #    ถ้าไม่ตัดให้ตรงกัน จับคู่ชื่ออังกฤษไม่ติดเลยสักแถว
    df["district_name_th"] = df.district_name_th.str.replace(
        r"^(กิ่งอำเภอ|อำเภอ|เขต)", "", regex=True).str.strip()
    df["subdistrict_name_th"] = df.subdistrict_name_th.str.replace(
        r"^(ตำบล|แขวง)", "", regex=True).str.strip()
    return df


# ── ภาคของประเทศไทย ───────────────────────────────────────────────────
# ใช้เกณฑ์ราชบัณฑิตยสถาน 6 ภาค (ที่ใช้ในตำราภูมิศาสตร์)
# แบบ 5 ภาค = ยุบ "ตะวันตก" เข้ากับ "กลาง"
REGION6 = {
    "ภาคเหนือ": """เชียงราย เชียงใหม่ น่าน พะเยา แพร่ แม่ฮ่องสอน ลำปาง ลำพูน
                  อุตรดิตถ์""",
    "ภาคตะวันออกเฉียงเหนือ": """กาฬสินธุ์ ขอนแก่น ชัยภูมิ นครพนม นครราชสีมา บึงกาฬ
                  บุรีรัมย์ มหาสารคาม มุกดาหาร ยโสธร ร้อยเอ็ด เลย ศรีสะเกษ สกลนคร
                  สุรินทร์ หนองคาย หนองบัวลำภู อำนาจเจริญ อุดรธานี อุบลราชธานี""",
    "ภาคกลาง": """กรุงเทพมหานคร กำแพงเพชร ชัยนาท นครนายก นครปฐม นครสวรรค์ นนทบุรี
                  ปทุมธานี พระนครศรีอยุธยา พิจิตร พิษณุโลก เพชรบูรณ์ ลพบุรี
                  สมุทรปราการ สมุทรสงคราม สมุทรสาคร สระบุรี สิงห์บุรี สุโขทัย
                  สุพรรณบุรี อ่างทอง อุทัยธานี""",
    "ภาคตะวันออก": """จันทบุรี ฉะเชิงเทรา ชลบุรี ตราด ปราจีนบุรี ระยอง สระแก้ว""",
    "ภาคตะวันตก": """กาญจนบุรี ตาก ประจวบคีรีขันธ์ เพชรบุรี ราชบุรี""",
    "ภาคใต้": """กระบี่ ชุมพร ตรัง นครศรีธรรมราช นราธิวาส ปัตตานี พังงา พัทลุง
                  ภูเก็ต ยะลา ระนอง สงขลา สตูล สุราษฎร์ธานี""",
}
PROV_REGION6 = {p: r for r, s in REGION6.items() for p in s.split()}
PROV_REGION5 = {p: ("ภาคกลาง" if r == "ภาคตะวันตก" else r)
                for p, r in PROV_REGION6.items()}


def norm(s):
    """ตัดวรรณยุกต์/ทัณฑฆาตออก ใช้จับคู่ชื่อข้ามสองไฟล์

    ⚠️ สองไฟล์สะกดต่างกันเล็กน้อยได้ เช่น มีการันต์บ้างไม่มีบ้าง
       จับคู่แบบตรงตัวจะพลาดเยอะ จึงเทียบแบบตัดเครื่องหมายออกก่อน
    """
    s = str(s)
    for a, b in PUA.items():      # ทั้ง provincecode และ rcode2 ใช้ Thai PUA
        s = s.replace(a, b)
    s = unicodedata.normalize("NFC", s)
    # ⚠️ ไฟล์ชื่อเก็บคำนำหน้าไว้ ("อำเภอไชโย") แต่ไฟล์รหัสตัดออกแล้ว ("ไชโย")
    #    ตัดออกทั้งสองฝั่ง "เฉพาะตอนเทียบ" ส่วนที่ส่งมอบยังเก็บคำนำหน้าไว้ครบ
    s = re.sub(r"^ท้องถิ่น", "", s).strip()
    s = re.sub(r"^(จังหวัด|กิ่งอำเภอ|อำเภอ|เขต|ตำบล|แขวง)", "", s).strip()
    s = re.sub(r"^(CHANGWAT|King Amphoe|Amphoe|Khet|Khwaeng|Tambon)\s+",
               "", s, flags=re.I).strip()
    # ⚠️ แตกสระอำก่อนตัดวรรณยุกต์ ไม่งั้นสองฝั่งได้คีย์คนละแบบ
    #    เรา  น้ำคำ -> น้ําคํา -> นาคา   ·   ไฟล์ นํ้าคํา -> นาคา
    s = s.replace("ำ", "ํา")
    s = re.sub(r"[็-๎]", "", s)      # วรรณยุกต์ · ไม้ไต่คู้ · การันต์
    return re.sub(r"[\s\-\.]", "", s)




def main():
    OUT.mkdir(exist_ok=True)

    # ══════════════════════════════════════════════════════════════════
    # ตัวตั้งคือไฟล์ "ชื่อ" ของราชบัณฑิตยสภา — ชื่อไทย/อังกฤษครบทุกแถว
    # ไฟล์ "รหัส" เอามาเติมรหัสอย่างเดียว ตัวไหนไม่เจอปล่อย NULL
    #
    # 🔴 ความสัมพันธ์ระหว่างตารางใช้ *_id ไม่ใช่ *_code
    #    เพราะ code เป็นของกรมการปกครอง ขาดได้ (บึงกาฬตั้งปี 2554)
    #    ถ้าผูก FK ด้วย code จะมี 8 อำเภอ 607 ตำบล หลุดจากลำดับชั้น
    # ══════════════════════════════════════════════════════════════════
    name_csv = OUT / "thai_admin_full.csv"
    if not name_csv.exists():
        sys.exit(f"ไม่พบ {name_csv}\n  รัน thai_admin_from_pdf.py ก่อน")
    nm = pd.read_csv(name_csv, encoding="utf-8-sig").fillna("")
    print(f"ไฟล์ชื่อ (ตัวตั้ง)  {len(nm):,} แถว")

    print("อ่านไฟล์รหัส ...", flush=True)
    code = read_codes()
    print(f"ไฟล์รหัส (ตัวเสริม) {len(code):,} แถว")
    code = code[~code.subdistrict_name_th.eq("ไม่มีข้อมูล")]
    code = code[~code.province_code.isin(["00", "99"])]

    for c in ("province_th", "district_th", "subdistrict_th"):
        nm["k_" + c] = nm[c].map(norm)
    print("อ่านทำเนียบท้องที่ 2566 ...", flush=True)
    r_prov, r_dist = read_rcode()
    print("อ่านรหัสตำบล (rcode2) ...", flush=True)
    r_sub = read_rcode2()
    print(f"  ตำบล {len(r_sub):,}")
    print(f"  จังหวัด {len(r_prov)} · อำเภอ {len(r_dist)}")

    code["k_province_th"] = code.province_name_th.map(norm)
    code["k_district_th"] = code.district_name_th.map(norm)
    code["k_subdistrict_th"] = code.subdistrict_name_th.map(norm)

    # ── ตาราง 1 : จังหวัด ────────────────────────────────────────────
    pv = (nm[["province_th", "province_en", "k_province_th"]]
          .drop_duplicates("k_province_th")
          .sort_values("province_th").reset_index(drop=True))
    pv = pv.merge(code[["k_province_th", "province_code"]]
                  .drop_duplicates("k_province_th"),
                  on="k_province_th", how="left")
    # ⚠️ ตารางภาคใช้ชื่อเปล่า แต่ province_th ตอนนี้มี "จังหวัด" นำหน้า
    #    จึงต้องค้นด้วยชื่อที่ตัดคำนำหน้าแล้ว
    bare = pv.province_th.str.replace(r"^จังหวัด", "", regex=True).str.strip()
    # ⚠️ ลำดับสำคัญ — ต้องเติมรหัสจังหวัดก่อน ไม่งั้นอำเภอของจังหวัดนั้น
    #    จะจับคู่ไม่ได้ เพราะคีย์อำเภอคือ (ชื่อ, รหัสจังหวัด)
    pv = pv.merge(r_prov.rename(columns={"province_code": "_rc"}),
                  left_on="k_province_th", right_on="k", how="left")
    filled_p = int(pv.province_code.isna().sum() - (pv.province_code.fillna(pv._rc)).isna().sum())
    pv["province_code"] = pv.province_code.fillna(pv._rc)
    pv = pv.drop(columns=["_rc", "k"], errors="ignore")

    pv["Region_6"] = bare.map(PROV_REGION6)
    pv["Region_5"] = bare.map(PROV_REGION5)
    pv.insert(0, "province_id", range(1, len(pv) + 1))
    dim_p = pv.rename(columns={"province_th": "province_name_th",
                               "province_en": "province_name_en"})[
        ["province_id", "province_code", "province_name_th",
         "province_name_en", "Region_6", "Region_5"]]

    # ── ตาราง 2 : อำเภอ / เขต ────────────────────────────────────────
    dt = (nm[["province_th", "district_th", "district_en",
              "k_province_th", "k_district_th"]]
          .drop_duplicates(["k_province_th", "k_district_th"])
          .sort_values(["province_th", "district_th"]).reset_index(drop=True))
    dt = dt.merge(code[["k_province_th", "k_district_th", "district_code"]]
                  .drop_duplicates(["k_province_th", "k_district_th"]),
                  on=["k_province_th", "k_district_th"], how="left")
    # ผูกกับจังหวัดด้วย id — มาจากไฟล์ชื่อเดียวกัน จึงครบเสมอ
    dt = dt.merge(pv[["k_province_th", "province_id", "province_code"]],
                  on="k_province_th", how="left")
    dt = dt.merge(r_dist.rename(columns={"district_code": "_rc"}),
                  left_on=["k_district_th", "province_code"],
                  right_on=["k", "province_code"], how="left")
    filled_d = int(dt.district_code.isna().sum() - (dt.district_code.fillna(dt._rc)).isna().sum())
    dt["district_code"] = dt.district_code.fillna(dt._rc)
    dt = dt.drop(columns=["_rc", "k"], errors="ignore")

    dt.insert(0, "district_id", range(1, len(dt) + 1))
    dim_d = dt.rename(columns={"district_th": "district_name_th",
                               "district_en": "district_name_en"})[
        ["district_id", "district_code", "district_name_th",
         "district_name_en", "province_id", "province_code"]]

    # ── ตาราง 3 : ตำบล / แขวง ────────────────────────────────────────
    sd = nm.sort_values(["province_th", "district_th",
                         "subdistrict_th"]).reset_index(drop=True)
    sd = sd.merge(code[["k_province_th", "k_district_th", "k_subdistrict_th",
                        "subdistrict_code"]]
                  .drop_duplicates(["k_province_th", "k_district_th",
                                    "k_subdistrict_th"]),
                  on=["k_province_th", "k_district_th", "k_subdistrict_th"],
                  how="left")
    sd = sd.merge(dt[["k_province_th", "k_district_th", "district_id",
                      "district_code", "province_id"]],
                  on=["k_province_th", "k_district_th"], how="left")
    # เติมรหัสตำบลที่ PDF เดิมไม่มี — คีย์คือ (รหัสอำเภอ, ชื่อตำบล)
    sd = sd.merge(r_sub.rename(columns={"subdistrict_code": "_rc"}),
                  left_on=["district_code", "k_subdistrict_th"],
                  right_on=["district_code", "k"], how="left")
    filled_s = int(sd.subdistrict_code.isna().sum()
                   - sd.subdistrict_code.fillna(sd._rc).isna().sum())
    sd["subdistrict_code"] = sd.subdistrict_code.fillna(sd._rc)
    sd = sd.drop(columns=["_rc", "k"], errors="ignore")

    sd.insert(0, "subdistrict_id", range(1, len(sd) + 1))
    dim_s = sd.rename(columns={"subdistrict_th": "subdistrict_name_th",
                               "subdistrict_en": "subdistrict_name_en"})[
        ["subdistrict_id", "subdistrict_code", "subdistrict_name_th",
         "subdistrict_name_en", "district_id", "district_code",
         "province_id"]]

    # ══════════════════════════════════════════════════════════════════
    print("\n── ผล ──")
    for lab, d in (("dim_province", dim_p), ("dim_district", dim_d),
                   ("dim_subdistrict", dim_s)):
        print(f"  {lab:18} {len(d):>6,} แถว")

    print("\n── 🔴 คีย์ความสัมพันธ์ (ต้องไม่มี NULL เลย) ──")
    for lab, d, c in (("district.province_id", dim_d, "province_id"),
                      ("subdistrict.district_id", dim_s, "district_id"),
                      ("subdistrict.province_id", dim_s, "province_id")):
        n = d[c].isna().sum()
        print(f"  {lab:26} NULL {n}   {'OK' if n == 0 else '<-- มีปัญหา'}")

    print("\n── rcode.xlsx เติมรหัสที่ PDF ไม่มี ──")
    print(f"  จังหวัด  +{filled_p}")
    print(f"  อำเภอ    +{filled_d}")
    print(f"  ตำบล     +{filled_s}   (จาก rcode2.pdf)")

    print("\n── รหัสอ้างอิงภายนอก (ขาดได้ ไม่กระทบ join) ──")
    for lab, d, c in (("province_code", dim_p, "province_code"),
                      ("district_code", dim_d, "district_code"),
                      ("subdistrict_code", dim_s, "subdistrict_code")):
        got = d[c].notna().sum()
        print(f"  {lab:18} {got:>6,} / {len(d):>6,}  ({got/len(d)*100:5.1f}%)")

    nocode = dim_p[dim_p.province_code.isna()]
    if len(nocode):
        print(f"\n  จังหวัดที่ไม่มีรหัส: {', '.join(nocode.province_name_th)}"
              f"  (แต่ join ได้ปกติเพราะใช้ id)")
    print("\n── จังหวัดต่อภาค ──")
    print(dim_p.groupby("Region_6").size().sort_values(ascending=False).to_string())

    # ── เขียนไฟล์ ────────────────────────────────────────────────────
    enc = "utf-8-sig"
    dim_p.to_csv(OUT / "dim_province.csv", index=False, encoding=enc)
    dim_d.to_csv(OUT / "dim_district.csv", index=False, encoding=enc)
    dim_s.to_csv(OUT / "dim_subdistrict.csv", index=False, encoding=enc)

    nocode_all = pd.concat([
        dim_p[dim_p.province_code.isna()].assign(ระดับ="จังหวัด")
            .rename(columns={"province_name_th": "name_th"})[["ระดับ", "name_th"]],
        dim_d[dim_d.district_code.isna()].assign(ระดับ="อำเภอ")
            .rename(columns={"district_name_th": "name_th"})[["ระดับ", "name_th"]],
        dim_s[dim_s.subdistrict_code.isna()].assign(ระดับ="ตำบล")
            .rename(columns={"subdistrict_name_th": "name_th"})[["ระดับ", "name_th"]],
    ], ignore_index=True)
    nocode_all.to_csv(OUT / "no_code.csv", index=False, encoding=enc)

    # ══════════════════════════════════════════════════════════════════
    # ตารางรวม 3 ระดับในแถวเดียว — สำหรับคนที่ไม่อยาก join เอง
    # 1 แถว = 1 ตำบล พร้อมอำเภอและจังหวัดที่สังกัด ครบทั้ง id · code · ชื่อ
    # ══════════════════════════════════════════════════════════════════
    flat = (dim_s
            .merge(dim_d.drop(columns=["province_code"]), on="district_id",
                   how="left", suffixes=("", "_d"))
            .merge(dim_p, on="province_id", how="left", suffixes=("", "_p")))
    flat = flat[[
        "province_id", "province_code", "province_name_th", "province_name_en",
        "Region_6", "Region_5",
        "district_id", "district_code", "district_name_th", "district_name_en",
        "subdistrict_id", "subdistrict_code", "subdistrict_name_th",
        "subdistrict_name_en",
    ]]
    flat.to_csv(OUT / "dim_admin_flat.csv", index=False, encoding=enc)

    with pd.ExcelWriter(OUT / "thai_admin_dim.xlsx", engine="openpyxl") as xw:
        flat.to_excel(xw, sheet_name="รวม3ระดับ", index=False)
        dim_p.to_excel(xw, sheet_name="dim_province", index=False)
        dim_d.to_excel(xw, sheet_name="dim_district", index=False)
        dim_s.to_excel(xw, sheet_name="dim_subdistrict", index=False)
        nocode_all.to_excel(xw, sheet_name="ยังไม่มีรหัส", index=False)

    (OUT / "thai_admin_dim.sql").write_text(SCHEMA, encoding="utf-8")
    print(f"\nเขียนลง {OUT}")
    for f in ("dim_admin_flat.csv",
              "dim_province.csv", "dim_district.csv", "dim_subdistrict.csv",
              "thai_admin_dim.xlsx", "thai_admin_dim.sql", "no_code.csv"):
        q = OUT / f
        print(f"  {f:26} {q.stat().st_size/1024:8.1f} KB")


SCHEMA = """-- ตาราง dimension ที่อยู่ไทย · nvarchar ทั้งหมด รองรับ UTF-8
-- ตัวตั้งคือไฟล์ชื่อของราชบัณฑิตยสภา — ชื่อไทย/อังกฤษครบทุกแถว
-- รหัสมาจาก provincecode.pdf — ตัวไหนไม่มีปล่อย NULL
--
-- 🔴 ความสัมพันธ์ผูกด้วย *_id ไม่ใช่ *_code
--    code เป็นของกรมการปกครอง ขาดได้เมื่อมีจังหวัด/อำเภอใหม่
--    (บึงกาฬตั้งปี 2554 · ไฟล์รหัสเก่ากว่า จึงไม่มี 1 จังหวัด 8 อำเภอ 607 ตำบล)
--    ถ้าผูก FK ด้วย code รายการเหล่านั้นจะหลุดจากลำดับชั้นทั้งหมด

CREATE TABLE dbo.dim_province (
    province_id      int           NOT NULL IDENTITY(1,1),
    province_code    nvarchar(2)   NULL,        -- รหัสกรมการปกครอง 2 หลัก
    province_name_th nvarchar(50)  NOT NULL,
    province_name_en nvarchar(50)  NOT NULL,
    Region_6         nvarchar(40)  NOT NULL,    -- เกณฑ์ราชบัณฑิตยสถาน 6 ภาค
    Region_5         nvarchar(40)  NOT NULL,    -- ยุบภาคตะวันตกเข้ากับภาคกลาง
    CONSTRAINT pk_dim_province PRIMARY KEY (province_id),
    CONSTRAINT uq_dim_province_code UNIQUE (province_code)
);

CREATE TABLE dbo.dim_district (
    district_id      int           NOT NULL IDENTITY(1,1),
    district_code    nvarchar(4)   NULL,        -- 2 ตัวแรก = province_code
    district_name_th nvarchar(60)  NOT NULL,
    district_name_en nvarchar(60)  NOT NULL,
    province_id      int           NOT NULL,    -- ★ คีย์ความสัมพันธ์
    province_code    nvarchar(2)   NULL,        -- สำเนาไว้อ่านง่าย ไม่ใช่ FK
    CONSTRAINT pk_dim_district PRIMARY KEY (district_id),
    CONSTRAINT uq_dim_district_code UNIQUE (district_code),
    CONSTRAINT fk_district_province FOREIGN KEY (province_id)
        REFERENCES dbo.dim_province (province_id)
);

CREATE TABLE dbo.dim_subdistrict (
    subdistrict_id      int           NOT NULL IDENTITY(1,1),
    subdistrict_code    nvarchar(6)   NULL,     -- 4 ตัวแรก = district_code
    subdistrict_name_th nvarchar(60)  NULL,
    subdistrict_name_en nvarchar(60)  NOT NULL,
    district_id         int           NOT NULL, -- ★ คีย์ความสัมพันธ์
    district_code       nvarchar(4)   NULL,     -- สำเนาไว้อ่านง่าย ไม่ใช่ FK
    province_id         int           NOT NULL, -- ทางลัด ไม่ต้อง join 2 ต่อ
    CONSTRAINT pk_dim_subdistrict PRIMARY KEY (subdistrict_id),
    CONSTRAINT uq_dim_subdistrict_code UNIQUE (subdistrict_code),
    CONSTRAINT fk_subdistrict_district FOREIGN KEY (district_id)
        REFERENCES dbo.dim_district (district_id),
    CONSTRAINT fk_subdistrict_province FOREIGN KEY (province_id)
        REFERENCES dbo.dim_province (province_id)
);

CREATE INDEX ix_district_province    ON dbo.dim_district    (province_id);
CREATE INDEX ix_subdistrict_district ON dbo.dim_subdistrict (district_id);
CREATE INDEX ix_subdistrict_province ON dbo.dim_subdistrict (province_id);
CREATE INDEX ix_province_name_th     ON dbo.dim_province    (province_name_th);
CREATE INDEX ix_district_name_th     ON dbo.dim_district    (district_name_th);
CREATE INDEX ix_subdistrict_name_th  ON dbo.dim_subdistrict (subdistrict_name_th);

-- ⚠️ นำเข้าด้วย BULK INSERT ต้องระบุ CODEPAGE ไม่งั้นภาษาไทยเพี้ยนทั้งตาราง
-- BULK INSERT dbo.dim_province FROM 'dim_province.csv'
-- WITH (FORMAT='CSV', FIRSTROW=2, CODEPAGE='65001', DATAFILETYPE='char');
"""


if __name__ == "__main__":
    main()
