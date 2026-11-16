"""Snap every taxi's GPS trace to real roads (build step) — so playback moves cars along roads, not across blocks

Why: GPS fixes arrive every ~5 min and are on average 1.3 km apart; a straight line between two fixes cuts through
buildings ("flying cars"). Here each car is routed through its own moving fixes, in order, on our own GraphHopper
(scripts/taxi/graphhopper/config.yml — localhost, no data leaves the machine). Between two fixes that gives the
road path the car most likely took.

How:
  1. kept points  = fixes with a GPS signal that moved ≥ 60 m from the previous kept fix (parked jitter would add U-turns)
  2. route through ≤ 100 kept points per request (POST /route) → full geometry + where each fix was snapped
  3. split the geometry at the snapped fixes → one "leg" per pair of consecutive kept fixes
  4. drop legs that are > 3 × the straight distance + 1 km (a fix snapped to the wrong road) → the page draws those straight
  5. simplify each leg (Douglas-Peucker 8 m) and store its inner vertices as int16 steps of 1e-5° from fix a
     (the first / last vertex are the fixes themselves, already in the data)

Output (written by build_dashboard.py as data/taxi-roads.js, loaded by the page after first paint):
  { a: u32[legs] start point index · n: u16[legs] point index distance to the end fix (b = a + n)
    off: u32[legs + 1] offsets into verts (pairs) · verts: i16[2 × inner vertices] (dlon, dlat) · stats }

Needs GraphHopper running:  java -Xmx5g -jar graphhopper-web-11.1.jar server scripts/taxi/graphhopper/config.yml
"""
import json
import math
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

GH = "http://127.0.0.1:8989"          # not "localhost": on Windows it tries IPv6 first and waits ~2 s per request
CHUNK = 100
MOVE_KM = 0.06
SIMPLIFY_M = 8.0
Q = 1e5                     # 1e-5 degree ≈ 1.1 m


def _km(lo1, la1, lo2, la2):
    return math.hypot((lo2 - lo1) * 111.320 * math.cos(math.radians((la1 + la2) / 2)), (la2 - la1) * 110.540)


