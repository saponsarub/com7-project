# -*- coding: utf-8 -*-
"""จัดหมวดสินค้า ITEC — สคริปต์บรรทัดคำสั่ง ไม่ต้องเปิดโน้ตบุ๊ก

ใช้กฎจาก rules.yaml ซึ่งขึ้น git ไปด้วย เครื่องปลายทางจึงรันได้เลย

    python run.py                      ประมวลผลทั้งชุด -> _out/
    python run.py --source db          ดึงข้อมูลสดจากฐานแทนการอ่าน csv
    python run.py --gold 300           สุ่ม gold set ให้คนตรวจ
    python run.py --score              วัดผลกับ gold_set_checked.csv
    python run.py --sample 5000        ลองกับข้อมูลบางส่วนก่อน

ตั้งเครื่องใหม่ -> COM7-Knowledge-Base/08_Reference/Environment Setup.md
แก้กฎ          -> Cell 3 ของ itec_dimension.ipynb เท่านั้น (rules.yaml ถูกเขียนทับ)
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))          # ให้ import db ได้
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")      # ไม่งั้น cp874 พังกับภาษาไทย

import dimension as D                             # noqa: E402

DATA = HERE / "_data" / "dim_item_itec.csv"
OUT = HERE / "_out"
GOLD_BLANK = OUT / "gold_set_check.csv"
GOLD_DONE = OUT / "gold_set_checked.csv"

SQL = """
SELECT ItemId, ItemName, CategoryName, SubCategoryName,
       [Model/Series] AS ModelSeries, Brand
FROM   rpt.dim_item_itec
"""

# คีย์สำรองเวลา gold set รุ่นเก่าไม่มี ItemId
# ⚠️ ItemName อย่างเดียวใช้ไม่ได้ — "(Part) LCD" มี 60 แถว
FALLBACK_KEY = ["ItemName", "CategoryName", "SubCategoryName", "Brand"]


def load(source, sample=0):
    if source == "db":
        import db
        print("ดึงจาก rpt.dim_item_itec ...", flush=True)
        df = db.query("itec", SQL)
    else:
        if not DATA.exists():
            sys.exit(f"ไม่พบ {DATA}\n"
                     f"  · export จาก rpt.dim_item_itec มาวางไว้ หรือ\n"
                     f"  · ใช้ --source db เพื่อดึงสด (ต้องตั้ง MIS_USER / MIS_PWD)")
        df = pd.read_csv(DATA, encoding="utf-8-sig", dtype=str)
    df = df.fillna("")
    if sample:
        df = df.sample(min(sample, len(df)), random_state=42).reset_index(drop=True)
    print(f"{len(df):,} แถว")
    return D.normalize_columns(df)


def run(df, verbose=True):
    df = D.add_columns(df, verbose=verbose)
    return D.compose(df)


def report(df):
    n = len(df)
    print("\n── สุขภาพของกฎ ──")
    print(D.health(df).to_string(index=False))
    vc = df.Main_Product_Dimension.value_counts()
    print(f"\n── Main {len(vc)} หมวด · Sub {df.Sub_Product_Dimension.nunique()} ──")
    print(pd.DataFrame({"n": vc, "%": (vc / n * 100).round(1)}).to_string())

    # กติกาที่ต้องไม่พังเด็ดขาด
    bad = df.groupby("Sub_Product_Dimension").Main_Product_Dimension.nunique()
    bad = bad[bad > 1]
    print("\nSub ที่ชี้ไปหลาย Main:", "ไม่มี" if bad.empty else bad.to_dict())


def save(df):
    OUT.mkdir(exist_ok=True)
    KEEP = ["ItemId", "ItemName", "CategoryName", "SubCategoryName", "Brand",
            "Item_Type", "Item_Host", "Item_Platform", "by_category",
            "IS_Promotion", "Promotion_Source", "IS_Product",
            "Sale_Type", "Product_Dimension", "Product_Purpose",
            "Main_Product_Dimension", "Sub_Product_Dimension"]
    out = df[[c for c in KEEP if c in df.columns]]
    p = OUT / "itec_dimension.csv"
    out.to_csv(p, index=False, encoding="utf-8-sig")
    print(f"\nเขียน {p}  ({len(out):,} แถว · {len(out.columns)} คอลัมน์)")
    try:
        out.to_parquet(OUT / "itec_dimension.parquet", index=False)
        print(f"เขียน {OUT / 'itec_dimension.parquet'}")
    except Exception as e:
        print("ข้าม parquet:", e)


def make_gold(df, n):
    """ครึ่งหนึ่งสุ่มทั่วไป อีกครึ่งเจาะกองที่น่าสงสัย — จะได้เห็นทั้งภาพรวมและจุดอ่อน"""
    OUT.mkdir(exist_ok=True)
    half = n // 2
    suspect = df[(df.Item_Type == "Unknown")
                 | df.by_category
                 | (df.Main_Product_Dimension == "Others")
                 | (df.Item_Host == "")]
    a = df.sample(min(half, len(df)), random_state=42).assign(**{"กลุ่ม": "สุ่มทั่วไป"})
    b = (suspect.drop(index=a.index, errors="ignore")
                .sample(min(n - half, len(suspect)), random_state=42)
                .assign(**{"กลุ่ม": "น่าสงสัย"}))
    g = pd.concat([a, b])

    # ⚠️ ItemId ขาดไม่ได้ ไม่งั้น join ไฟล์ที่ตรวจแล้วกลับเข้าผลลัพธ์ไม่ได้
    SHOW = ["กลุ่ม", "ItemId", "ItemName", "CategoryName", "SubCategoryName", "Brand",
            "IS_Promotion", "IS_Product", "Sale_Type", "Product_Dimension",
            "Product_Purpose", "Main_Product_Dimension", "Sub_Product_Dimension",
            "Item_Type", "Item_Host", "Item_Platform", "by_category"]
    g = g[[c for c in SHOW if c in g.columns]].copy()
    for c in ("ถูกไหม", "Main_ที่ถูก", "ผิดคอลัมน์อื่น", "หมายเหตุ"):
        g[c] = ""
    g.to_csv(GOLD_BLANK, index=False, encoding="utf-8-sig")

    print(f"\nเขียน {GOLD_BLANK} · {len(g):,} แถว")
    print("""
