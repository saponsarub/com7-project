"""ลอง "Predictive AI Functions" แบบ Databricks กับข้อมูล EV7 taxi — แต่รันในเครื่อง (ไม่มี Databricks)

  1. anomalies  ≈ ai_detect_anomalies — จำนวนรถออนไลน์ทุก 10 นาที แยกศูนย์ · ทำนายช่วงที่ควรเป็นจากอดีตของแต่ละจุดเวลา
                  ด้วย Chronos-Bolt แล้ว flag จุดที่หลุดช่วง (anomaly_score > 0.99 — default 0.95 ของ Databricks เตือนผิด ~5%
                  ของจุดโดยธรรมชาติ = ~36 ครั้ง/วัน สำหรับข้อมูลทุก 10 นาที)
  2. top drivers ≈ ai_top_drivers    — ชั่วโมงมีผู้โดยสาร · ชั่วโมงนอกกรุงเทพฯ  วันที่ 30 ก.ย. เทียบ 1 ต.ค. (ช่วงนาฬิกาเดียวกัน)
                  → segment (ศูนย์ · จังหวัด · ช่วงเวลา · คู่ของมิติ) ที่ดันขึ้น / ฉุดลงมากสุด · support ≥ 5% ของแถว
  3. forecast   ≈ ai_forecast        — ซ่อน 4 ชม.สุดท้าย ให้ Chronos-Bolt พยากรณ์ แล้วเทียบของจริง
                  กับ baseline 2 แบบ: ค่าล่าสุด · เวลาเดียวกันเมื่อวาน

โมเดล: amazon/chronos-bolt-small (time series foundation model แบบ transformer · Apache-2.0 · ~200 MB · CPU พอ)
  ใกล้เคียงแนวคิดของ ai_forecast v2 แต่ไม่ใช่ตัวเดียวกัน (Databricks ไม่เปิดเผยว่าใช้โมเดลอะไร)
ติดตั้ง:  pip install chronos-forecasting einops   (แนะนำ env แยก — อาจดึง transformers คนละรุ่นกับงานอื่น)

รัน:     python scripts/taxi/predictive_local.py      → ผลพิมพ์บนจอ + _out/predictive/*.csv · *.png
ต้องมี:  _out/points_clean.parquet (จาก build_dashboard.py)

⚠️ ข้อมูลชุดทดสอบมีแค่ ~29 ชม. (30 ก.ย. 10:48 – 1 ต.ค. 15:29) — พอสาธิตวิธี แต่ยังสรุปเชิงธุรกิจไม่ได้
   ผลไม่มีทะเบียนรถ (รวมเป็นกลุ่มเท่านั้น)
"""
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
OUT = HERE / "_out" / "predictive"
BIN = "10min"
HOLDOUT = 24            # 24 × 10 นาที = 4 ชม. ที่ซ่อนไว้ทดสอบ forecast
MIN_SUPPORT = 0.05      # เท่า default ของ ai_top_drivers


# ── data ─────────────────────────────────────────────────────────────────────
def load():
    d = pd.read_parquet(HERE / "_out" / "points_clean.parquet",
                        columns=["vin", "center", "meter", "signal", "speed", "gps_time", "dist"])
    sys.argv = sys.argv[:1]                                   # build_dashboard อ่าน argv ตอน import
    import build_dashboard as bd
    g = json.load(open(bd.DIST_PIP, encoding="utf-8"))["features"]
    dists = pd.DataFrame([f["properties"] for f in g])
    d["province"] = d.dist.map(dists.pen).fillna("Unknown")
    d["district"] = d.dist.map(dists.en).fillna("Unknown")
    d["in_bkk"] = d.dist.map(dists.ppc).eq("TH10")
    d = d.sort_values(["vin", "gps_time"]).reset_index(drop=True)
    # เวลาที่แต่ละจุด "แทน" = ถึงจุดถัดไปของคันเดียวกัน (ไม่เกิน 10 นาที) — เหมือนหน้าเว็บ
    nxt = d.groupby("vin").gps_time.shift(-1)
    d["dur_h"] = ((nxt - d.gps_time).dt.total_seconds().clip(upper=600).fillna(300)) / 3600
    d["hired"] = d.meter.eq("F")
    return d


def series(d):
    """จำนวนรถ (ไม่ซ้ำ) ที่มีจุดในแต่ละช่วง 10 นาที — ทั้งหมด / แยกศูนย์ / เฉพาะมีผู้โดยสาร"""
    d = d.assign(bin=d.gps_time.dt.floor(BIN))
    idx = pd.date_range(d.bin.min(), d.bin.max(), freq=BIN)
    s = {"online · all": d.groupby("bin").vin.nunique()}
    for c, g in d.groupby("center"):
        s[f"online · center {c}"] = g.groupby("bin").vin.nunique()
    s["on trip · all"] = d[d.hired].groupby("bin").vin.nunique()
    return pd.DataFrame(s).reindex(idx).fillna(0)