def gh_ok(url=GH):
    try:
        with urllib.request.urlopen(url + "/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def _route(points):
    body = json.dumps({"points": points, "profile": "car", "points_encoded": False, "instructions": False,
                       "calc_points": True}).encode()
    req = urllib.request.Request(GH + "/route", data=body, headers={"Content-Type": "application/json"})
    for k in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:        # 400 = a point could not be snapped → caller splits the chunk
            return {"error": e.read()[:200].decode("utf-8", "replace")}
        except Exception:
            time.sleep(1 + k)
    return None


def _dp(xy, tol):
    """Douglas-Peucker on metre coordinates → indices kept"""
    n = len(xy)
    if n < 3:
        return list(range(n))
    keep = np.zeros(n, bool); keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = xy[i], xy[j]
        ab = b - a; L = math.hypot(*ab)
        seg = xy[i + 1:j]
        d = np.abs(ab[0] * (seg[:, 1] - a[1]) - ab[1] * (seg[:, 0] - a[0])) / L if L > 0 else np.hypot(*(seg - a).T)
        k = int(np.argmax(d))
        if d[k] > tol:
            m = i + 1 + k; keep[m] = True
            stack += [(i, m), (m, j)]
    return np.flatnonzero(keep).tolist()


def _split(coords, snapped, chunk):
    """route geometry → [(a, b, path)] split at the snapped waypoints (they appear in order along the geometry)"""
    out, pos = [], 0
    idx = []
    for w in snapped:
        best, bd = pos, 1e18
        for k in range(pos, len(coords)):            # forward search — waypoints are in order
            d = (coords[k][0] - w[0]) ** 2 + (coords[k][1] - w[1]) ** 2
            if d < bd:
                bd, best = d, k
            if d == 0:
                break
        idx.append(best); pos = best
    for k in range(len(chunk) - 1):
        out.append((chunk[k], chunk[k + 1], coords[idx[k]:idx[k + 1] + 1]))
    return out


def _snap_vehicle(args):
    lon, lat, kept = args
    legs, bad = [], 0
    chunks = [kept[c:c + CHUNK] for c in range(0, max(1, len(kept) - 1), CHUNK - 1)]
    queue = [ch for ch in chunks if len(ch) >= 2]
    while queue:
        ch = queue.pop(0)
        j = _route([[float(lon[i]), float(lat[i])] for i in ch])
        if not j or "paths" not in j:
            if len(ch) > 2:                          # one bad point (e.g. off the network) → halve and retry
                m = len(ch) // 2
                queue[:0] = [ch[:m + 1], ch[m:]]
            else:
                bad += 1
            continue
        p = j["paths"][0]
        for a, b, path in _split(p["points"]["coordinates"], p["snapped_waypoints"]["coordinates"], ch):
            direct = _km(lon[a], lat[a], lon[b], lat[b])
            road = sum(_km(*path[k - 1], *path[k]) for k in range(1, len(path)))
            if len(path) < 2 or road > 3 * direct + 1:
                bad += 1
                continue
            legs.append((a, b, path))
    return legs, bad


def snap_all(pos, spd, flg, start, count, workers=6, log=print):
    """pos = cols['pos'] (lon, lat interleaved float32) · start/count per vehicle → payload dict (see module doc)"""
    lon, lat = pos[0::2].astype(np.float64), pos[1::2].astype(np.float64)
    jobs = []
    for v in range(len(start)):
        s, e = int(start[v]), int(start[v]) + int(count[v])
        kept = []
        for i in range(s, e):
            if flg[i] & 2:
                continue
            if not kept or _km(lon[kept[-1]], lat[kept[-1]], lon[i], lat[i]) >= MOVE_KM:
                kept.append(i)
        if len(kept) >= 2:
            jobs.append((lon, lat, kept))
    t0 = time.time()
    A, Nn, OFF, V = [], [], [0], []
    bad = done = 0
    with ThreadPoolExecutor(workers) as ex:
        for legs, b in ex.map(_snap_vehicle, jobs):
            bad += b; done += 1
            for a, bb, path in sorted(legs):
                # metres around fix a for the simplification
                la0 = math.radians(lat[a])
                xy = np.array([[(x - lon[a]) * 111320 * math.cos(la0), (y - lat[a]) * 110540] for x, y in path])
                keep = _dp(xy, SIMPLIFY_M)
                inner = [path[k] for k in keep[1:-1]]
                px, py = round(lon[a] * Q), round(lat[a] * Q)
                steps = []
                for x, y in inner:
                    qx, qy = round(x * Q), round(y * Q)
                    dx, dy = qx - px, qy - py
                    while abs(dx) > 32767 or abs(dy) > 32767:  # very long straight stretch → intermediate vertex
                        sx, sy = max(-32767, min(32767, dx)), max(-32767, min(32767, dy))
                        steps.append((sx, sy)); px += sx; py += sy; dx -= sx; dy -= sy
                    steps.append((dx, dy)); px, py = qx, qy
                if bb - a > 65535:
                    continue
                A.append(a); Nn.append(bb - a); V.extend(steps); OFF.append(OFF[-1] + len(steps))
            if done % 500 == 0:
                log(f"    {done:,}/{len(jobs):,} vehicles · {len(A):,} legs · {time.time() - t0:.0f} s")
    total = sum(len(j[2]) - 1 for j in jobs)
    log(f"  ตามถนน {len(A):,} / {total:,} ช่วง ({len(A) / max(1, total):.0%}) · ไม่ได้ {bad:,} · จุดกลาง {len(V):,} · {time.time() - t0:.0f} s")
    return {
        "a": np.array(A, np.uint32), "n": np.array(Nn, np.uint16), "off": np.array(OFF, np.uint32),
        "verts": np.array(V, np.int16).reshape(-1), "stats": {"legs": len(A), "of": total, "vertices": len(V)},
    }


def snap_cached(pos, spd, flg, start, count, out_dir, log=print):
    """snap_all with a cache in _out/roadsnap.npz, keyed by the points it was built from:
    same data → reuse (no GraphHopper needed) · new data → GraphHopper must be running, else no road file"""
    import hashlib
    key = hashlib.sha1(np.ascontiguousarray(pos).tobytes() + np.ascontiguousarray(flg).tobytes()
                       + np.asarray(start, np.int64).tobytes() + np.asarray(count, np.int64).tobytes()).hexdigest()
    cache = out_dir / "roadsnap.npz"
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        if str(z["key"]) == key:
            r = {k: z[k] for k in ("a", "n", "off", "verts")}
            r["stats"] = json.loads(str(z["stats"]))
            log(f"ตามถนน: ใช้ผลเดิม (ข้อมูลชุดเดิม) · {r['stats']['legs']:,} ช่วง")
            return r
    if not gh_ok():
        log("  (GraphHopper ไม่ได้รันอยู่ และข้อมูลเปลี่ยน — ข้ามขั้นตามถนน · ดู scripts/taxi/graphhopper/config.yml)")
        return None
    log("ตามถนน (GraphHopper localhost) ...")
    r = snap_all(pos, spd, flg, start, count, log=log)
    np.savez_compressed(cache, key=key, a=r["a"], n=r["n"], off=r["off"], verts=r["verts"], stats=json.dumps(r["stats"]))
    return r
