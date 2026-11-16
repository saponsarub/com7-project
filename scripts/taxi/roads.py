"""ระยะจากจุดที่รถจอด ถึงขอบถนนที่ใกล้ที่สุด — ใช้ตัดสินว่า "จอดอยู่บนถนน" หรือ "จอดนอกถนน" (ก่อนพิจารณาตัดไฟ)

ข้อมูลถนน: vector tiles ของ OpenFreeMap (OpenStreetMap ชุดเดียวกับแผนที่ฐานในหน้าเว็บ) ซูม 14 · ชั้น transportation
  ดึงเฉพาะ tile ที่มีจุดจอด (~2,200 tile ทั่วประเทศ) · เก็บ cache ไว้ที่ _out/roads_z14/ · ครั้งแรก ~10 นาที
  ถอด .pbf เอง (ไม่ต้องติดตั้ง package เพิ่ม)

ถนนที่นับ: motorway · trunk · primary · secondary · tertiary · minor (ซอย/ถนนในหมู่บ้าน)
  ไม่นับ: service (ทางในลานจอด/ทางเข้าบ้าน) · track · path · ราง
  ไม่นับสะพาน/อุโมงค์ — ใต้ทางด่วนมักเป็นลานจอด ส่วนถนนพื้นราบข้างล่างมีเส้นของตัวเองอยู่แล้ว
ระยะ = ระยะถึงเส้นกลางถนน − ครึ่งความกว้างโดยประมาณตามประเภทถนน (= ระยะถึง "ขอบถนน")

ความคลาดเคลื่อน (เรื่อง normalize): พิกัดในข้อมูลบางจุดมีแค่ทศนิยม 4 ตำแหน่ง (~±5.5 ม.) + GPS คลาด ~5–15 ม.
  ที่นี่คำนวณรายจุด — หน้าเว็บเอาค่า "มัธยฐาน" ของทุกจุดช่วงที่รถนิ่ง แล้วเผื่อระยะคลาดก่อนตัดสิน (js/analysis/parkstate.js)

คืนคอลัมน์ต่อจุด (ลำดับเดียวกับ cols):
  road  u8  ระยะถึงขอบถนน (ม.) 0–250 · 251 = ไกลกว่า 250 ม. · 255 = ไม่ได้คำนวณ (รถวิ่ง / ไม่มีสัญญาณ / ไม่มีข้อมูลถนน)
  rname u16 index ชื่อถนนที่ใกล้สุด (ภายใน 80 ม.) ใน road_names · 65535 = ไม่มี
"""
import json
import math
import time
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
CACHE = HERE / "_out" / "roads_z14"
Z = 14
UA = {"User-Agent": "EV7-SmartTaxi-Dashboard/2 (internal analytics)"}
ROAD_CLASS = {"motorway": 12, "trunk": 10, "primary": 8, "secondary": 7, "tertiary": 6, "minor": 4}   # ครึ่งความกว้าง (ม.)
STEP_M = 4            # เติมจุดตามเส้นถนนทุก ~4 ม. ก่อนหาจุดใกล้สุด (คลาดไม่เกิน 2 ม.)


# ── ถอด Mapbox Vector Tile (protobuf) แบบย่อ — เอาแค่ที่ต้องใช้ ─────────────────
def _varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1
        r |= (c & 0x7F) << s
        if c < 0x80:
            return r, i
        s += 7


def _fields(b):
    """(field number, wire type, value) ของ message — value = int หรือ bytes"""
    i, n = 0, len(b)
    while i < n:
        k, i = _varint(b, i)
        f, w = k >> 3, k & 7
        if w == 0:
            v, i = _varint(b, i)
        elif w == 2:
            ln, i = _varint(b, i); v = b[i:i + ln]; i += ln
        elif w == 1:
            v = b[i:i + 8]; i += 8
        elif w == 5:
            v = b[i:i + 4]; i += 4
        else:
            raise ValueError("wire type")
        yield f, w, v


def _packed(b):
    i, out = 0, []
    while i < len(b):
        v, i = _varint(b, i); out.append(v)
    return out


def _value(b):
    for f, w, v in _fields(b):
        if f == 1:
            return bytes(v).decode("utf-8", "replace")
        if f in (4, 5):
            return v
        if f == 6:
            return (v >> 1) ^ -(v & 1)
        if f == 7:
            return bool(v)
        if f in (2, 3):
            return None
    return None


