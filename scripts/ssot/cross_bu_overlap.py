# -*- coding: utf-8 -*-
"""SSOT — วัดลูกค้าซ้อนกันข้ามระบบแบบคร่าวๆ ด้วยเลขบัตรประชาชน และเบอร์มือถือ

    python scripts/ssot/cross_bu_overlap.py            → scripts/ssot/_out/cross_bu_overlap.json (ตัวเลขรวมเท่านั้น)

คร่าวๆ = เทียบ "ชุดของคีย์" ระหว่างระบบ (ยังไม่ใช่การจับคู่รายคนเต็มรูปแบบของ IDENTITY layer)
  - เลขบัตร: เฉพาะเลขบุคคล 13 หลักที่ผ่าน checksum (ขึ้นต้น 1–8)
  - มือถือ: 0[689] + 8 หลัก หลัง normalize · ตัดเบอร์ที่ใช้ร่วมกันมาก (≥ 5 แถวในระบบเดียวกันที่ต่าง id) ไม่ได้ทำ → ตัวเลขมือถือเป็นค่าสูงสุด
ระบบ: CRM (member_auth.identity_no · members.phone) · ITEC-Rep (Customer2) · K2 (PERSON) · ITOS (S_CUSTOMER / S_CUSTTEL)
EV7 taxi ไม่อยู่ใน SSOT · GI Core รอสิทธิ์
คีย์อยู่ในหน่วยความจำเท่านั้น ไม่เขียนลงดิสก์
"""
import json
import sys
import time
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import db                                                   # noqa: E402
from ssot.cleanse import clean_phone, thai_id              # noqa: E402

pd.set_option("future.infer_string", False)
OUT = HERE / "_out"
K = {}                                                      # {system: {"id": np.array, "mobile": np.array}}


def keys(id_series, phone_series_list):
    d, v, k = thai_id(id_series) if id_series is not None else (None, None, None)
    ids = np.unique(pd.to_numeric(d[k == 1], errors="coerce").dropna().astype("int64").to_numpy()) if id_series is not None else np.empty(0, "int64")
    mob = []
    for s in phone_series_list:
        p = clean_phone(s)
        mob.append(p["val"][p["mobile"]])
    mob = np.unique(np.concatenate(mob)) if mob else np.empty(0, "int64")
    return ids, mob


def add(sysname, ids, mob):
    if sysname not in K:
        K[sysname] = {"id": [], "mobile": []}
    K[sysname]["id"].append(ids); K[sysname]["mobile"].append(mob)


def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def load_k2_itos():
    cur = db.connect("k2", timeout=900).cursor()
    cur.execute("SELECT TAX_ID, PHONE, PHONE_SECOND FROM dbo.PERSON WITH (NOLOCK)")
    df = pd.DataFrame.from_records(cur.fetchall(), columns=["id", "p1", "p2"])
    add("K2", *keys(df.id, [df.p1, df.p2])); log(f"K2 {len(df):,}")
    X = "ILOAN_DATASOURCE.ILOAN_DATASOURCE.ext_collection"
    cur.execute(f"SELECT CUST_CARDNO FROM {X}.S_CUSTOMER")
    a = pd.DataFrame.from_records(cur.fetchall(), columns=["id"])
    cur.execute(f"SELECT TEL_PHONE FROM {X}.S_CUSTTEL")
    t = pd.DataFrame.from_records(cur.fetchall(), columns=["p"])
    ids, _ = keys(a.id, []); _, mob = keys(None, [t.p])
    add("ITOS", ids, mob); log(f"ITOS {len(a):,} · tel {len(t):,}")


