# -*- coding: utf-8 -*-
"""ดึง keyword ทั้งหมดจาก ci_item_category.sql ออกมาเป็น YAML

ไม่ต้องพิมพ์ 76 คำเอง และไม่มีโอกาสพิมพ์ผิด
    python scripts/itec/category/extract_keywords.py <path ไป .sql>
"""
import re
import sys
from pathlib import Path

import yaml

sys.stdout.reconfigure(encoding="utf-8")

OUT = Path(__file__).parent / "item_keywords.yaml"

# keyword สั้น เสี่ยงจับคำอื่นติดมา -> ตั้ง whole_word ให้ตั้งแต่แรก
RISKY = {"pc", "sd", "ram", "cpu", "pin", "card", "case", "sim", "usb",
         "hdd", "ssd", "h/d", "care", "demo", "dock", "film"}


def parse(sql_text):
    flat = re.sub(r"\s+", " ", sql_text)
    pat = r"CASE WHEN (.*?) THEN 1 ELSE 0 END AS (IS_[A-Za-z_]+)"
    rules = {}
    for cond, name in re.findall(pat, flat, re.I):
        words = sorted({w.lower() for w in re.findall(r"LIKE '%([^']*)%'", cond)})
        rules[name] = {"words": words,
                       "whole_word": any(w in RISKY for w in words)}
    return rules


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1
               else Path.home() / "Downloads" / "ci_item_category.sql")
    rules = parse(src.read_text(encoding="utf-8", errors="replace"))

    with OUT.open("w", encoding="utf-8") as f:
        yaml.safe_dump(rules, f, allow_unicode=True, sort_keys=False, width=100)

    risky = [k for k, v in rules.items() if v["whole_word"]]
    print(f"flag {len(rules)} ตัว · keyword {sum(len(v['words']) for v in rules.values())} คำ")
    print(f"ตั้ง whole_word ไว้ {len(risky)} ตัว: {', '.join(risky)}")
    print(f"เขียนแล้ว: {OUT}")


if __name__ == "__main__":
    main()
