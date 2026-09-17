# -*- coding: utf-8 -*-
"""ที่เดียวสำหรับต่อฐานข้อมูลทุกตัวของโปรเจกต์ — read-only

    python scripts/db.py                 ดูว่าฐานไหนต่อได้บ้าง
    python scripts/db.py itec            ทดสอบต่อ itec
    python scripts/db.py itec "SELECT TOP 5 * FROM rpt.booking_list"

ใช้ในโค้ด

    import db
    df = db.query("itec", "SELECT TOP 10 * FROM rpt.booking_list")
    with db.connect("k2") as cn:
        ...

⚠️ credential อ่านจาก environment variable เท่านั้น — ห้าม hardcode รหัสผ่าน
   ตั้งถาวรครั้งเดียวด้วย PowerShell แล้วเปิด VS Code ใหม่

       [Environment]::SetEnvironmentVariable('MIS_USER','...','User')
       [Environment]::SetEnvironmentVariable('MIS_PWD','...','User')

เอกสาร: COM7-Knowledge-Base/02_System/Retail (ITEC + CRM)/ITEC - Query Cookbook.md
"""
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

DRIVER = "ODBC Driver 18 for SQL Server"

# ── ฐานข้อมูลทั้งหมดที่โปรเจกต์นี้ใช้ ───────────────────────────────────
# แก้ค่า default ที่นี่ที่เดียว · override ด้วย env ได้ทุกตัว
PROFILES = {
    "itec": {
        "ชื่อ": "ITEC / MIS — ยอดขาย สินค้า สมาชิก",
        "server": os.environ.get("MIS_SERVER", "192.168.43.250,18963"),
        "database": os.environ.get("MIS_DB", "_db1_3f9c2a7e-8b41-4d6f-9c25-1a7e5c0d2b8f"),
        "user_env": "MIS_USER",
        "pwd_env": "MIS_PWD",
    },
    "k2": {
        "ชื่อ": "K2 / ITOS — สัญญา ผ่อนชำระ บอกเลิก",
        "server": os.environ.get("K2_SERVER", "43.254.133.123"),
        "database": os.environ.get("K2_DB", "HPCOM7"),
        "user_env": "K2_USER",
        "pwd_env": "K2_PWD",
    },
}


def creds(profile):
    """คืน (user, pwd) — ไม่คืนค่าจริงออกไปข้างนอก ใช้ภายในเท่านั้น"""
    p = PROFILES[profile]
    return os.environ.get(p["user_env"]), os.environ.get(p["pwd_env"])


def ready(profile):
    """ตั้ง credential ครบหรือยัง"""
    u, w = creds(profile)
    return bool(u and w)


def connect(profile, database=None, timeout=300):
    """เปิด connection · profile = 'itec' หรือ 'k2'

    database  ระบุเพื่อข้ามฐาน default (เช่น itec มีหลายฐานในเครื่องเดียวกัน)
    """
    if profile not in PROFILES:
        raise KeyError(f"ไม่รู้จัก profile '{profile}' · ที่มี: {list(PROFILES)}")
    p = PROFILES[profile]
    u, w = creds(profile)
    if not (u and w):
        raise RuntimeError(
            f"ยังไม่ได้ตั้ง credential ของ '{profile}'\n"
            f"  ต้องมี env: {p['user_env']} และ {p['pwd_env']}\n"
            f"  ตั้งถาวร:  [Environment]::SetEnvironmentVariable('{p['user_env']}','...','User')\n"
            f"             [Environment]::SetEnvironmentVariable('{p['pwd_env']}','...','User')\n"
            f"  แล้วเปิด VS Code ใหม่")

    import pyodbc
    db = database or p["database"]
    cs = (f"DRIVER={{{DRIVER}}};SERVER={p['server']};"
          + (f"DATABASE={db};" if db else "")
          + f"UID={u};PWD={w};TrustServerCertificate=yes;")
    return pyodbc.connect(cs, timeout=timeout)


def query(profile, sql, params=None, database=None, timeout=300):
    """รัน SELECT แล้วคืน DataFrame"""
    import pandas as pd
    with connect(profile, database, timeout) as cn:
        return pd.read_sql(sql, cn, params=params)


def columns(profile, schema, table, database=None):
    """ดูโครงสร้างตาราง — ใช้บ่อยตอนสำรวจของใหม่"""
    return query(profile, """
        SELECT ORDINAL_POSITION AS pos, COLUMN_NAME AS col, DATA_TYPE AS ชนิด,
               CHARACTER_MAXIMUM_LENGTH AS ยาว, IS_NULLABLE AS null_ได้
        FROM   INFORMATION_SCHEMA.COLUMNS
        WHERE  TABLE_SCHEMA = ? AND TABLE_NAME = ?
        ORDER  BY ORDINAL_POSITION""", [schema, table], database)


def status():
    """สรุปว่าฐานไหนพร้อมใช้ — ไม่แสดงรหัสผ่าน"""
    import pandas as pd
    rows = []
    for k, p in PROFILES.items():
        u, _ = creds(k)
        rows.append({
            "profile": k, "ระบบ": p["ชื่อ"], "server": p["server"],
            "env": f"{p['user_env']} / {p['pwd_env']}",
            "user": u or "—",
            "พร้อม": "✅" if ready(k) else "❌ ยังไม่ได้ตั้ง env",
        })
    return pd.DataFrame(rows)


def _ping(profile):
    import time
    t0 = time.time()
    try:
        with connect(profile, timeout=15) as cn:
            v = cn.cursor().execute("SELECT @@VERSION").fetchval()
        print(f"  ✅ {profile:<6} ต่อได้ใน {time.time()-t0:.1f}s · {v.splitlines()[0][:60]}")
        return True
    except Exception as e:
        print(f"  ❌ {profile:<6} {str(e).splitlines()[0][:100]}")
        return False


if __name__ == "__main__":
    import pandas as pd
    pd.set_option("display.width", 200)

    if len(sys.argv) == 1:
        print(status().to_string(index=False))
        print("\nทดสอบต่อจริง")
        for k in PROFILES:
            if ready(k):
                _ping(k)
            else:
                print(f"  ⏭  {k:<6} ข้าม (ยังไม่ได้ตั้ง env)")
        sys.exit(0)

    prof = sys.argv[1]
    if len(sys.argv) == 2:
        _ping(prof)
    else:
        print(query(prof, sys.argv[2]).to_string(index=False))