def load_itec():
    cn = db.connect("itec", timeout=900); last = ""; n = 0
    while True:
        cur = cn.cursor()
        cur.execute("SELECT TOP (200000) CusCode, Tel, CitizenNo, TaxNo FROM dbo.Customer2 WITH (NOLOCK) "
                    "WHERE CusCode > CAST(? AS varchar(20)) ORDER BY CusCode", last)
        r = cur.fetchall()
        if not r:
            break
        df = pd.DataFrame.from_records(r, columns=["code", "tel", "cit", "tax"]); last = df.code.iat[-1]; n += len(df)
        idc = df.cit.where(thai_id(df.cit)[2] == 1, df.tax)        # CitizenNo ถ้าเป็นเลขบุคคล ไม่งั้น TaxNo
        add("ITEC-Rep", *keys(idc, [df.tel]))
        if n % 2_000_000 < 200_000:
            log(f"ITEC {n:,}")
        if len(df) < 200000:
            break
    log(f"ITEC done {n:,}")


def load_crm():
    cn = db.connect("crm", database="crm_pool_prod", timeout=900); cur = cn.cursor()
    cur.execute("SELECT MIN(id), MAX(id) FROM member_auth"); lo, hi = cur.fetchone()
    for s in range(lo, hi + 1, 50_000):
        cur.execute("SELECT identity_no FROM member_auth WHERE id BETWEEN %s AND %s", (s, s + 49_999))
        r = cur.fetchall()
        if r:
            add("CRM", keys(pd.Series([x[0] for x in r]), [])[0], np.empty(0, "int64"))
    cur.execute("SELECT MIN(id), MAX(id) FROM members"); lo, hi = cur.fetchone(); n = 0
    for s in range(lo, hi + 1, 50_000):
        for attempt in range(5):
            try:
                cur.execute("SELECT phone FROM members WHERE id BETWEEN %s AND %s", (s, s + 49_999)); r = cur.fetchall(); break
            except Exception as e:
                log(f"retry {attempt + 1}: {str(e)[:60]}"); time.sleep(20 * (attempt + 1))
                cn = db.connect("crm", database="crm_pool_prod", timeout=900); cur = cn.cursor()
        if r:
            n += len(r); add("CRM", np.empty(0, "int64"), keys(None, [pd.Series([x[0] for x in r])])[1])
    log(f"CRM members {n:,}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"_run": time.strftime("%Y-%m-%d %H:%M"), "systems": {}, "id_overlap": {}, "mobile_overlap": {}, "notes": []}
    for name, fn in [("K2 + ITOS", load_k2_itos), ("ITEC-Rep", load_itec), ("CRM", load_crm)]:
        try:
            fn()
        except Exception as e:
            res["notes"].append(f"{name}: {str(e)[:120]}"); log(f"{name} FAILED {str(e)[:120]}")
    S = {s: {k: np.unique(np.concatenate(v[k])) if v[k] else np.empty(0, "int64") for k in ("id", "mobile")} for s, v in K.items()}
    for s, v in S.items():
        res["systems"][s] = {"ids": int(len(v["id"])), "mobiles": int(len(v["mobile"]))}
    for kind, key in [("id_overlap", "id"), ("mobile_overlap", "mobile")]:
        for a, b in combinations(sorted(S), 2):
            if len(S[a][key]) and len(S[b][key]):
                res[kind][f"{a} ∩ {b}"] = int(len(np.intersect1d(S[a][key], S[b][key], assume_unique=True)))
    if {"K2", "ITOS", "ITEC-Rep"} <= set(S):
        x = np.intersect1d(np.intersect1d(S["K2"]["id"], S["ITOS"]["id"]), S["ITEC-Rep"]["id"])
        res["id_overlap"]["K2 ∩ ITOS ∩ ITEC-Rep"] = int(len(x))
        u = np.union1d(S["K2"]["id"], S["ITOS"]["id"])
        res["id_overlap"]["UFUND (K2 ∪ ITOS)"] = int(len(u))
        res["id_overlap"]["UFUND ∩ ITEC-Rep"] = int(len(np.intersect1d(u, S["ITEC-Rep"]["id"])))
    json.dump(res, open(OUT / "cross_bu_overlap.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