def pipeline():
    import torch
    from chronos import BaseChronosPipeline
    return BaseChronosPipeline.from_pretrained("amazon/chronos-bolt-small", dtype=torch.float32)


# ── 1 · anomalies ────────────────────────────────────────────────────────────
def feed_outages(S, frac=0.5):
    """ช่วงที่ API ส่งข้อมูลมาน้อยผิดปกติ (รถออนไลน์ทั้งระบบ < 50% ของค่ามัธยฐานทั้งชุด) = ข้อมูลขาด ไม่ใช่รถหายจริง
    ใช้มัธยฐานทั้งชุด ไม่ใช่แบบเลื่อน — ช่วงต้นข้อมูล (30 ก.ย. 10:40–11:20 มีแค่ 1–7 คัน) เพื่อนบ้านก็ต่ำ เลยหลุดถ้าใช้แบบเลื่อน"""
    y = S["online · all"]
    return y < frac * y.median()


def detect_anomalies(S, pipe, threshold=0.99, context_min=24):
    """สำหรับทุกจุดเวลา t: ใช้ข้อมูลก่อน t ทำนาย 1 ช่วงข้างหน้า → ค่าที่คาด + ช่วง → anomaly score
    Chronos-Bolt ให้ quantile 0.1–0.9 → แปลงความกว้างเป็น σ (ช่วง 80% ≈ ±1.28σ) แล้วคิด score = P(|z| ≤ ค่าที่เห็น)
    ช่วงที่ feed ขาดยังถูก flag แต่ไม่ถูกใช้เป็น "อดีต" ของจุดถัดไป (ให้เป็น NaN) — ไม่งั้นจุดหลังฟื้นจะถูก flag ผิด"""
    import torch
    from math import erf, sqrt
    gap = feed_outages(S).to_numpy()
    rows = []
    for col in S.columns:
        y = S[col].to_numpy(np.float32)
        yc = np.where(gap, np.nan, y).astype(np.float32)
        ctx = [torch.tensor(yc[:t]) for t in range(context_min, len(y))]
        q, med = pipe.predict_quantiles(ctx, prediction_length=1, quantile_levels=[0.1, 0.5, 0.9])
        q10, q50, q90 = q[:, 0, 0].numpy(), q[:, 0, 1].numpy(), q[:, 0, 2].numpy()
        sigma = np.maximum((q90 - q10) / 2.563, 1.0)          # อย่างน้อย 1 คัน กันช่วงแคบเกินจริง
        obs = y[context_min:]
        z = np.abs(obs - q50) / sigma
        score = np.array([erf(v / sqrt(2)) for v in z])
        rows.append(pd.DataFrame({"series": col, "time": S.index[context_min:], "observed": obs, "expected": q50.round(1),
                                  "lower_bound": (q50 - 1.96 * sigma).round(1), "upper_bound": (q50 + 1.96 * sigma).round(1),
                                  "anomaly_score": score.round(3), "is_anomaly": score > threshold,
                                  "kind": np.where(gap[context_min:], "data feed gap", np.where(score > threshold, "unusual value", ""))}))
    return pd.concat(rows, ignore_index=True)