━━━ วิธีกรอก ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
เปิดด้วย Excel แล้วดู 6 คอลัมน์นี้ทุกแถว
   IS_Promotion · IS_Product · Product_Dimension · Product_Purpose
   Main_Product_Dimension  <- ตัวสำคัญสุด
   Sub_Product_Dimension

ถูกครบ        ->  ถูกไหม = y
Main ผิด      ->  เว้น ถูกไหม ว่าง แล้วพิมพ์หมวดที่ถูกใน Main_ที่ถูก
คอลัมน์อื่นผิด ->  พิมพ์ใน ผิดคอลัมน์อื่น : promo / product / demo / gaming / sub
ไม่แน่ใจ      ->  ถูกไหม = ?   (จะถูกตัดออกจากการนับ ไม่ต้องเดา)

เซฟทับเป็น  gold_set_checked.csv  แล้วรัน  python run.py --score
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")
    mains = sorted(df.Main_Product_Dimension.dropna().unique())
    print(f"หมวดที่มีให้เลือก {len(mains)} หมวด — พิมพ์ให้ตรงตามนี้")
    for i in range(0, len(mains), 4):
        print("   " + "".join(f"{m:<22}" for m in mains[i:i + 4]))


def score(df):
    if not GOLD_DONE.exists():
        sys.exit(f"ไม่พบ {GOLD_DONE}\n  กรอก gold_set_check.csv แล้วเซฟเป็นชื่อนี้ก่อน")
    g = pd.read_csv(GOLD_DONE, encoding="utf-8-sig", dtype=str).fillna("")
    key = ["ItemId"] if "ItemId" in g.columns and g.ItemId.ne("").all() else FALLBACK_KEY
    if key != ["ItemId"]:
        print("⚠️ gold set ไม่มี ItemId — ใช้คีย์ 4 ช่องแทน อาจจับคู่ไม่ตรงบางแถว")

    cur = df.drop_duplicates(key)
    m = g.merge(cur[key + ["Main_Product_Dimension", "Sub_Product_Dimension"]],
                on=key, how="left", suffixes=("_ตรวจ", ""))

    # คนกรอกสะกดอิสระ — "iphone" "Apple watch" "Other" "NETWORK"
    # เทียบกับชื่อจริงเองแทนที่จะให้พลาดกลายเป็นผิด
    mains = {x.strip().lower(): x for x in df.Main_Product_Dimension.dropna().unique()}
    _u = df.dropna(subset=["Sub_Product_Dimension"]).drop_duplicates("Sub_Product_Dimension")
    subs = dict(zip(_u.Sub_Product_Dimension.str.strip().str.lower(),
                    _u.Main_Product_Dimension))
    ALIAS = {"other": "Others", "console & gaming": "Console Gaming",
             "gaming gear": "Console Gaming", "it accessories": "PC Component"}

    def resolve(x):
        k = str(x).strip().lower()
        if not k:
            return ""
        if k in mains:                       # ชื่อ Main ตรง ๆ
            return mains[k]
        if k in subs:                        # เผลอกรอกชื่อ Sub -> เอา Main ของ Sub นั้น
            return subs[k]
        return ALIAS.get(k, x.strip())

    mark = g["ถูกไหม"].str.strip().str.lower()
    unsure = mark.eq("?")
    said_ok = mark.eq("y")
    # หมวดที่ถูก = ที่คนกรอกไว้ ถ้าไม่ได้กรอกแปลว่าของเดิมถูกอยู่แล้ว
    truth = g["Main_ที่ถูก"].str.strip()
    truth = truth.where(truth != "", g["Main_Product_Dimension"].str.strip()).map(resolve)
    unknown = truth.ne("") & ~truth.isin(set(mains.values()))
    if unknown.any():
        print(f"⚠️ ชื่อหมวดที่ไม่รู้จัก {int(unknown.sum())} แถว (ตัดออกจากการนับ): "
              f"{sorted(truth[unknown].unique())[:8]}")

    have = m.Main_Product_Dimension.notna() & m.Main_Product_Dimension.ne("")
    use = have & ~unsure & ~unknown
    ok = m.Main_Product_Dimension.str.strip().eq(truth)

    print(f"\n{'='*58}")
    print(f"จับคู่ได้ {int(have.sum())}/{len(g)} · ไม่แน่ใจ {int(unsure.sum())} (ตัดออก)")
    print(f"accuracy ของ Main = {ok[use].mean()*100:.1f}%   ({int(ok[use].sum())}/{int(use.sum())})")
    print(f"  ตอนที่คนตรวจเห็น  {said_ok[use].mean()*100:.1f}%")
    print("=" * 58)

    b = m[use & ~ok]
    if len(b):
        print(f"\n── ที่ยังผิด {len(b)} แถว ──")
        t = b.assign(truth=truth[use & ~ok]).groupby(
            ["Main_Product_Dimension", "truth"]).size().sort_values(ascending=False)
        for (a, c), v in t.head(15).items():
            print(f"  {v:>3}  {a:24} → {c}")
        p = OUT / "gold_errors.csv"
        b.assign(truth=truth[use & ~ok]).to_csv(p, index=False, encoding="utf-8-sig")
        print(f"\nรายการเต็ม -> {p}")
    print("\n⚠️ ถ้าเคยเอา gold set ชุดนี้ไปใช้แก้กฎมาแล้ว ตัวเลขจะสูงเกินจริง")
    print("   อยากได้ตัวเลขที่เชื่อได้ ต้องสุ่มชุดใหม่ที่ยังไม่เคยเห็น")


def main():
    ap = argparse.ArgumentParser(description="จัดหมวดสินค้า ITEC ด้วยกฎจาก rules.yaml")
    ap.add_argument("--source", choices=["csv", "db"], default="csv")
    ap.add_argument("--sample", type=int, default=0, help="ลองกับข้อมูลบางส่วน")
    ap.add_argument("--gold", type=int, metavar="N", help="สุ่ม gold set N แถวให้คนตรวจ")
    ap.add_argument("--score", action="store_true", help="วัดผลกับ gold_set_checked.csv")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if not (HERE / "rules.yaml").exists():
        sys.exit("ไม่พบ rules.yaml — รัน Cell 3 ของ itec_dimension.ipynb ก่อน")

    df = run(load(a.source, a.sample), verbose=not a.quiet)

    if a.gold:
        make_gold(df, a.gold)
    elif a.score:
        score(df)
    else:
        report(df)
        save(df)


if __name__ == "__main__":
    main()
