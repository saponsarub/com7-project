# -*- coding: utf-8 -*-
"""จัดหมวดสินค้า ITEC ด้วย pandas แทน CASE WHEN ใน SQL

    from mapper import run
    out = run(df)                       # strict = ได้ผลเท่าของเดิมทุกแถว
    out = run(df, strict=False)          # เปิด whole_word + แก้บั๊ก PC/Notebook

รันตรง ๆ เพื่อดูตัวอย่าง:
    python scripts/itec/category/mapper.py
เอกสาร: COM7-Knowledge-Base/05_ETL/ITEC Item Category Mapping (SQL to Python).md
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

import rules as R

sys.stdout.reconfigure(encoding="utf-8")

KEYWORDS = Path(__file__).parent / "item_keywords.yaml"
TEXT_COLS = ["ItemName", "CategoryName", "SubCategoryName"]

SQL_EXTRACT = """
SELECT ItemId, ItemName, CategoryName, SubCategoryName, [Model/Series], Brand
FROM   rpt.dim_item_itec
"""


def load_rules(path=KEYWORDS):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def normalize(s):
    """พิมพ์เล็ก · ตัดอักขระพิเศษ · ยุบช่องว่าง · เก็บ / & + . - ไว้เพราะ h/d ใช้"""
    return (s.fillna("").astype(str).str.lower()
             .str.replace(r"[^\w\s/&+.-]", " ", regex=True)
             .str.replace(r"\s+", " ", regex=True)
             .str.strip())


def build_search_text(df):
    """ต่อ 3 คอลัมน์เป็นข้อความเดียว · LIKE เดิม OR ทั้ง 3 คอลัมน์อยู่แล้ว 201 -> 67 ครั้ง

    คั่นด้วย | กันคำจากคนละคอลัมน์ต่อกันเป็นคำใหม่ เช่น power + bank
    """
    return (normalize(df[TEXT_COLS[0]]) + " | "
            + normalize(df[TEXT_COLS[1]]) + " | "
            + normalize(df[TEXT_COLS[2]]))


def to_pattern(words, whole_word):
    body = "|".join(re.escape(w) for w in words)
    return rf"\b(?:{body})\b" if whole_word else body


def build_flags(df, rules, strict=True):
    """สร้าง IS_* ทั้งหมด · strict = ไม่ใช้ whole_word เพื่อให้ตรงของเดิมเป๊ะ"""
    text = df["search_text"]
    flags = {name: text.str.contains(
                to_pattern(spec["words"], (not strict) and spec.get("whole_word", False)),
                regex=True, na=False).astype("int8")
             for name, spec in rules.items()}
    return pd.concat([df, pd.DataFrame(flags, index=df.index)], axis=1)


def apply_ordered(df, ordered, default):
    """np.select = CASE WHEN · เงื่อนไขแรกที่จริงชนะ"""
    conds = [cond(df).to_numpy() for _, cond in ordered]
    labels = [lbl for lbl, _ in ordered]
    return np.select(conds, labels, default=default)


def add_dimensions(df, fix_pc_notebook=False):
    f = lambda n: df[next(c for c in df.columns if c.lower() == n.lower())].astype(bool)

    df["Sale_Type"] = np.where(f("IS_Promotion"), "Promotion Sale", "Normal Sale")
    df["Product_Dimension"] = np.where(f("IS_Demo_Product"), "Demo Product", "Normal Product")
    df["Product_Purpose"] = np.where(f("IS_Gaming"), "Gaming", "Ordinary")

    df["Main_Product_Dimension"] = apply_ordered(
        df, R.main_rules(fix_pc_notebook), R.MAIN_DEFAULT)

    ordered = R.sub_rules()
    # None = PC/Notebook ที่ใช้ Product_Purpose นำหน้า ต้องคิดเป็นรายแถว
    dyn = df["Product_Purpose"] + "-" + df["Main_Product_Dimension"]
    conds = [c(df).to_numpy() for _, c in ordered]
    choices = [dyn.to_numpy() if lbl is None else np.full(len(df), lbl)
               for lbl, _ in ordered]
    df["Sub_Product_Dimension"] = np.select(
        conds, choices, default=df["Main_Product_Dimension"].to_numpy())
    return df


def add_fuzzy(df, vocab, cutoff=88):
    """เดาหมวดให้เฉพาะแถวที่ตกเป็น Accessory and Others · เก็บคะแนนไว้ตรวจย้อนเสมอ

    ห้ามเขียนทับ Main_Product_Dimension - keyword คือกฎที่คนตั้งใจ fuzzy คือการเดา
    """
    from rapidfuzz import fuzz, process

    todo = df.Main_Product_Dimension == R.MAIN_DEFAULT
    df[["fuzzy_guess", "fuzzy_term", "fuzzy_score"]] = None

    def guess(text):
        hit = process.extractOne(text, vocab.keys(),
                                 scorer=fuzz.token_set_ratio, score_cutoff=cutoff)
        return (vocab[hit[0]], hit[0], hit[1]) if hit else (None, None, None)

    if todo.any():
        got = df.loc[todo, "search_text"].map(guess)
        df.loc[todo, ["fuzzy_guess", "fuzzy_term", "fuzzy_score"]] = pd.DataFrame(
            got.tolist(), index=got.index).to_numpy()
    return df


def run(df, strict=True, rules=None):
    df = df.copy()
    df["search_text"] = build_search_text(df)
    df = build_flags(df, rules or load_rules(), strict=strict)
    return add_dimensions(df, fix_pc_notebook=not strict)


# ------------------------------------------------------------- ตัวอย่าง --
DEMO = pd.DataFrame({
    "ItemId": [1, 2, 3, 4, 5, 6, 7],
    "ItemName": ["iPhone 15 Pro Max 256GB", "Case iPhone 15 Clear",
                 "MacBook Air M3 13", "Logitech Gaming Mouse G502",
                 "Shipping Fee", "AppleCare+ for iPad", "Samsung SSD 980 1TB"],
    "CategoryName": ["Smartphone", "Accessory", "Notebook", "Mouse",
                     "Service", "Insurance", "Storage"],
    "SubCategoryName": ["Apple", "Case", "Apple", "Gaming", "Other", "Apple", "Internal"],
})

if __name__ == "__main__":
    out = run(DEMO)
    cols = ["ItemName", "Main_Product_Dimension", "Sub_Product_Dimension",
            "Product_Purpose", "IS_Pin", "IS_Case"]
    print(out[cols].to_string(index=False))
    print()
    strict_pin = int(out.IS_Pin.sum())
    loose = run(DEMO, strict=False)
    print(f"IS_Pin  strict={strict_pin}  whole_word={int(loose.IS_Pin.sum())}"
          "   <- 'Shipping' ไม่ควรติด IS_Pin")