# ── 2 · top drivers ──────────────────────────────────────────────────────────
def top_drivers(rows, metric, is_test, dims, min_support=MIN_SUPPORT, top=12):
    """เหมือน ai_top_drivers: sum(metric) ของ test − control ต่อ segment (1 มิติ และคู่มิติ) ที่ครอบคลุม ≥ min_support ของแถว"""
    r = rows.dropna(subset=[metric, is_test])
    n = len(r)
    out = [{"contributor": "all", "metric_control": r.loc[~r[is_test], metric].sum(), "metric_test": r.loc[r[is_test], metric].sum(), "support": 1.0}]
    for k in (1, 2):
        for combo in combinations(dims, k):
            g = r.groupby(list(combo) + [is_test])[metric].sum().unstack(is_test, fill_value=0)
            sup = r.groupby(list(combo)).size() / n
            for key, row in g.iterrows():
                key = key if isinstance(key, tuple) else (key,)
                s = sup.loc[key if len(key) > 1 else key[0]]
                if s < min_support:
                    continue
                out.append({"contributor": " · ".join(f"{c}={v}" for c, v in zip(combo, key)),
                            "metric_control": row.get(False, 0.0), "metric_test": row.get(True, 0.0), "support": s})
    o = pd.DataFrame(out)
    o = o[(o.metric_control != 0) | (o.metric_test != 0)]            # segment ที่เป็น 0 ทั้งสองฝั่ง ไม่มีความหมาย
    o["change"] = o.metric_test - o.metric_control
    o["relative_change"] = o.change / o.metric_control.replace(0, np.nan)
    o = o.round({"metric_control": 1, "metric_test": 1, "change": 1, "relative_change": 3, "support": 3})
    allrow = o[o.contributor == "all"]
    rest = o[o.contributor != "all"].sort_values("change")
    return allrow, rest.tail(top // 2).iloc[::-1], rest.head(top // 2)


def day_compare(d, full=0.9):
    """30 ก.ย. vs 1 ต.ค. เฉพาะช่วง 10 นาทีที่ "ทั้งสองวัน" มีข้อมูลครบ (รถออนไลน์ ≥ 90% ของค่ามัธยฐาน)
    เคยพลาด: เทียบตามนาฬิกา 10:48–15:29 ตรง ๆ แต่วันแรกข้อมูลจริงเริ่ม ~11:30 → ชั่วโมง 11:00 ของวันแรกมีแค่ครึ่งชั่วโมง
    ทำให้ "ชั่วโมงมีผู้โดยสาร +20%" ซึ่งเป็นผลจากข้อมูลขาด ไม่ใช่ธุรกิจ"""
    t = d.gps_time
    b = t.dt.floor(BIN)
    on = d.groupby([b.dt.date.rename("day"), (b - b.dt.normalize()).rename("clock")]).vin.nunique().unstack("day")
    good = on.index[(on >= full * on.stack().median()).all(axis=1)]          # bins complete on both days
    clock = b - b.dt.normalize()
    r = d[clock.isin(good) & t.dt.date.isin(on.columns[:2])].copy()
    lo, hi = good.min(), good.max() + pd.Timedelta(BIN)
    r["is_test"] = r.gps_time.dt.date == t.max().date()
    r["hour"] = r.gps_time.dt.hour.map(lambda h: f"{h:02d}:00")
    r["area"] = np.where(r.in_bkk, "Bangkok", "outside Bangkok")
    r["hired_h"] = np.where(r.hired, r.dur_h, 0.0)
    r["outside_h"] = np.where(~r.in_bkk & r.signal.eq("A"), r.dur_h, 0.0)
    return r, lo, hi


# ── 3 · forecast ─────────────────────────────────────────────────────────────
def forecast(S, pipe, cols=("online · all", "on trip · all"), h=HOLDOUT):
    import torch
    gap = feed_outages(S).to_numpy()
    res = []
    for col in cols:
        y = np.where(gap, np.nan, S[col].to_numpy(np.float32)).astype(np.float32)   # feed gaps = missing, not zero
        train, test = y[:-h], y[-h:]
        q, _ = pipe.predict_quantiles(torch.tensor(train), prediction_length=h, quantile_levels=[0.1, 0.5, 0.9])
        q = q[0].numpy()
        naive = np.full(h, train[~np.isnan(train)][-1])
        yday = y[-h - 144:-144] if len(y) >= h + 144 else np.full(h, np.nan)   # 144 × 10 นาที = 24 ชม.
        mae = lambda p: float(np.nanmean(np.abs(p - test)))
        ok = ~np.isnan(test)
        res.append({"series": col, "MAE chronos": round(mae(q[:, 1]), 1), "MAE last value": round(mae(naive), 1),
                    "MAE same time yesterday": round(mae(yday), 1), "MAPE chronos %": round(float(np.nanmean(np.abs(q[:, 1] - test) / np.maximum(test, 1))) * 100, 1),
                    "80% interval covers": f"{np.mean(((test >= q[:, 0]) & (test <= q[:, 2]))[ok]):.0%}",
                    "_pred": q, "_test": test, "_train": train, "_yday": yday})
    return res


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)
    OUT.mkdir(parents=True, exist_ok=True)
    print("โหลดข้อมูล ...", flush=True)
    d = load()
    S = series(d)
    print(f"  {len(d):,} จุด · {d.vin.nunique():,} คัน · {len(S)} ช่วง × 10 นาที ({S.index[0]} – {S.index[-1]})")
    print("โหลดโมเดล Chronos-Bolt ...", flush=True)
    pipe = pipeline()

    print("\n━━ 1 · ai_detect_anomalies (เทียบเท่า) — รถออนไลน์ทุก 10 นาที ━━")
    A = detect_anomalies(S, pipe)
    A.to_csv(OUT / "anomalies.csv", index=False, encoding="utf-8-sig")
    flagged = A[A.is_anomaly]
    print(f"  ตรวจ {len(A):,} จุด · ผิดปกติ {len(flagged)} จุด (score > 0.99) · ช่วง feed ขาด {int(feed_outages(S).sum())} ช่วง")
    print(flagged.sort_values(["series", "time"]).to_string(index=False, max_rows=40))

    print("\n━━ 2 · ai_top_drivers (เทียบเท่า) — 30 ก.ย. เทียบ 1 ต.ค. ช่วงนาฬิกาเดียวกัน ━━")
    r, lo, hi = day_compare(d)
    print(f"  ช่วงที่ข้อมูลครบทั้งสองวัน {str(lo)[-8:-3]}–{str(hi)[-8:-3]} ({r.gps_time.dt.floor(BIN).dt.time.nunique()} ช่วง × 10 นาที) · control = {r.gps_time.min().date()} · test = {r.gps_time.max().date()}")
    cov = r.groupby(["hour", "is_test"]).vin.nunique().unstack().rename(columns={False: "control", True: "test"})
    print("  ตรวจความครอบคลุมข้อมูลก่อน (จำนวนรถที่มีจุด ต่อชั่วโมง) — ถ้าไม่เท่ากัน ความต่างอาจมาจากข้อมูล ไม่ใช่ธุรกิจ")
    print("  " + cov.T.to_string().replace("\n", "\n  "))
    for metric, label in (("hired_h", "ชั่วโมงมีผู้โดยสาร"), ("outside_h", "ชั่วโมงอยู่นอกกรุงเทพฯ")):
        allrow, up, down = top_drivers(r, metric, "is_test", ["center", "province", "hour"])
        a = allrow.iloc[0]
        print(f"\n  [{label}] รวม {a.metric_control:,.0f} → {a.metric_test:,.0f} ชม. ({a.relative_change:+.1%})")
        print("  ดันขึ้นมากสุด:"); print(up[["contributor", "metric_control", "metric_test", "change", "relative_change", "support"]].to_string(index=False))
        print("  ฉุดลงมากสุด:"); print(down[["contributor", "metric_control", "metric_test", "change", "relative_change", "support"]].to_string(index=False))
        pd.concat([allrow, up, down]).to_csv(OUT / f"top_drivers_{metric}.csv", index=False, encoding="utf-8-sig")

    print(f"\n━━ 3 · ai_forecast (เทียบเท่า) — ซ่อน {HOLDOUT * 10 // 60} ชม. สุดท้ายแล้วพยากรณ์ ━━")
    F = forecast(S, pipe)
    print(pd.DataFrame([{k: v for k, v in f.items() if not k.startswith("_")} for f in F]).to_string(index=False))
    plot(S, A, F)
    print(f"\nบันทึก {OUT}")


