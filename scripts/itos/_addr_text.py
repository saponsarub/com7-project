# -*- coding: utf-8 -*-
"""แกะจังหวัด/อำเภอ/ตำบล ออกจากที่อยู่ข้อความก้อนเดียวของ ITOS

ใช้เป็น **ตัวสอบทาน** ผลที่ได้จากการ join ด้วยรหัสใน flood_waiver.py
ไม่ใช่แหล่งข้อมูลหลัก เพราะที่อยู่ข้อความว่าง 50,352 จาก 329,078 แถว

รูปแบบที่อยู่

    148 เธก.หมู่ที่ 8 ยี่ล้น วิเศษชัยชาญ อ่างทอง 14110
                      ^ตำบล  ^อำเภอ      ^จังหวัด ^ไปรษณีย์

'เธก.' คือ 'ม.' ที่ถูก decode เป็น CP874 แทน UTF-8 — ไม่กระทบเพราะไล่จากท้าย
"""
import re
import unicodedata
import unicodedata as _u
from pathlib import Path

import pandas as pd

GEO = Path(__file__).resolve().parents[1] / "geo" / "_out" / "dim_admin_flat.csv"
ZIP = re.compile(r"\s(\d{5})\s*$")
# บาง record ใส่รหัสไปรษณีย์ผิดความยาว (120120 · 4000 · 12)
# ถ้าไม่ตัดออกด้วยจะแกะจังหวัดไม่ออกทั้งแถว
TAIL_NUM = re.compile(r"\s\d+\s*$")


def norm(s):
    s = unicodedata.normalize("NFC", str(s)).strip()
    s = re.sub(r"^(จังหวัด|กิ่งอำเภอ|อำเภอ|เขต|ตำบล|แขวง|จ\.|อ\.|ต\.)", "", s).strip()
    s = s.replace("ำ", "ํา")
    s = re.sub(r"[็-๎]", "", s)
    return re.sub(r"[\s\-\.]", "", s)


def _tables():
    """สร้าง dict ค้นหา — ⚠️ คีย์ต้องเป็น tuple ทุกระดับ

    ถ้าระดับจังหวัดใช้ str ธรรมดา peel() จะหาไม่เจอเลยแม้แต่แถวเดียว
    (บั๊กที่เคยทำให้ได้ 0% แล้วดูเหมือนข้อมูลพัง)
    """
    g = pd.read_csv(GEO, encoding="utf-8-sig", dtype=str)
    g["kp"] = g.province_name_th.map(norm)
    g["kd"] = g.district_name_th.map(norm)
    g["ks"] = g.subdistrict_name_th.map(norm)
    prov, dist, sub = {}, {}, {}
    for kp, v in zip(g.kp, g.province_name_th):
        prov.setdefault((kp,), re.sub(r"^จังหวัด", "", v))
    for kp, kd, v in zip(g.kp, g.kd, g.district_name_th):
        dist.setdefault((kp, kd), re.sub(r"^(อำเภอ|เขต|กิ่งอำเภอ)", "", v))
    for kp, kd, ks, v in zip(g.kp, g.kd, g.ks, g.subdistrict_name_th):
        sub.setdefault((kp, kd, ks), re.sub(r"^(ตำบล|แขวง)", "", v))
    return prov, dist, sub


def peel(tokens, table, prefix=()):
    """ดึงชื่อที่ยาวสุดจากท้าย tokens ที่มีใน table

    ลองรวม 3 → 2 → 1 token เพราะบางชื่อถูกตัดด้วยช่องว่าง
    """
    for n in range(min(3, len(tokens)), 0, -1):
        k = norm("".join(tokens[-n:]))
        if prefix + (k,) in table:
            return table[prefix + (k,)], k, tokens[:-n]
    return None, None, tokens


def make_parser():
    """คืนฟังก์ชัน parse(addr) -> (จังหวัด, อำเภอ, ตำบล, ไปรษณีย์)"""
    prov, dist, sub = _tables()

    def parse(addr):
        if addr is None or pd.isna(addr):
            return None, None, None, None
        s = str(addr).strip()
        m = ZIP.search(s)
        zp = m.group(1) if m else None
        cut = m or TAIL_NUM.search(s)
        if cut:
            s = s[:cut.start()]
        tk = s.split()
        p, kp, tk = peel(tk, prov)
        if p is None:
            return None, None, None, zp
        dd, kd, tk = peel(tk, dist, (kp,))
        if dd is None:
            return p, None, None, zp
        sd, _, _ = peel(tk, sub, (kp, kd))
        return p, dd, sd, zp
    return parse
