# -*- coding: utf-8 -*-
"""Fine-tune backbone แล้วเทียบกับแบบแช่แข็ง บน test set ชุดเดียวกัน

    ItemName ─► [backbone] ─► เวกเตอร์ ─► [LinearSVC] ─► หมวด
                 ❄️ หรือ 🔥

ทำ 4 ขั้นในรอบเดียว
    1. แบ่ง train/test  (seed เดียวกับ benchmark_models.py จะได้เทียบกันได้)
    2. วัด baseline     backbone แช่แข็ง -> LinearSVC -> คะแนนบน test
    3. fine-tune        เฉพาะ train เท่านั้น ห้ามให้เห็น test
    4. วัดใหม่          backbone ที่ปรับแล้ว -> LinearSVC ตัวเดิม -> test ชุดเดิม

ต่างกันแค่ backbone จึงชี้ได้ว่า fine-tune ช่วยจริงหรือไม่

    python finetune.py -n 20000 --epochs 1
    python finetune.py -n 20000 --model bge          # ต้อง GPU

เอกสาร: COM7-Knowledge-Base/05_ETL/ITEC Model - Fine-tune Design.md
กฎจัดหมวดมาจาก ../category/ - รัน sync_rules.py ก่อนถ้าแก้กฎที่นั่น
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

HERE = Path(__file__).parent
OUT = HERE / "_out"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE))
import type_platform as TP

MODELS = {
    "mini": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "e5":   "intfloat/multilingual-e5-base",
    "bge":  "BAAI/bge-m3",
}


def need(pkg, mod=None):
    try:
        __import__(mod or pkg)
    except ImportError:
        print(f"ติดตั้ง {pkg} ...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], check=True)


def normalize(s):
    """ต้องเหมือน itec_mapper.normalize เป๊ะ ๆ ไม่งั้นข้อความตอน fine-tune
    ไม่ตรงกับตอนเทรน classifier และตอน predict จริง

    ก-๛ ต้องเขียนเป็นอักษรไทยจริง ห้ามใช้ escape แบบ backslash-u
    เพราะ pandas 3 ใช้ Arrow/RE2 ซึ่งไม่รองรับ
    """
    return (s.fillna("").astype(str).str.lower()
             .str.replace(r"[^\w\s/&+.\-ก-๛]", " ", regex=True)
             .str.replace(r"\s+", " ", regex=True)
             .str.strip())


def load(csv, n, seed, min_per_class, label):
    df = pd.read_csv(csv, encoding="utf-8-sig", dtype=str).fillna("")
    ren = {"item_name": "ItemName", "item_id": "ItemId", "category": "CategoryName",
           "sub_category": "SubCategoryName", "brand": "Brand"}
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    df = df[df.ItemName.astype(str).str.strip() != ""].reset_index(drop=True)
    df = TP.add_columns(df)

    # triplet loss ต้องมีอย่างน้อย 2 ตัวอย่างต่อหมวดในหนึ่ง batch จึงตัดหมวดบางไป
    vc = df[label].value_counts()
    df = df[df[label].isin(vc[vc >= min_per_class].index)].reset_index(drop=True)
    if n < len(df):
        df = pd.concat([g.sample(max(int(len(g) * n / len(df)), min_per_class),
                                 random_state=seed, replace=False)
                        if len(g) >= min_per_class else g
                        for _, g in df.groupby(label)]).reset_index(drop=True)
    print(f"{len(df):,} แถว · {df[label].nunique()} หมวด · label={label} "
          f"(ตัดหมวดที่มีน้อยกว่า {min_per_class} แถวออกแล้ว)")
    return df


def score(emb, texts, y, tr, te, tag):
    t = time.time()
    X = np.asarray(emb.encode(texts, batch_size=64, normalize_embeddings=True,
                              show_progress_bar=True))
    clf = LinearSVC(C=1.0, class_weight="balanced").fit(X[tr], y[tr])
    p = clf.predict(X[te])
    acc, f1 = accuracy_score(y[te], p), f1_score(y[te], p, average="macro")
    print(f"  {tag:22} acc={acc:.4f}  f1_macro={f1:.4f}  ({time.time()-t:.0f}s)")
    return acc, f1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(HERE / "_data" / "dim_item_itec.csv"))
    ap.add_argument("-n", type=int, default=20000)
    ap.add_argument("--model", default="mini", choices=list(MODELS))
    ap.add_argument("--epochs", type=float, default=1)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max-seq", type=int, default=64,
                    help="ชื่อสินค้าสั้น ตัดสั้นช่วยให้เร็วและประหยัด VRAM มาก")
    ap.add_argument("--label", default="Item_Type",
                    choices=["Type_Platform", "Item_Type", "Item_Platform"],
                    help="Item_Type มีแค่ ~20 หมวด ตัวอย่างต่อหมวดเยอะกว่า เห็นผล fine-tune ชัดกว่า")
    ap.add_argument("--min-per-class", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    need("sentence-transformers", "sentence_transformers")
    need("datasets")
    need("accelerate")

    import torch
    from datasets import Dataset
    from sentence_transformers import (SentenceTransformer, SentenceTransformerTrainer,
                                       SentenceTransformerTrainingArguments)
    from sentence_transformers.losses import BatchAllTripletLoss
    from sentence_transformers.training_args import BatchSamplers

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    name = MODELS[args.model]
    print(f"backbone={name} · device={dev}\n")

    df = load(Path(args.csv), args.n, args.seed, args.min_per_class, args.label)
    texts = normalize(df.ItemName).tolist()
    y = df[args.label].to_numpy(dtype=object)

    # แบ่งครั้งเดียว ใช้ชุดเดียวกันทั้งก่อนและหลัง fine-tune
    tr, te = train_test_split(np.arange(len(df)), test_size=0.2,
                              random_state=args.seed, stratify=y)
    print(f"train {len(tr):,} · test {len(te):,}\n")

    # ---------------------------------------------------------- 1 baseline --
    print("① baseline · backbone แช่แข็ง")
    base = SentenceTransformer(name, device=dev)
    base.max_seq_length = args.max_seq
    acc0, f10 = score(base, texts, y, tr, te, "frozen")

    # ------------------------------------------------- 2 fine-tune เฉพาะ train --
    print(f"\n② fine-tune · {args.epochs} epoch · batch {args.batch} · lr {args.lr}")
    codes, uniq = pd.factorize(pd.Series(y[tr]))          # triplet loss ใช้ label เป็น int
    ds = Dataset.from_dict({"sentence": [texts[i] for i in tr],
                            "label": codes.tolist()})

    model = SentenceTransformer(name, device=dev)
    model.max_seq_length = args.max_seq
    loss = BatchAllTripletLoss(model)

    targs = SentenceTransformerTrainingArguments(
        output_dir=str(OUT / "ft-ckpt"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        learning_rate=args.lr,
        warmup_ratio=0.1,
        fp16=(dev == "cuda"),
        # จัด batch ให้มีหลายตัวอย่างต่อหมวด ไม่งั้นสร้าง triplet ไม่ได้
        batch_sampler=BatchSamplers.GROUP_BY_LABEL,
        logging_steps=100,
        save_strategy="no",
        report_to=[],
    )
    t0 = time.time()
    SentenceTransformerTrainer(model=model, args=targs,
                               train_dataset=ds, loss=loss).train()
    print(f"  ใช้เวลา {time.time()-t0:.0f}s")

    outdir = OUT / f"{args.model}-{args.label}-finetuned"
    model.save(str(outdir))
    print(f"  เซฟ backbone -> {outdir}")

    # --------------------------------------------- 3 วัดใหม่ ด้วย test ชุดเดิม --
    print("\n③ หลัง fine-tune")
    acc1, f11 = score(model, texts, y, tr, te, "fine-tuned")

    # ------------------------------------------------------------- สรุป --
    d_acc, d_f1 = acc1 - acc0, f11 - f10
    print("\n" + "=" * 62)
    print(f"{'':22}{'accuracy':>12}{'f1_macro':>12}")
    print(f"{'frozen':22}{acc0:>12.4f}{f10:>12.4f}")
    print(f"{'fine-tuned':22}{acc1:>12.4f}{f11:>12.4f}")
    print(f"{'ต่าง':22}{d_acc:>+12.4f}{d_f1:>+12.4f}")
    print("=" * 62)
    print("-> fine-tune ช่วยจริง คุ้มที่จะใช้" if d_f1 > 0.01 else
          "-> ไม่คุ้ม · label ยังไม่สะอาดพอ ใช้แบบแช่แข็งต่อไป")

    pd.DataFrame([{"model": name, "label": args.label, "n": len(df), "epochs": args.epochs,
                   "acc_frozen": acc0, "f1_frozen": f10,
                   "acc_ft": acc1, "f1_ft": f11,
                   "d_acc": d_acc, "d_f1": d_f1}]).to_csv(
        OUT / "finetune_result.csv", index=False, encoding="utf-8-sig")
    print(f"เซฟผล -> {OUT / 'finetune_result.csv'}")


if __name__ == "__main__":
    main()
