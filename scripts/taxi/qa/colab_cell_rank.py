# ── 7.1 · จัดอันดับพื้นที่ — "เขตไหน / อำเภอไหน / จังหวัดไหน มีรถมากที่สุด" ──
# รันหลังส่วน 7 (และหลัง cell chatbot ถ้ามี) · ห่อ ask() และ facts_for() เดิม ไม่ต้องเทรนใหม่
import re

RANK_RE = re.compile(r"(เขต|อำเภอ|จังหวัด|พื้นที่|แขวง|โซน|ตำบล)\s*ไหน|ที่ไหน.*(มาก|เยอะ)|(มาก|เยอะ|สูง)\s*(ที่)?สุด|อันดับ|top\s*\d*", re.I)

def is_rank(q):
    return bool(RANK_RE.search(q)) and not find_plate(q)[0]     # มีทะเบียน = ถามรถคันเดียว ไม่ใช่จัดอันดับ

def x_rank_area(place, when, top=5):
    now = latest_at(when[1])
    if place and place["level"] == "dist":                     # อำเภอเดียว → ไม่มีอะไรให้จัดอันดับ ตอบจำนวนรถ
        return x_cars_in_area(place, when)
    if place:                                                  # จังหวัด → จัดอันดับเขต/อำเภอในจังหวัดนั้น
        sub, col, scope = now[now.prov_code == place["code"]], "dist_th", place["label"]
        unit = "เขต" if place["code"] == "10" else "อำเภอ"
    else:                                                      # ไม่ระบุ → จัดอันดับจังหวัดทั้งประเทศ
        sub, col, scope, unit = now, "prov_th", "ทั้งประเทศ", "จังหวัด"
    g = (sub.assign(hired=sub.status.eq("มีผู้โดยสาร"))
            .groupby(col).agg(n=("car_id", "size"), hired=("hired", "sum"))
            .sort_values("n", ascending=False).head(top))
    return {"as_of": when[1], "scope": scope, "unit": unit, "total": len(sub),
            "top": [(k, int(r.n), int(r.hired)) for k, r in g.iterrows()]}

def rank_text(r):
    if "error" in r or "top" not in r:
        return answer("cars_in_area", r)
    if not r["top"]:
        return f"ไม่มีรถออนไลน์ใน{r['scope']} (ข้อมูล ณ {fmt_t(r['as_of'])})"
    lst = " · ".join(f"{i}. {name} {n} คัน (มีผู้โดยสาร {h})" for i, (name, n, h) in enumerate(r["top"], 1))
    return f"{r['unit']}ที่มีรถมากที่สุดใน{r['scope']} (รถออนไลน์ทั้งหมด {r['total']:,} คัน): {lst} · ข้อมูล ณ {fmt_t(r['as_of'])}"

def rank_facts(q):
    e = extract(q)
    if "memory" in globals() and not e["place"] and memory.get("place") and re.search(r"ที่นั่น|จังหวัดนี้|แถวนั้น|ที่เดิม", q):
        e["place"] = memory["place"]
    r = x_rank_area(e["place"], e["when"])
    if "memory" in globals() and e["place"]:
        memory["place"] = e["place"]
    return rank_text(r)

# ห่อ ask() เดิม (รันซ้ำได้ ไม่ห่อซ้อน)
if "_ask_orig" not in globals():
    _ask_orig = ask
def ask(q, verbose=False):
    if is_rank(q):
        if verbose:
            print("  intent=area_ranking (กฎคำว่า 'ไหน…มากที่สุด')")
        return rank_facts(q)
    return _ask_orig(q, verbose)

# ห่อ facts_for() ของ chatbot ถ้ามี
if "facts_for" in globals():
    if "_facts_orig" not in globals():
        _facts_orig = facts_for
    def facts_for(q):                                          # cell 10 คืน (intent, ข้อความ)
        return ("area_ranking", rank_facts(q)) if is_rank(q) else _facts_orig(q)

for q in ["รถอยู่เขตไหนในกรุงเทพมากที่สุด", "อำเภอไหนในชลบุรีมีรถเยอะสุด", "จังหวัดไหนมีรถเยอะที่สุด",
          "ตอนนี้รถคันไหนอยู่ภูเกตบ้าง", "ที่ชาร์จใกล้ที่สุดแถวหาดใหญ่"]:
    print("Q:", q); print("A:", ask(q, verbose=True)); print()