def decode_lines(pbf, want=("transportation", "transportation_name")):
    """{ชื่อ layer: [(props, [[(x, y), ...], ...] พิกัดใน tile 0..extent), ...]} เฉพาะเส้น (LineString)"""
    out = {}
    for f, _, layer in _fields(pbf):
        if f != 3:
            continue
        name, keys, vals, feats, extent = None, [], [], [], 4096
        for g, _, v in _fields(layer):
            if g == 1: name = bytes(v).decode()
            elif g == 3: keys.append(bytes(v).decode())
            elif g == 4: vals.append(_value(v))
            elif g == 5: extent = v
            elif g == 2: feats.append(v)
        if name not in want:
            continue
        res = []
        for ft in feats:
            tags, gtype, geom = [], 0, []
            for g, _, v in _fields(ft):
                if g == 2: tags = _packed(v)
                elif g == 3: gtype = v
                elif g == 4: geom = _packed(v)
            if gtype != 2:
                continue
            props = {keys[tags[k]]: vals[tags[k + 1]] for k in range(0, len(tags) - 1, 2)}
            lines, cur, x, y, i = [], [], 0, 0, 0
            while i < len(geom):
                cmd, cnt = geom[i] & 7, geom[i] >> 3; i += 1
                if cmd in (1, 2):
                    for _ in range(cnt):
                        dx, dy = geom[i], geom[i + 1]; i += 2
                        x += (dx >> 1) ^ -(dx & 1); y += (dy >> 1) ^ -(dy & 1)
                        if cmd == 1 and cur:
                            lines.append(cur); cur = []
                        cur.append((x, y))
                elif cmd == 7:
                    pass
            if cur:
                lines.append(cur)
            res.append((props, lines, extent))
        out[name] = res
    return out


# ── tile ────────────────────────────────────────────────────────────────────
def tile_of(lat, lon, z=Z):
    n = 2 ** z
    lr = np.radians(lat)
    x = np.floor((lon + 180) / 360 * n).astype(np.int64)
    y = np.floor((1 - np.log(np.tan(lr) + 1 / np.cos(lr)) / math.pi) / 2 * n).astype(np.int64)
    return x, y


def tile_lonlat(x, y, px, py, extent, z=Z):
    n = 2 ** z
    lon = (x + px / extent) / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + py / extent) / n))))
    return lon, lat


def tile_url():
    tj = json.load(urllib.request.urlopen(urllib.request.Request("https://tiles.openfreemap.org/planet", headers=UA), timeout=30))
    return tj["tiles"][0]


def get_tile(x, y, url):
    f = CACHE / f"{x}_{y}.pbf"
    if f.exists():
        return f.read_bytes()
    for k in range(4):
        try:
            b = urllib.request.urlopen(urllib.request.Request(url.replace("{z}", str(Z)).replace("{x}", str(x)).replace("{y}", str(y)), headers=UA), timeout=30).read()
            if b[:2] == b"\x1f\x8b":
                import gzip
                b = gzip.decompress(b)
            f.write_bytes(b)
            return b
        except Exception as e:                                 # 404 = ทะเล/ไม่มีข้อมูล → tile ว่าง
            if getattr(e, "code", None) == 404:
                f.write_bytes(b""); return b""
            time.sleep(2 * (k + 1))
    return None


