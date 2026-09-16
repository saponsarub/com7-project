# -*- coding: utf-8 -*-
"""เทียบ backbone หลายตัวบน subset เพื่อตัดสินว่าต้องใช้ GPU จริงไหม

label ที่ใช้วัดมาจาก rule-based เดิม (itec_mapper.run) ไม่ใช่ ground truth
ตอบได้แค่ว่า "โมเดลไหนจับ pattern เดียวกับกฎเดิมได้ดีกว่ากัน"

    pip install sentence-transformers scikit-learn
    python benchmark_models.py --csv dim_item_itec.csv -n 5000

เอกสาร: COM7-Knowledge-Base/05_ETL/ITEC Category Model (ML).md
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.model_selection import cross_validate
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import make_pipeline
from sklearn.svm import LinearSVC

sys.path.insert(0, str(Path(__file__).resolve().parent))
import itec_mapper as M
import type_platform as TP

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass          # Jupyter/Colab ไม่มีเมธอดนี้ และไม่ต้องใช้

FULL_ROWS = 216_009
SCORING = ("accuracy", "f1_macro")

# ตัว classifier ที่เอามาเทียบบน feature ชุดเดียวกัน
# proba = มี predict_proba ไหม · Cell 12 ของ notebook ต้องใช้หาของที่ key ผิด
CLASSIFIERS = [
    ("LogisticRegression", lambda: LogisticRegression(max_iter=2000, n_jobs=-1), True),
    ("LinearSVC",          lambda: LinearSVC(), False),
    ("SGD log_loss",       lambda: SGDClassifier(loss="log_loss", max_iter=2000,
                                                 tol=1e-3, n_jobs=-1), True),
    ("ComplementNB",       lambda: ComplementNB(), True),
]

MODELS = [
    ("MiniLM-L12-v2", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
    ("e5-base",       "intfloat/multilingual-e5-base"),
    ("bge-m3",        "BAAI/bge-m3"),
]


def load(csv, n, seed, label='Main_Product_Dimension'):
    df = pd.read_csv(csv, encoding="utf-8-sig", dtype=str).fillna("")
    print(f"อ่าน {len(df):,} แถว")

    df = M.run(df, strict=True)                         # label จากกฎเดิม
    df = TP.add_columns(df)                             # + Type_Platform
    df = df[df.ItemName.astype(str).str.strip() != ""]  # ว่าง = embed แล้วได้ขยะ

    # สุ่มคงสัดส่วนหมวด · ไม่ใช้ groupby.apply เพราะ pandas 3 ตัดคอลัมน์ที่ group ออก
    frac = min(n / len(df), 1.0)
    s = pd.concat([g.sample(max(int(len(g) * frac), 1), random_state=seed)
                   for _, g in df.groupby(label)])
    print(f"สุ่มมา {len(s):,} แถว · {s[label].nunique()} หมวด · label={label}")
    print(s[label].value_counts().head(20).to_string())
    return s.reset_index(drop=True)


def evaluate(est, X, y, label, embed_sec, n_rows, dim):
    t = time.time()
    cv = cross_validate(est, X, y, cv=5, n_jobs=-1, scoring=SCORING)
    return {
        "model": label,
        "accuracy": cv["test_accuracy"].mean(),
        "sd": cv["test_accuracy"].std(),
        "f1_macro": cv["test_f1_macro"].mean(),
        "embed_sec": embed_sec,
        "fit_sec": time.time() - t,
        "full_hours": embed_sec / n_rows * FULL_ROWS / 3600 if embed_sec else 0.0,
        "dim": dim,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(HERE / "_data" / "dim_item_itec.csv"))
    ap.add_argument("-n", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--label", default="Main_Product_Dimension",
                    choices=["Main_Product_Dimension", "Sub_Product_Dimension",
                             "Type_Platform", "Item_Type"],
                    help="คอลัมน์ที่ใช้เป็น label")
    ap.add_argument("--skip-embed", action="store_true", help="รัน TF-IDF อย่างเดียว")
    ap.add_argument("--compare-clf", action="store_true",
                    help="เทียบ classifier หลายตัวบน TF-IDF ชุดเดียวกัน")
    args = ap.parse_args()

    df = load(Path(args.csv), args.n, args.seed, args.label)
    # ต้องเป็น ndarray · pandas 3 คืน ArrowExtensionArray ที่ sklearn index ไม่ได้
    text = np.asarray(df.ItemName.astype(str).str.lower().tolist(), dtype=object)
    y = df[args.label].to_numpy(dtype=object)
    rows = []

    # baseline ที่ไม่ต้องโหลดโมเดลอะไรเลย
    tfidf = make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4),
                        min_df=2, max_features=50000),
        LogisticRegression(max_iter=2000))
    r = evaluate(tfidf, text, y, "TF-IDF + LogisticRegression", 0, len(text), 0)
    r["predict_proba"] = True
    rows.append(r)
    print(f"\nTF-IDF  acc={r['accuracy']:.4f}  f1_macro={r['f1_macro']:.4f}")

    if args.compare_clf:
        vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4),
                              min_df=2, max_features=50000)
        for name, make, has_proba in CLASSIFIERS[1:]:      # ตัวแรกทำไปแล้วข้างบน
            try:
                r = evaluate(make_pipeline(vec, make()), text, y,
                             f"TF-IDF + {name}", 0, len(text), 0)
                r["predict_proba"] = has_proba
                rows.append(r)
                print(f"{name:22} acc={r['accuracy']:.4f}  f1={r['f1_macro']:.4f}  "
                      f"{r['fit_sec']:.0f}s  proba={'yes' if has_proba else 'NO'}")
            except Exception as e:
                print(f"{name} ล้มเหลว: {type(e).__name__}: {e}")

    if not args.skip_embed:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print("\nไม่มี sentence-transformers — ข้ามส่วน embedding")
            print("  pip install sentence-transformers")
            SentenceTransformer = None

        if SentenceTransformer:
            for label, name in MODELS:
                try:
                    print(f"\nโหลด {label} ...")
                    m = SentenceTransformer(name)
                    t = time.time()
                    X = np.asarray(m.encode(list(text), batch_size=64,
                                            show_progress_bar=True,
                                            normalize_embeddings=True))
                    sec = time.time() - t
                    clf = LogisticRegression(max_iter=2000, n_jobs=-1)
                    r = evaluate(clf, X, y, label, sec, len(text), X.shape[1])
                    rows.append(r)
                    print(f"{label}  acc={r['accuracy']:.4f}  f1={r['f1_macro']:.4f}  "
                          f"embed {sec:.0f}s -> ชุดเต็มราว {r['full_hours']:.1f} ชม.")
                    del m, X
                except Exception as e:
                    print(f"{label} ล้มเหลว: {type(e).__name__}: {e}")

    out = pd.DataFrame(rows).sort_values("f1_macro", ascending=False)
    print("\n" + "=" * 84)
    print(out.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print("=" * 84)

    best = out.iloc[0]
    cheap = out[out.model.str.contains("MiniLM|TF-IDF")]
    if len(cheap):
        gap = best.f1_macro - cheap.f1_macro.max()
        print(f"\nดีสุด {best.model}  f1_macro={best.f1_macro:.4f}")
        print(f"ตัวที่รันบน CPU ได้ ต่างจากตัวดีสุด {gap:.4f} ({gap*100:.2f} จุด)")
        print("-> ต่างน้อยกว่า 2 จุด ใช้ CPU ได้ ไม่ต้องรอ GPU"
              if gap < 0.02 else "-> ต่างเกิน 2 จุด คุ้มที่จะรอ GPU")

    out.to_csv(Path(__file__).parent / "benchmark_result.csv",
               index=False, encoding="utf-8-sig")
    print(f"\nเซฟผล -> {Path(__file__).parent / 'benchmark_result.csv'}")


if __name__ == "__main__":
    main()
