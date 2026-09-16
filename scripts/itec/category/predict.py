# -*- coding: utf-8 -*-
"""เอาโมเดลที่เทรนแล้วมาทำนายชื่อสินค้าใหม่

    python predict.py "iPhone 15 Case Clear" "เคส Samsung S24"
    python predict.py --csv new_items.csv --col ItemName --out _out/predicted.csv
    python predict.py "Logitech MX Master 3S" --top 5

โมเดลมาจาก Cell 11 ของ itec_recategorization.ipynb (model1_itemname.joblib)
ทำนายจาก ItemName อย่างเดียว - ตรงกับสภาพจริงตอนมีสินค้าใหม่เข้ามา

เอกสาร: COM7-Knowledge-Base/05_ETL/ITEC Model - Notebook Explained.md
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

HERE = Path(__file__).parent
OUT = HERE / "_out"
sys.path.insert(0, str(HERE))
import itec_mapper as M          # ใช้ normalize ตัวเดียวกับตอนเทรน

DEFAULT_MODEL = OUT / "model1_itemname.joblib"


class ItemCategorizer:
    """ห่อ normalize + embedder + classifier ไว้ในตัวเดียว

        cat = ItemCategorizer()
        cat.predict(["iPhone 15 Case Clear"])       -> ['Case iPhone']
        cat.predict_df(["iPhone 15 Case"], top=3)   -> DataFrame พร้อมความมั่นใจ

    backbone โหลดตอนเรียกใช้ครั้งแรก (lazy) ไม่ใช่ตอนสร้าง
    จะได้ไม่ต้องรอโหลดโมเดล 2 GB ถ้าแค่อยากดูว่ามีหมวดอะไรบ้าง
    """

    def __init__(self, model_path=None):
        import joblib
        p = Path(model_path or DEFAULT_MODEL)
        if not p.exists():
            found = sorted(HERE.rglob("model1_itemname.joblib"))
            raise FileNotFoundError(
                f"ไม่พบ {p}" + (f" · เจอที่ {found[0]}" if found else
                                " · ยังไม่ได้เทรน รัน Cell 11 ในโน้ตบุ๊กก่อน"))
        self.meta = joblib.load(p)
        self.clf = self.meta["clf"]
        self.backbone_name = self.meta["backbone"]
        self.label_col = self.meta.get("label_col", "?")
        self._emb = None

    @property
    def embedder(self):
        if self._emb is None:
            from sentence_transformers import SentenceTransformer
            print(f"โหลด backbone {self.backbone_name} ...")
            self._emb = SentenceTransformer(self.backbone_name)
        return self._emb

    @property
    def classes_(self):
        return self.clf.classes_

    def _vec(self, names):
        txt = M.normalize(pd.Series(list(names))).tolist()   # normalize เหมือนตอนเทรน
        return txt, np.asarray(self.embedder.encode(
            txt, normalize_embeddings=True, batch_size=64,
            show_progress_bar=len(txt) > 500))

    def predict(self, names):
        """รับ list ของชื่อสินค้า คืน list ของหมวด"""
        return self.clf.predict(self._vec(names)[1])

    def proba(self, names):
        """คืน (คลาส, ความน่าจะเป็น) · SVC ใช้ softmax บน margin"""
        _, X = self._vec(names)
        if hasattr(self.clf, "predict_proba"):
            return self.classes_, self.clf.predict_proba(X)
        d = self.clf.decision_function(X).reshape(len(X), -1)
        e = np.exp(d - d.max(axis=1, keepdims=True))
        return self.classes_, e / e.sum(axis=1, keepdims=True)

    def predict_df(self, names, top=1):
        names = list(names)
        txt, X = self._vec(names)
        cls, prob = self.classes_, None
        if hasattr(self.clf, "predict_proba"):
            prob = self.clf.predict_proba(X)
        else:
            d = self.clf.decision_function(X).reshape(len(X), -1)
            e = np.exp(d - d.max(axis=1, keepdims=True))
            prob = e / e.sum(axis=1, keepdims=True)
        order = np.argsort(-prob, axis=1)[:, :top]
        rows = []
        for i, nm in enumerate(names):
            r = {"ItemName": nm, "normalized": txt[i]}
            for k in range(top):
                j = order[i, k]
                suf = "" if k == 0 else f"_{k+1}"
                r[f"pred{suf}"] = cls[j]
                r[f"conf{suf}"] = round(float(prob[i, j]), 4)
            rows.append(r)
        return pd.DataFrame(rows)

    def __repr__(self):
        return (f"ItemCategorizer(backbone={self.backbone_name!r}, "
                f"label={self.label_col!r}, classes={len(self.classes_)})")


def build_pipeline(model_path=None):
    """แบบ sklearn Pipeline · pipe.predict(["ชื่อสินค้า"]) ได้เลย"""
    from sklearn.base import BaseEstimator, TransformerMixin
    from sklearn.pipeline import Pipeline

    cat = ItemCategorizer(model_path)

    class TextToVector(BaseEstimator, TransformerMixin):
        def fit(self, X, y=None):
            return self
        def transform(self, X):
            return cat._vec(X)[1]

    return Pipeline([("embed", TextToVector()), ("clf", cat.clf)])


def load_model(path):
    import joblib
    from sentence_transformers import SentenceTransformer

    p = Path(path)
    if not p.exists():
        cands = sorted(HERE.rglob("model1_itemname.joblib"))
        sys.exit(f"ไม่พบ {p}\n"
                 + (f"เจอที่อื่น: {[str(c) for c in cands]}" if cands else
                    "ยังไม่ได้เทรน - รัน Cell 11 ในโน้ตบุ๊กก่อน"))

    m = joblib.load(p)
    name = m["backbone"]
    # backbone อาจเป็น path ของตัวที่ fine-tune แล้ว - เทียบกับที่เก็บไว้
    if Path(name).exists() or "/" in name or "\\" in name:
        name = str(Path(name)) if Path(name).exists() else name
    print(f"โมเดล   {p.name}")
    print(f"backbone {name}")
    print(f"label    {m.get('label_col','?')} · {len(m.get('classes',[]))} หมวด\n")
    return m, SentenceTransformer(name)


def predict(names, model, embedder, top=1):
    """คืน DataFrame · ItemName + หมวดที่ทำนาย + ความมั่นใจ"""
    clf = model["clf"]
    text = M.normalize(pd.Series(list(names))).tolist()
    X = np.asarray(embedder.encode(text, normalize_embeddings=True,
                                   batch_size=64, show_progress_bar=len(text) > 500))

    # LinearSVC ไม่มี predict_proba - ใช้ softmax บน margin เหมือนตอนเทรน
    if hasattr(clf, "predict_proba"):
        prob = clf.predict_proba(X)
    else:
        d = clf.decision_function(X)
        d = d.reshape(len(text), -1)
        e = np.exp(d - d.max(axis=1, keepdims=True))
        prob = e / e.sum(axis=1, keepdims=True)

    order = np.argsort(-prob, axis=1)[:, :top]
    rows = []
    for i, name in enumerate(names):
        r = {"ItemName": name, "normalized": text[i]}
        for k in range(top):
            j = order[i, k]
            suf = "" if k == 0 else f"_{k+1}"
            r[f"pred{suf}"] = clf.classes_[j]
            r[f"conf{suf}"] = round(float(prob[i, j]), 4)
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help="ชื่อสินค้าที่จะทำนาย")
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--csv", help="ทำนายทั้งไฟล์แทนการพิมพ์ทีละชื่อ")
    ap.add_argument("--col", default="ItemName")
    ap.add_argument("--out", help="เขียนผลลง CSV")
    ap.add_argument("--top", type=int, default=1, help="แสดงกี่อันดับ")
    args = ap.parse_args()

    if args.csv:
        df = pd.read_csv(args.csv, encoding="utf-8-sig", dtype=str).fillna("")
        ren = {"item_name": "ItemName"}
        df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
        assert args.col in df.columns, f"ไม่พบคอลัมน์ {args.col} · ที่มี {list(df.columns)}"
        names = df[args.col].astype(str).tolist()
    elif args.names:
        names = args.names
    else:
        names = ["iPhone 15 Pro Max 256GB", "iPhone 15 Case Clear", "เคส Samsung S24",
                 "Logitech MX Master 3S", "CASE ATX 002",
                 "Power Supply Plenty ATX 500W", "ค่าบริการ Restore เครื่อง"]
        print("ไม่ได้ระบุชื่อสินค้า - ใช้ตัวอย่างในตัว\n")

    model, embedder = load_model(args.model)
    res = predict(names, model, embedder, args.top)

    cols = [c for c in res.columns if c != "normalized"]
    print(res[cols].to_string(index=False))

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(args.out, index=False, encoding="utf-8-sig")
        print(f"\nเขียน {args.out} · {len(res):,} แถว")

    if args.top == 1 and len(res) > 20:
        lo = res[res.conf < 0.5]
        print(f"\nความมั่นใจต่ำกว่า 0.5: {len(lo):,} แถว ({len(lo)/len(res):.1%}) "
              "<- ควรให้คนตรวจ")


if __name__ == "__main__":
    main()
