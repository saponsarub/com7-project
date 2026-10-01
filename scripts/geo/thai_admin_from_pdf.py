# -*- coding: utf-8 -*-
"""แปลง PDF รายชื่อ จังหวัด / อำเภอ-เขต / ตำบล-แขวง ของราชบัณฑิตยสภา เป็น CSV + Excel

    python scripts/geo/thai_admin_from_pdf.py
    python scripts/geo/thai_admin_from_pdf.py "path\\to\\file.pdf" --out D:\\งาน\\geo

ผลลัพธ์ใน _out/
    thai_admin_full.csv        ตารางแบน 1 แถว = 1 ตำบล/แขวง  (พร้อม import)
    thai_province.csv          จังหวัด
    thai_district.csv          อำเภอ + เขต
    thai_subdistrict.csv       ตำบล + แขวง
    thai_admin.xlsx            รวมทุกชีต
    thai_admin_schema.sql      CREATE TABLE — nvarchar ทั้งหมด

═══════════════════════════════════════════════════════════════════════
 ⚠️ กับดัก 2 ข้อของไฟล์นี้ ที่ทำให้ดึงตรง ๆ ไม่ได้
═══════════════════════════════════════════════════════════════════════

① เป็นตาราง 3 คอลัมน์ — extract_text() จะได้ไทยทั้งก้อนแล้วอังกฤษทั้งก้อน
   จับคู่กันไม่ได้ จึงต้องอ่านพิกัด x/y ของทุกตัวอักษรแล้วประกอบแถวเอง

   ระดับชั้นดูจาก x0 ของคอลัมน์อังกฤษ เพราะฝั่งไทยย่อหน้าไม่คงที่
       x0 ~348  =  Khet / Amphoe      (อำเภอ · เขต)
       x0 ~364  =  Khwaeng / Tambon   (ตำบล · แขวง)

② 🔴 ฟอนต์ในไฟล์เข้ารหัสสระผิด — ตรวจกับตัวอักษรจริงแล้วได้กฎนี้

   อักขระที่ฟอนต์ทำหาย ถูกแทนด้วย "ช่องว่างที่ x ทับกับตัวถัดไปพอดี"
   นับจำนวนช่องว่างทับซ้อนแล้วเติมกลับได้

       อ + [1 ช่องว่าง] + า        ->  อำ      (สระอำ)
       น + [2 ช่องว่าง] + า        ->  น้ำ     (ไม้โท + สระอำ)
       ตี + [1 ช่องว่าง] + ย       ->  เตี้ย   (ไม้โทที่หาย)

   ⚠️ ช่องว่างจริง (ย่อหน้า · คั่นคำ) มีระยะห่างชัดเจน อย่าเอาไปปนกัน

   อีกอาการ — ฟอนต์หนาเขียน "า" เป็น "ำ" (ใช้กับชื่อจังหวัดเท่านั้น)
       "กรุงเทพมหำนคร"  ->  กรุงเทพมหานคร
       "นครรำชสีมำ"     ->  นครราชสีมา

   ถ้าไม่แก้ทั้งสองอาการ ชื่อจังหวัดผิด 58 จาก 77 · ตำบลผิดอีก 133 แห่ง
═══════════════════════════════════════════════════════════════════════
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import pdfplumber

OUT = Path(__file__).resolve().parent / "_out"

# ── เส้นแบ่งคอลัมน์ (pt) ───────────────────────────────────────────────
# ⚠️ ชื่อจังหวัดยาว ๆ ล้นขอบคอลัมน์ — วัดแล้วไกลสุดถึง x=153
#    "CHANGWAT NAKHON" ตัว N สุดท้ายอยู่ที่ x=150 พอดี
#    "จังหวัดพระนครศรีอยุธยา" สระท้ายอยู่ที่ x=153
#    ถ้าตั้ง 150 ตามที่ตาเห็น ตัวท้ายจะหายเงียบ ๆ กลายเป็น NAKHO / อยุธย
#    คอลัมน์ถัดไปเริ่มที่ 155.9 จึงตั้ง 155 ได้พอดี
C1_MAX = 155.0      # คอลัมน์ 1  ชื่อจังหวัด ทั้งไทยและอังกฤษ
C2_MAX = 340.0      # คอลัมน์ 2  อำเภอ/ตำบล ภาษาไทย
LV_SPLIT = 356.0    # คอลัมน์ 3  < นี้ = อำเภอ/เขต · >= นี้ = ตำบล/แขวง

TOP_SKIP = 55.0     # ข้ามเลขหน้า
# ⚠️ ไทยกับอังกฤษของแถวเดียวกันอยู่คนละ top ได้ ต่างกันถึง 6pt
#    เช่น หน้า 6  "แขวงสะพานสูง" y=663  แต่ "Khwaeng Saphan Sung" y=666
#    ถ้าจัดกลุ่มด้วยการปัดเศษจะแยกจากกัน ชื่อไทยเลยหายไป
#    แถวจริงห่างกัน ~21pt จึงรวมในระยะ 8pt ได้อย่างปลอดภัย
LINE_MERGE = 8.0    # top ห่างไม่เกินนี้ = บรรทัดเดียวกัน

THAI = re.compile(r"[ก-๛]")
SARA = ("\u0E32", "\u0E33")          # า  ำ


def render(chars):
    """ประกอบตัวอักษรเป็นข้อความ พร้อมแก้สระที่ฟอนต์เข้ารหัสผิด

    ⚠️ ห้ามเรียงตาม x0 — สระบน/ล่างของไทยใช้พิกัดเดียวกับตัวถัดไป
       เรียงตาม x แล้ว "อุบลราชธานี" จะกลายเป็น "อบุลราชธานี"
       และ "ชัยภูมิ" จะกลายเป็น "ชัยภูม ิ"
       pdfplumber คืน chars ตามลำดับใน content stream อยู่แล้ว ใช้ตามนั้น
    """
    out = []
    ghost = 0                   # จำนวนช่องว่างซ้อนทับที่ค้างอยู่
    n = len(chars)
    for i, c in enumerate(chars):
        t = c["text"]

        if t == " ":
            nxt = chars[i + 1] if i + 1 < n else None
            # ช่องว่างที่ x ตรงกับตัวถัดไปเป๊ะ = ร่องรอยอักขระที่ฟอนต์ทำหาย
            # ส่วนช่องว่างจริง (ย่อหน้า · คั่นคำ) มีระยะห่างชัดเจน
            if nxt is not None and abs(nxt["x0"] - c["x0"]) < 1.0:
                ghost += 1
            elif out and out[-1] != " ":
                out.append(" ")
            continue

        if ghost:
            if t in SARA:
                # ghost ตัวสุดท้ายคือสระอำ ที่เหลือคือวรรณยุกต์
                out.append("้" * (ghost - 1) + "ำ")
            else:
                out.append("้" * ghost)
                out.append(t)
            ghost = 0
            continue

        if t == "ำ" and "Bold" in c["fontname"]:
            out.append("า")   # ฟอนต์หนาเขียน า เป็น ำ
            continue

        out.append(t)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def strip_prefix(name, words):
    return split_prefix(name, words)[1]


def split_prefix(name, words):
    """คืน (คำนำหน้า, ชื่อ) — คำนำหน้าเก็บตามต้นฉบับเป๊ะ รวมตัวพิมพ์

    ⚠️ ไฟล์นี้ใส่คำนำหน้าไม่ครบทุกแถว
       กรุงเทพฯ     "แขวงชนะสงคราม" / "Khwaeng Chana Songkhram"
       ต่างจังหวัด   "บ้านป้อม"      / "Ban Pom"      <- ไม่มีคำนำหน้า
       ช่องที่ว่างคือของจริง ไม่ใช่ดึงพลาด
    """
    for w in sorted(words, key=len, reverse=True):
        if name.startswith(w):
            return w, name[len(w):].strip(" .")
    return "", name


def read_rows(pdf_path):
    """อ่าน PDF -> [(ชนิด, ไทย, อังกฤษ)] ตามลำดับที่ปรากฏในเล่ม"""
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for pi, page in enumerate(pdf.pages, 1):
            if pi % 50 == 0 or pi == total:
                print(f"  อ่านหน้า {pi}/{total}", flush=True)
            chars = [c for c in page.chars if c["top"] >= TOP_SKIP]
            # จัดกลุ่มบรรทัดตามระยะใกล้ ไม่ใช่ปัดเศษ
            tops = sorted({round(c["top"], 1) for c in chars})
            band, bands = [], []
            for t in tops:
                if band and t - band[-1] <= LINE_MERGE:
                    band.append(t)
                else:
                    band = [t]
                    bands.append(band)
            where = {t: i for i, b in enumerate(bands) for t in b}

            lines = defaultdict(list)
            for c in chars:
                lines[where[round(c["top"], 1)]].append(c)

            for key in sorted(lines):
                cs = lines[key]
                c1 = [c for c in cs if c["x0"] < C1_MAX]
                c2 = [c for c in cs if C1_MAX <= c["x0"] < C2_MAX]
                c3 = [c for c in cs if c["x0"] >= C2_MAX]

                if c1:
                    t = render(c1)
                    # ⚠️ ท้ายเล่มมีเชิงอรรถหลุดมาอยู่คอลัมน์แรก ตัดทิ้ง
                    if t and not t.startswith("*") and "เป็นการ" not in t:
                        rows.append(("col1", t, ""))
                if c2 or c3:
                    # ⚠️ ย่อหน้าในไฟล์นี้เป็น "อักขระช่องว่างจริง" ไม่ใช่ระยะห่าง
                    #    ถ้านับช่องว่างด้วย ทุกบรรทัดจะได้ x0 เท่ากันหมด (347.35)
                    #    จึงต้องหาอักขระตัวแรกที่ไม่ใช่ช่องว่าง
                    ink = [c["x0"] for c in c3 if c["text"].strip()]
                    x3 = min(ink) if ink else 999
                    lvl = "subdistrict" if x3 >= LV_SPLIT else "district"
                    rows.append((lvl, render(c2), render(c3)))
    return rows


def assemble(rows):
    """ประกอบเป็นตารางแบน — จังหวัด/อำเภอ ไหลลงมาให้ตำบลข้างล่าง

    ⚠️ ชื่อจังหวัดอังกฤษตัดบรรทัดในคอลัมน์แคบ เช่น  CHON / BURI
       จึงต้องสะสมชิ้นส่วนจนกว่าจะเจอชื่อไทยของจังหวัดถัดไป
    """
    prov_th = dist_th = dist_en = ""
    en_parts = defaultdict(list)          # ชื่อไทย -> ชิ้นส่วนอังกฤษ
    out = []

    for lvl, th, en in rows:
        if lvl == "col1":
            if THAI.search(th):
                prov_th = th          # เก็บตามต้นฉบับ รวมคำว่า "จังหวัด"
            elif prov_th:
                # ⚠️ ชิ้นส่วนอังกฤษแทรกสลับกับแถวอำเภอ/ตำบล ไม่ได้ต่อกันรวด
                #    จึงสะสมไว้ก่อน แล้วค่อยประกอบตอนจบ
                en_parts[prov_th].append(th)
            continue

        if lvl == "district":
            dist_th, dist_en = th, en      # เก็บตามต้นฉบับ รวมคำนำหน้า
            continue

        # ⚠️ ชื่ออังกฤษยาวเกินคอลัมน์จะตัดบรรทัด ท่อนต่อไม่มีชื่อไทยและ
        #    ไม่มีคำนำหน้า Khwaeng/Tambon — ต้องต่อกลับเข้าแถวก่อนหน้า
        #    ไม่งั้นจะได้แถวผี เช่น
        #      นิคมสร้างตนเองทุ่งโพธิ์ทะเล | Nikhom Sang Ton-eng Thung Pho
        #      (ว่าง)                      | Thale
        if (not th and en and out
                and not re.match(r"(Khwaeng|Tambon)\b", en)):
            out[-1]["subdistrict_en"] = (out[-1]["subdistrict_en"]
                                         + " " + en).strip()
            continue

        sub_th, sub_en = th, en        # เก็บตามต้นฉบับ รวมคำนำหน้า
        if not (sub_th or sub_en):
            continue
        out.append({"province_th": prov_th,
                    "district_th": dist_th, "district_en": dist_en,
                    "subdistrict_th": sub_th, "subdistrict_en": sub_en})

    # ประกอบชื่ออังกฤษของแต่ละจังหวัด — ชิ้นส่วนชุดเดิมวนซ้ำทุกครั้งที่ขึ้นหน้าใหม่
    # จึงตัดซ้ำโดยคงลำดับที่เจอครั้งแรกไว้
    prov_en = {}
    for th, parts in en_parts.items():
        seen, ordered = set(), []
        for x in parts:
            if x not in seen:
                seen.add(x)
                ordered.append(x)
        prov_en[th] = " ".join(ordered)      # เก็บ CHANGWAT ไว้ตามต้นฉบับ

    df = pd.DataFrame(out)
    df.insert(1, "province_en", df.province_th.map(prov_en).fillna(""))
    return df


def clean(df):
    for c in df.columns:
        df[c] = (df[c].astype(str)
                 .str.replace("\u200b", "", regex=False)
                 .str.replace(r"\s+", " ", regex=True).str.strip())
    # หมายเหตุ: คง "(BANGKOK)" ไว้ตามต้นฉบับ
    # ชื่อที่มีขีดกลางถูกตัดบรรทัดตรงขีด เช่น PHANG- NGA -> PHANG-NGA
    for c in [x for x in df.columns if x.endswith("_en")]:
        df[c] = df[c].str.replace(r"-\s+", "-", regex=True)
    # * ** คือเชิงอรรถในต้นฉบับ ไม่ใช่ส่วนของชื่อ
    # ⚠️ แต่จุดต้องเก็บไว้ — "จ.ป.ร." เป็นชื่อตำบลจริงใน จ.ระนอง
    for c in df.columns:
        df[c] = df[c].str.replace(r"\*+", "", regex=True).str.strip()
    # ⚠️ ท้ายเล่มมีคำอธิบายของราชบัณฑิตยสภาหลุดมาอยู่ในคอลัมน์ชื่อ
    #    ชื่อตำบลจริงยาวสุด 24 ตัวอักษร ข้อความที่ยาวกว่านั้นไม่ใช่ชื่อ
    NOTE = r"อักขรวิธี|ที่ถูกต้อง|หมายเหต|เป็นการ"
    for c in ("district_th", "subdistrict_th"):
        df.loc[df[c].str.contains(NOTE, regex=True, na=False), c] = ""
        df.loc[df[c].str.len() > 30, c] = ""
    df = df[(df.subdistrict_th != "") | (df.subdistrict_en != "")]
    return df.drop_duplicates().reset_index(drop=True)


def report(df, prov, dist):
    """ตรวจว่าผลที่ได้สมเหตุสมผล — จำนวนจริงของไทยคือ 77 จังหวัด"""
    print("\n── ผล ──")
    print(f"  จังหวัด      {len(prov):>6,}   (ของจริง 77)")
    print(f"  อำเภอ/เขต    {len(dist):>6,}   (ของจริง ~928)")
    print(f"  ตำบล/แขวง    {len(df):>6,}   (ของจริง ~7,436)")

    bad = []
    if len(prov) != 77:
        bad.append(f"จังหวัดได้ {len(prov)} ไม่ใช่ 77")
    dup = prov[prov.province_th.duplicated(keep=False)]
    if len(dup):
        bad.append(f"ชื่อจังหวัดไทยซ้ำ {dup.province_th.nunique()} ชื่อ")
    empty = df[(df.province_th == "") | (df.district_th == "")]
    if len(empty):
        bad.append(f"แถวที่จังหวัด/อำเภอว่าง {len(empty)}")
    if bad:
        print("\n🔴 ต้องตรวจ")
        for b in bad:
            print("   ·", b)
    else:
        print("\n✅ ตัวเลขตรงตามที่ควรเป็น")


SCHEMA = """-- ตารางที่อยู่ไทย · ทุกคอลัมน์ nvarchar รองรับ UTF-8
-- ที่มา: ราชบัณฑิตยสภา · ชื่อจังหวัดอำเภอตำบลเขตแขวง แก้ไข 14 ส.ค. 62