# ── หลัก ────────────────────────────────────────────────────────────────────
def road_columns(lon, lat, spd, flg):
    """lon/lat/spd/flg = คอลัมน์ต่อจุด (numpy) → (road u8, rname u16, names list)"""
    from scipy.spatial import cKDTree
    n = len(lon)
    road = np.full(n, 255, np.uint8)
    rname = np.full(n, 65535, np.uint16)
    stat = (spd < 5) & ((flg & 2) == 0)                       # เฉพาะจุดที่รถนิ่ง และมีสัญญาณ
    if not stat.any():
        return road, rname, []
    la, lo = lat[stat].astype(np.float64), lon[stat].astype(np.float64)
    key = np.round(la, 6) * 1e7 + np.round(lo, 6)
    ukey, inv = np.unique(key, return_inverse=True)
    first = np.zeros(len(ukey), np.int64); first[inv[::-1]] = np.arange(len(inv))[::-1]
    ula, ulo = la[first], lo[first]
    # tile ของทุกจุด + tile ข้างเคียงเฉพาะเมื่อจุดอยู่ห่างขอบ tile ไม่เกิน ~300 ม. (ถนนใกล้สุดอาจอยู่อีก tile)
    need = set()
    for dla in (-0.003, 0, 0.003):
        for dlo in (-0.003, 0, 0.003):
            tx, ty = tile_of(ula + dla, ulo + dlo)
            need.update(zip(tx.tolist(), ty.tolist()))
    CACHE.mkdir(parents=True, exist_ok=True)
    have = sum((CACHE / f"{x}_{y}.pbf").exists() for x, y in need)
    print(f"  tile ถนน {len(need):,} (cache {have:,} · ดึงใหม่ {len(need) - have:,})", flush=True)
    url = tile_url() if have < len(need) else None
    vx, vy, vw = [], [], []                                    # จุดบนถนน (lon, lat) · ครึ่งความกว้าง — list ของ array
    names, name_id = [], {}
    nx, ny, nid = [], [], []                                   # จุดบนเส้นชื่อถนน
    done = 0
    for x, y in sorted(need):
        b = get_tile(x, y, url)
        done += 1
        if done % 300 == 0:
            print(f"    {done:,}/{len(need):,}", flush=True)
        if not b:
            continue
        layers = decode_lines(b)
        for props, lines, ext in layers.get("transportation", []):
            c = props.get("class")
            if c not in ROAD_CLASS or props.get("brunnel") in ("bridge", "tunnel"):
                continue
            hw = ROAD_CLASS[c] - (1 if props.get("ramp") == 1 else 0)
            for ln in lines:
                a, b2 = _dense(x, y, ln, ext, STEP_M)
                vx.append(a); vy.append(b2); vw.append(np.full(len(a), hw, np.float32))
        for props, lines, ext in layers.get("transportation_name", []):
            nm = props.get("name:en") or props.get("name_en") or props.get("name")
            if not nm or props.get("class") not in ROAD_CLASS:
                continue
            if props.get("name") and props.get("name") != nm:
                nm = f"{nm} ({props['name']})" if len(nm) + len(props["name"]) < 60 else nm
            if nm not in name_id:
                name_id[nm] = len(names); names.append(nm)
            for ln in lines:
                a, b2 = _dense(x, y, ln, ext, 10)
                nx.append(a); ny.append(b2); nid.append(np.full(len(a), name_id[nm], np.int32))
    if not vx:
        return road, rname, names
    vx, vy, vw = np.concatenate(vx), np.concatenate(vy), np.concatenate(vw)
    if nx:
        nx, ny, nid = np.concatenate(nx), np.concatenate(ny), np.concatenate(nid)
    print(f"  จุดบนเส้นถนน {len(vx):,}", flush=True)
    to_xy = lambda lo_, la_: np.c_[np.asarray(lo_) * 111320 * np.cos(np.radians(np.asarray(la_))), np.asarray(la_) * 110540]
    tree = cKDTree(to_xy(vx, vy))
    dist, idx = tree.query(to_xy(ulo, ula), distance_upper_bound=300)
    hw = np.asarray(vw, np.float64)
    edge = np.where(np.isfinite(dist), np.maximum(0, dist - hw[np.minimum(idx, len(hw) - 1)]), 251)
    ur = np.minimum(np.round(edge), 251).astype(np.uint8)
    un = np.full(len(ukey), 65535, np.uint16)
    if len(nx):
        nd, ni = cKDTree(to_xy(nx, ny)).query(to_xy(ulo, ula), distance_upper_bound=80)
        ok = np.isfinite(nd)
        un[ok] = np.asarray(nid)[ni[ok]]
    # keep only the names some point actually uses (the tiles hold ~40k names)
    used = np.unique(un[un != 65535])
    remap = np.full(max(len(names), 1), 65535, np.uint16); remap[used] = np.arange(len(used))
    un = np.where(un != 65535, remap[np.minimum(un, len(remap) - 1)], 65535).astype(np.uint16)
    names = [names[i] for i in used]
    road[np.flatnonzero(stat)] = ur[inv]
    rname[np.flatnonzero(stat)] = un[inv]
    print(f"  จุดนิ่ง {stat.sum():,} (พิกัดไม่ซ้ำ {len(ukey):,}) · บนถนน (≤10 ม.) {np.mean(ur <= 10):.0%} · "
          f"นอกถนน (≥25 ม.) {np.mean((ur >= 25) & (ur < 251)):.0%} · ชื่อถนน {len(names):,}", flush=True)
    return road, rname, names


def _dense(x, y, ln, ext, step):
    """เส้นใน tile → lon/lat ที่เติมจุดทุก ~step เมตร (numpy)"""
    a = np.asarray(ln, np.float64)
    n = 2 ** Z
    lon = (x + a[:, 0] / ext) / n * 360 - 180
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * (y + a[:, 1] / ext) / n))))
    if len(a) < 2:
        return lon, lat
    dx = np.diff(lon) * 111320 * np.cos(np.radians(lat[:-1])); dy = np.diff(lat) * 110540
    m = np.maximum(1, (np.hypot(dx, dy) / step).astype(np.int64))
    seg = np.repeat(np.arange(len(m)), m)
    f = (np.arange(m.sum()) - np.repeat(np.cumsum(m) - m, m)) / np.repeat(m, m)
    lo = lon[seg] + np.diff(lon)[seg] * f; la = lat[seg] + np.diff(lat)[seg] * f
    return np.r_[lo, lon[-1]], np.r_[la, lat[-1]]


def _meters(lo1, la1, lo2, la2):
    return math.hypot((lo2 - lo1) * 111320 * math.cos(math.radians((la1 + la2) / 2)), (la2 - la1) * 110540)
