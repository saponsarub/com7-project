# -*- coding: utf-8 -*-
"""สำรวจข้อมูลจริงเพื่อหาว่าควรเพิ่ม/ลด flag ตัวไหน

    python explore_flags.py --csv dim_item_itec.csv

ออก 4 ไฟล์ไว้ให้แยกมือต่อ
    flag_usage.csv        flag แต่ละตัวติดกี่แถว · ถูกใช้ในกฎไหม
    unmatched_words.csv   คำที่โผล่บ่อยแต่ไม่มี flag ไหนจับ
    accessory_words.csv   คำเด่นในกองที่ตกเป็น Accessory and Others
    flag_overlap.csv      flag ที่ติดคู่กันบ่อย = อาจซ้ำซ้อน

เอกสาร: COM7-Knowledge-Base/05_ETL/ITEC Category Model (ML).md
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import itec_mapper as M
import rules as R

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass          # Jupyter/Colab ไม่มีเมธอดนี้ และไม่ต้องใช้
HERE = Path(__file__).parent
OUT = HERE / "_out"
OUT.mkdir(exist_ok=True)
DUMP = "Accessory and Others"


def rule_flags():
    """flag ที่ rules.py อ้างถึงจริง"""
    import inspect
    src = inspect.getsource(R)
    used = set(re.findall(r'_f\(d, "(IS_[A-Za-z_]+)"\)', src))
    used |= set(re.findall(r'\("[A-Za-z ]+", "(IS_[A-Za-z_]+)"\)', src))
    return {f.lower() for f in used} | {"is_promotion", "is_demo_product", "is_gaming"}


def tokens(series):
    """ตัดคำหยาบ ๆ · ชื่อสินค้าส่วนใหญ่เป็นอังกฤษ ไทยตัดตามช่วงอักษร"""
    pat = re.compile(r"[a-z]{3,}|[฀-๿]{3,}")
    c = Counter()
    for s in series:
        c.update(pat.findall(str(s).lower()))
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(HERE / "_data" / "dim_item_itec.csv"))
    ap.add_argument("--top", type=int, default=120)
    args = ap.parse_args()

    rules_yaml = yaml.safe_load((HERE / "item_keywords.yaml").read_text(encoding="utf-8"))
    all_kw = {w.lower() for spec in rules_yaml.values() for w in spec["words"]}

    df = pd.read_csv(args.csv, encoding="utf-8-sig", dtype=str).fillna("")
    df = M.run(df, strict=True)
    df = df[df.ItemName.astype(str).str.strip() != ""].reset_index(drop=True)
    n = len(df)
    print(f"{n:,} แถว · {df.Main_Product_Dimension.nunique()} หมวด")

    used = rule_flags()
    flag_cols = [c for c in df.columns if c.startswith("IS_")]

    # ---------------------------------------------------------- 1 flag usage --
    rows = []
    for f in flag_cols:
        hit = int(df[f].sum())
        rows.append({"flag": f, "hits": hit, "pct": hit / n,
                     "used_in_rules": f.lower() in used,
                     "keywords": " | ".join(rules_yaml.get(f, {}).get("words", []))})
    usage = pd.DataFrame(rows).sort_values("hits", ascending=False)
    usage.to_csv(OUT / "flag_usage.csv", index=False, encoding="utf-8-sig")

    dead = usage[usage.hits == 0]
    rare = usage[(usage.hits > 0) & (usage.pct < 0.0005)]
    unused = usage[~usage.used_in_rules]
    print(f"\nflag ไม่เคยติดเลย {len(dead)} · ติดน้อยกว่า 0.05% {len(rare)} "
          f"· คำนวณแต่กฎไม่ใช้ {len(unused)}")
    if len(dead):
        print("  ไม่เคยติด:", ", ".join(dead.flag))

    print("\nflag ที่กฎไม่ใช้ แต่ติดเยอะ (ผู้สมัครเป็นหมวดใหม่)")
    cand = unused.sort_values("hits", ascending=False).head(12)
    print(cand[["flag", "hits", "pct"]].to_string(
        index=False, float_format=lambda v: f"{v:.2%}"))

    # ------------------------------------------------- 2 กองที่ตกเป็น dump --
    dump = df[df.Main_Product_Dimension == DUMP]
    print(f"\n{DUMP}: {len(dump):,} แถว ({len(dump)/n:.1%}) <- กองใหญ่ที่สุด")

    hit_in_dump = []
    for f in flag_cols:
        h = int(dump[f].sum())
        if h:
            hit_in_dump.append({"flag": f, "hits_in_dump": h,
                                "pct_of_dump": h / len(dump),
                                "used_in_rules": f.lower() in used})
    dd = pd.DataFrame(hit_in_dump).sort_values("hits_in_dump", ascending=False)
    print("\nflag ที่ติดในกอง Accessory (ตัวที่กฎไม่ใช้ = ควรพิจารณาแยกหมวด)")
    print(dd.head(15).to_string(index=False, float_format=lambda v: f"{v:.1%}"))

    # -------------------------------- 3 คำเด่นในกอง ที่ไม่มี keyword ไหนจับ --
    tok_dump = tokens(dump.ItemName)
    tok_all = tokens(df.ItemName)
    uncovered = [(w, c) for w, c in tok_dump.most_common(4000)
                 if not any(k in w or w in k for k in all_kw)]
    pd.DataFrame(uncovered[:args.top], columns=["word", "count_in_dump"]).to_csv(
        OUT / "accessory_words.csv", index=False, encoding="utf-8-sig")

    print(f"\nคำที่โผล่บ่อยในกอง Accessory แต่ยังไม่มี flag ไหนจับ (top 25)")
    for w, c in uncovered[:25]:
        print(f"   {w:<22}{c:>7,}   ({c/len(dump):.2%} ของกอง)")

    allun = [(w, c) for w, c in tok_all.most_common(6000)
             if not any(k in w or w in k for k in all_kw)]
    pd.DataFrame(allun[:args.top], columns=["word", "count_all"]).to_csv(
        OUT / "unmatched_words.csv", index=False, encoding="utf-8-sig")

    # ------------------------------------------------------ 4 flag ซ้ำซ้อน --
    pairs = []
    for i, a in enumerate(flag_cols):
        sa = df[a].to_numpy(dtype=bool)
        if sa.sum() < 50:
            continue
        for b in flag_cols[i + 1:]:
            sb = df[b].to_numpy(dtype=bool)
            if sb.sum() < 50:
                continue
            inter = int((sa & sb).sum())
            if inter == 0:
                continue
            j = inter / int((sa | sb).sum())
            if j > 0.5:
                pairs.append({"flag_a": a, "flag_b": b, "jaccard": j,
                              "both": inter, "a_only": int((sa & ~sb).sum()),
                              "b_only": int((~sa & sb).sum())})
    ov = pd.DataFrame(pairs).sort_values("jaccard", ascending=False)
    ov.to_csv(OUT / "flag_overlap.csv", index=False, encoding="utf-8-sig")
    print(f"\nคู่ flag ที่ซ้อนทับกันเกิน 50% : {len(ov)} คู่")
    if len(ov):
        print(ov.head(10).to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    print("\nไฟล์ที่ออก:")
    for f in ("flag_usage.csv", "accessory_words.csv",
              "unmatched_words.csv", "flag_overlap.csv"):
        print("  ", OUT / f)


if __name__ == "__main__":
    main()