CREATE TABLE dbo.thai_admin (
    province_th     nvarchar(100) NOT NULL,
    province_en     nvarchar(100) NOT NULL,
    district_th     nvarchar(100) NOT NULL,
    district_en     nvarchar(100) NOT NULL,
    subdistrict_th  nvarchar(100) NOT NULL,
    subdistrict_en  nvarchar(100) NOT NULL
);

CREATE INDEX ix_thai_admin_prov ON dbo.thai_admin (province_th, district_th);
CREATE INDEX ix_thai_admin_sub  ON dbo.thai_admin (subdistrict_th);

-- นำเข้าด้วย BULK INSERT ต้องระบุ CODEPAGE ไม่งั้นภาษาไทยเพี้ยน
-- BULK INSERT dbo.thai_admin FROM 'thai_admin_full.csv'
-- WITH (FORMAT='CSV', FIRSTROW=2, CODEPAGE='65001', DATAFILETYPE='char');
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", nargs="?",
                    default=r"C:\Users\Sapon.S\Downloads"
                            r"\ชื่อจังหวัดอำเภอตำบลเขตแขวงแก้ไข14สค62.pdf")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    out = Path(a.out) if a.out else OUT
    out.mkdir(parents=True, exist_ok=True)

    print(f"อ่าน {a.pdf}", flush=True)
    df = clean(assemble(read_rows(a.pdf)))

    prov = (df[["province_th", "province_en"]].drop_duplicates()
            .sort_values("province_th").reset_index(drop=True))
    dist = (df[["province_th", "province_en", "district_th", "district_en"]]
            .drop_duplicates().sort_values(["province_th", "district_th"])
            .reset_index(drop=True))
    report(df, prov, dist)

    enc = "utf-8-sig"          # ให้ Excel เปิดภาษาไทยไม่เพี้ยน
    df.to_csv(out / "thai_admin_full.csv", index=False, encoding=enc)
    prov.to_csv(out / "thai_province.csv", index=False, encoding=enc)
    dist.to_csv(out / "thai_district.csv", index=False, encoding=enc)
    df[["province_th", "district_th", "subdistrict_th", "subdistrict_en"]] \
        .to_csv(out / "thai_subdistrict.csv", index=False, encoding=enc)
    (out / "thai_admin_schema.sql").write_text(SCHEMA, encoding="utf-8")

    with pd.ExcelWriter(out / "thai_admin.xlsx", engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="full", index=False)
        prov.to_excel(xw, sheet_name="province", index=False)
        dist.to_excel(xw, sheet_name="district", index=False)

    print(f"\nเขียนลง {out}")
    for f in sorted(out.iterdir()):
        print(f"  {f.name:28} {f.stat().st_size/1024:8.1f} KB")


if __name__ == "__main__":
    main()
