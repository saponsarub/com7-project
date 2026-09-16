# -*- coding: utf-8 -*-
"""แยกชื่อสินค้าเป็น ประเภท + แพลตฟอร์ม แล้วรวมเป็น label เดียว เช่น "Case iPhone"

ต่างจาก Main/Sub ของ SQL ตรงที่ **ประเภทมาก่อนเสมอ**
    SQL   iPhone 15 Case  ->  Main "Smart Phone" / Sub "Smart Phone Case"
    นี่    iPhone 15 Case  ->  "Case iPhone"

    python type_platform.py --csv dim_item_itec.csv --out type_platform.csv

เอกสาร: COM7-Knowledge-Base/05_ETL/ITEC Flag & Category Review Guide.md
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass          # Jupyter/Colab ไม่มีเมธอดนี้ และไม่ต้องใช้
HERE = Path(__file__).parent
OUT = HERE / "_out"
OUT.mkdir(exist_ok=True)

RULES_FILE = Path(__file__).parent / "type_platform.yaml"


def load_rules(path=RULES_FILE):
    """อ่านกฎจาก YAML · แก้กฎให้แก้ที่ไฟล์นั้น ไม่ต้องแตะโค้ดนี้"""
    import yaml
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    types = [(r["label"], r["words"], r.get("whole_word", False)) for r in d["types"]]
    plats = [(r["label"], r["words"], r.get("whole_word", False)) for r in d["platforms"]]
    dis = [(r["from"], r["words"], r["to"], r.get("whole_word", False))
           for r in d.get("disambiguate", [])]
    return types, plats, dis


TYPES, PLATFORMS, DISAMBIGUATE = load_rules()


def _pattern(words, whole_word=False):
    body = "|".join(re.escape(w) for w in words)
    return rf"(?:(?<![a-z0-9])(?:{body})(?![a-z0-9]))" if whole_word else body


def _first(s, table, default):
    return next((label for label, kw, ww in table
                 if re.search(_pattern(kw, ww), s)), default)


def classify(name, context=""):
    """คืน (Item_Type, Item_Platform)

    name    ชื่อสินค้า - ใช้ตัดสินหลัก
    context ข้อความเสริม (CategoryName/SubCategoryName) - ใช้แก้ความกำกวมเท่านั้น
            ไม่เอามาตัดสินตั้งแต่ต้น เพราะหมวดเดิมของ ITEC key ผิดเยอะ
    """
    s = str(name).lower()
    t = _first(s, TYPES, "Device")
    p = _first(s, PLATFORMS, "Generic")

    # ชื่อบอกไม่ได้ค่อยไปถามหมวดเดิม
    if context:
        c = str(context).lower()
        if t == "Device":
            t = _first(c, TYPES, "Device")
        if p == "Generic":
            p = _first(c, PLATFORMS, "Generic")

    both = s + " | " + str(context).lower()
    for old, kw, new, ww in DISAMBIGUATE:
        if t == old and re.search(_pattern(kw, ww), both):
            t = new
            break
    return t, p


def add_columns(df, col="ItemName", context_cols=("CategoryName", "SubCategoryName")):
    """context_cols=None = ใช้ชื่อสินค้าอย่างเดียว"""
    ctx = (df[[c for c in context_cols if c in df.columns]]
           .astype(str).agg(" ".join, axis=1) if context_cols else
           pd.Series("", index=df.index))
    tp = [classify(n, c) for n, c in zip(df[col], ctx)]
    df["Item_Type"] = [t for t, _ in tp]
    df["Item_Platform"] = [p for _, p in tp]
    # Device Generic ไม่มีความหมาย ปล่อยเป็น Device เฉย ๆ
    df["Type_Platform"] = np.where(
        df.Item_Platform == "Generic", df.Item_Type,
        df.Item_Type + " " + df.Item_Platform)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(HERE / "_data" / "dim_item_itec.csv"))
    ap.add_argument("--out")
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()

    df = pd.read_csv(args.csv, encoding="utf-8-sig", dtype=str).fillna("")
    ren = {"item_name": "ItemName", "item_id": "ItemId"}
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    df = df[df.ItemName.astype(str).str.strip() != ""].reset_index(drop=True)
    print(f"{len(df):,} แถว")

    df = add_columns(df)

    print(f"\nประเภท ({df.Item_Type.nunique()} ค่า)")
    print(df.Item_Type.value_counts().to_string())

    print(f"\nแพลตฟอร์ม ({df.Item_Platform.nunique()} ค่า)")
    print(df.Item_Platform.value_counts().head(12).to_string())

    print(f"\nรวมเป็น label เดียว ({df.Type_Platform.nunique()} ค่า) · top {args.top}")
    print(df.Type_Platform.value_counts().head(args.top).to_string())

    print("\nตัวอย่างของเสริมที่ระบุรุ่นได้")
    acc = df[(df.Item_Type != "Device") & (df.Item_Platform != "Generic")]
    print(acc[["ItemName", "Type_Platform"]].head(12).to_string(index=False))

    if args.out:
        keep = [c for c in ("ItemId", "ItemName") if c in df.columns] + \
               ["Item_Type", "Item_Platform", "Type_Platform"]
        df[keep].to_csv(args.out, index=False, encoding="utf-8-sig")
        print(f"\nเขียน {args.out}")


if __name__ == "__main__":
    main()
