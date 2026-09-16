# -*- coding: utf-8 -*-
"""ทำนาย flag ด้วย ML แล้วคำนวณ 5 ตัวแปรต่อด้วยกฎเดิม

    ItemName -> TF-IDF -> 50 binary classifier -> flags -> rules.py -> 5 ตัวแปร

ML แทนที่แค่ขั้น keyword matching · กฎที่เหลือไม่แตะ ผลจึงไม่ขัดกันเอง

    python predict_all.py --csv dim_item_itec.csv -n 50000
    python predict_all.py --csv dim_item_itec.csv -n 50000 --save

เอกสาร: COM7-Knowledge-Base/05_ETL/ITEC Category Model (ML).md
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import f1_score
from sklearn.model_selection import cross_val_predict, train_test_split
from sklearn.svm import LinearSVC

sys.path.insert(0, str(Path(__file__).resolve().parent))
import itec_mapper as M
import rules as R
import type_platform as TP

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass          # Jupyter/Colab ไม่มีเมธอดนี้ และไม่ต้องใช้

HERE = Path(__file__).parent
OUT = HERE / "_out"
OUT.mkdir(exist_ok=True)
OUTPUTS = ["Sale_Type", "Product_Dimension", "Product_Purpose",
           "Main_Product_Dimension", "Sub_Product_Dimension"]

# flag ที่กฎใช้จริง · อีก 17 ตัวใน yaml ไม่มีผลต่อ 5 ตัวแปรนี้ จึงไม่ต้องเทรน
DIRECT_FLAGS = ["IS_Promotion", "IS_Demo_Product", "IS_Gaming"]


def needed_flags(df):
    """flag ที่ rules.py อ้างถึง + 3 ตัวที่แปลงเป็นตัวแปรตรง ๆ"""
    import inspect
    import re
    src = inspect.getsource(R)
    used = set(re.findall(r'_f\(d, "(IS_[A-Za-z_]+)"\)', src))
    used |= set(re.findall(r'\("[A-Za-z ]+", "(IS_[A-Za-z_]+)"\)', src))
    used |= set(DIRECT_FLAGS)
    have = {c.lower(): c for c in df.columns}
    return sorted({have[f.lower()] for f in used if f.lower() in have})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(HERE / "_data" / "dim_item_itec.csv"))
    ap.add_argument("-n", type=int, default=50000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--save", action="store_true", help="เซฟโมเดลลง joblib")
    ap.add_argument("--out", help="ออกไฟล์ผลลัพธ์ครบทุกแถว เช่น --out itec_categorized.csv")
    args = ap.parse_args()

    # ---------------------------------------------------- ข้อมูล + ความจริง --
    df = pd.read_csv(args.csv, encoding="utf-8-sig", dtype=str).fillna("")
    df = M.run(df, strict=True)                          # flags + 5 ตัวแปร จากกฎ
    df = df[df.ItemName.astype(str).str.strip() != ""].reset_index(drop=True)
    if args.n < len(df):
        df = df.sample(args.n, random_state=args.seed).reset_index(drop=True)
    print(f"ใช้ {len(df):,} แถว")

    flags = needed_flags(df)
    print(f"flag ที่ต้องทำนาย {len(flags)} ตัว (จาก 67 ใน yaml)")

    text = df.ItemName.astype(str).str.lower().to_numpy(dtype=object)
    tr, te = train_test_split(np.arange(len(df)), test_size=0.2,
                              random_state=args.seed)

    # ------------------------------------------------------- vectorize ครั้งเดียว --
    t0 = time.time()
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4),
                          min_df=2, max_features=50000)
    Xtr = vec.fit_transform(text[tr])
    Xte = vec.transform(text[te])
    print(f"TF-IDF {Xtr.shape[1]:,} feature · {time.time()-t0:.0f}s")

    # ------------------------------------------------ เทรน binary ต่อ flag --
    t0 = time.time()
    models, pred = {}, {}
    skipped = []
    for f in flags:
        ytr = df[f].to_numpy(dtype=int)[tr]
        if ytr.min() == ytr.max():            # flag ที่ไม่เคยเป็น 1 เลย เทรนไม่ได้
            skipped.append(f)
            pred[f] = np.full(len(te), ytr[0], dtype=np.int8)
            continue
        clf = LinearSVC()
        clf.fit(Xtr, ytr)
        models[f] = clf
        pred[f] = clf.predict(Xte).astype(np.int8)
    print(f"เทรน {len(models)} flag · {time.time()-t0:.0f}s"
          + (f" · ข้าม {len(skipped)} ตัวที่ไม่มีตัวอย่างบวก" if skipped else ""))

    per_flag = pd.DataFrame([
        {"flag": f, "f1": f1_score(df[f].to_numpy(dtype=int)[te], pred[f],
                                   zero_division=0),
         "positives": int(df[f].to_numpy(dtype=int)[te].sum())}
        for f in flags]).sort_values("f1")
    print("\nflag ที่ทำนายแย่สุด 8 ตัว")
    print(per_flag.head(8).to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    # -------------------------- เอา flag ที่ทำนายได้ ไปเข้ากฎเดิม ไม่แตะกฎ --
    rebuilt = df.iloc[te][["ItemName"]].copy().reset_index(drop=True)
    for f in flags:
        rebuilt[f] = pred[f]
    for c in df.columns:                       # flag ที่กฎไม่ใช้ เติม 0 กันพัง
        if c.startswith("IS_") and c not in rebuilt.columns:
            rebuilt[c] = 0
    rebuilt = M.add_dimensions(rebuilt, fix_pc_notebook=False)

    truth = df.iloc[te].reset_index(drop=True)

    print("\n" + "=" * 74)
    print(f"{'ตัวแปร':<26}{'ตรงกับกฎเดิม':>16}{'f1_macro':>12}{'ค่าที่เป็นไปได้':>18}")
    print("-" * 74)
    for col in OUTPUTS:
        same = (rebuilt[col].to_numpy(dtype=object)
                == truth[col].to_numpy(dtype=object)).mean()
        f1 = f1_score(truth[col].to_numpy(dtype=object),
                      rebuilt[col].to_numpy(dtype=object),
                      average="macro", zero_division=0)
        print(f"{col:<26}{same:>15.2%}{f1:>12.4f}{truth[col].nunique():>18}")
    print("=" * 74)

    # ตรวจว่าผลไม่ขัดกันเอง - Sub ต้องสอดคล้องกับ Main เสมอเพราะคำนวณจากกฎ
    bad = sum(1 for m, s in zip(rebuilt.Main_Product_Dimension,
                                rebuilt.Sub_Product_Dimension)
              if m in ("Smart Phone", "Tablet", "Smart Watch", "HeadSet&Earpiece")
              and not str(s).startswith(m))
    print(f"\nแถวที่ Sub ขัดกับ Main: {bad}  (ควรเป็น 0 เพราะ Sub คำนวณจาก Main)")

    if args.save:
        import joblib
        joblib.dump({"vectorizer": vec, "flag_models": models,
                     "flags": flags, "skipped": skipped},
                    OUT / "itec_flag_models.joblib")
        print(f"เซฟแล้ว -> {OUT / 'itec_flag_models.joblib'}")

    per_flag.to_csv(OUT / "flag_scores.csv", index=False, encoding="utf-8-sig")
    print(f"คะแนนรายflag -> {OUT / 'flag_scores.csv'}")

    if args.out:
        write_full(df, text, flags, vec, args)


def write_full(df, text, flags, vec, args):
    """ทำนายให้ครบทุกแถวแบบ out-of-fold แล้วเขียนไฟล์ผลลัพธ์

    out-of-fold = แต่ละแถวถูกทำนายโดยโมเดลที่ไม่เคยเห็นแถวนั้น
    ถ้าเทรนทั้งก้อนแล้วทำนายทั้งก้อน ตัวเลขจะสวยเกินจริง
    """
    print()
    print("ทำนายครบทุกแถวแบบ out-of-fold ...")
    t0 = time.time()
    X = vec.fit_transform(text)
    out = df[[c for c in ("ItemId", "ItemName", "CategoryName",
                          "SubCategoryName", "Brand") if c in df.columns]].copy()

    for f in flags:
        yf = df[f].to_numpy(dtype=int)
        if yf.min() == yf.max():
            out[f] = yf
            continue
        out[f] = cross_val_predict(LinearSVC(), X, yf, cv=5,
                                   n_jobs=-1).astype(np.int8)
    for c in df.columns:
        if c.startswith("IS_") and c not in out.columns:
            out[c] = 0
    out = M.add_dimensions(out, fix_pc_notebook=False)
    out = TP.add_columns(out)      # เพิ่ม Item_Type / Item_Platform / Type_Platform
    print(f"เสร็จใน {time.time()-t0:.0f}s")

    # ติดธงว่าแถวไหนต่างจากกฎเดิม - ไว้ให้คนตรวจว่าใครถูก
    for col in OUTPUTS:
        out[f"rule_{col}"] = df[col].to_numpy(dtype=object)
    out["differs"] = (out.Main_Product_Dimension.to_numpy(dtype=object)
                      != out.rule_Main_Product_Dimension.to_numpy(dtype=object))

    keep = ([c for c in ("ItemId", "ItemName") if c in out.columns] + OUTPUTS
            + ["Item_Type", "Item_Platform", "Type_Platform"]
            + [f"rule_{c}" for c in OUTPUTS] + ["differs"])
    out[keep].to_csv(args.out, index=False, encoding="utf-8-sig")
    n = int(out.differs.sum())
    print(f"เขียน {args.out} · {len(out):,} แถว · ต่างจากกฎเดิม {n:,} ({n/len(out):.2%})")
    print("คอลัมน์ผลลัพธ์: " + " · ".join(OUTPUTS))


if __name__ == "__main__":
    main()