def plot(S, A, F):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(12, 7), constrained_layout=True)
    a = A[A.series == "online · all"]
    ax[0].fill_between(a.time, a.lower_bound, a.upper_bound, color="#cfe3d6", label="expected range (95%)")
    ax[0].plot(S.index, S["online · all"], color="#10231a", lw=1.2, label="online vehicles / 10 min")
    f = a[a.is_anomaly]
    ax[0].scatter(f.time, f.observed, color="#d93a40", zorder=3, s=28, label="anomaly")
    ax[0].set_title("Anomalies — vehicles online every 10 min (Chronos-Bolt, one step ahead)", loc="left", fontsize=11)
    ax[0].legend(loc="lower left", fontsize=8, frameon=False)
    for k, fc in enumerate(F):
        idx = S.index
        h = len(fc["_test"]); tt = idx[-h:]
        col = ["#00a332", "#f08c00"][k]
        ax[1].plot(idx[:-h], fc["_train"], color=col, lw=1, alpha=.7)
        ax[1].plot(tt, fc["_test"], color=col, lw=1.6, label=f"{fc['series']} — actual")
        ax[1].plot(tt, fc["_pred"][:, 1], color="#10231a", lw=1.2, ls="--")
        ax[1].fill_between(tt, fc["_pred"][:, 0], fc["_pred"][:, 2], color=col, alpha=.18)
    ax[1].plot([], [], color="#10231a", ls="--", label="Chronos forecast (80% band shaded)")
    ax[1].set_title(f"Forecast — last {HOLDOUT * 10 // 60} h hidden, then predicted", loc="left", fontsize=11)
    ax[1].legend(loc="upper left", fontsize=8, frameon=False)
    for x in ax:
        x.spines[["top", "right"]].set_visible(False); x.grid(axis="y", color="#e3e8e5", lw=.6)
    fig.savefig(OUT / "predictive_taxi.png", dpi=110)


if __name__ == "__main__":
    main()
