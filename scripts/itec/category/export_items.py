# -*- coding: utf-8 -*-
"""ดึง dim_item_itec เป็น CSV แล้วอัปขึ้น S3 สำหรับรันโมเดลบน EC2

    $env:MIS_USER="..."; $env:MIS_PWD="..."
    python scripts/itec/category/export_items.py --bucket com7-ml-itec

ไม่ใส่ --bucket = เขียนไฟล์อย่างเดียว ไม่อัป
เอกสาร: COM7-Knowledge-Base/05_ETL/ITEC Model - Run on EC2 Guide.md
"""
import argparse
import os
import sys
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass          # Jupyter/Colab ไม่มีเมธอดนี้ และไม่ต้องใช้

SQL = """
SELECT ItemId, ItemName, CategoryName, SubCategoryName, [Model/Series], Brand
FROM   rpt.dim_item_itec
"""

OUT = Path(__file__).parent / "dim_item_itec.csv"


def connect():
    import pyodbc
    user, pwd = os.environ.get("MIS_USER"), os.environ.get("MIS_PWD")
    if not user or not pwd:
        sys.exit('ต้องตั้ง credential ก่อน:  $env:MIS_USER="..."; $env:MIS_PWD="..."')
    server = os.environ.get("MIS_SERVER", "192.168.43.250,18963")
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};"
        f"UID={user};PWD={pwd};TrustServerCertificate=yes;", timeout=60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", help="S3 bucket ปลายทาง · ไม่ใส่ = ไม่อัป")
    ap.add_argument("--prefix", default="itec/model-input")
    ap.add_argument("--region", default=os.environ.get("AWS_REGION", "ap-southeast-7"))
    args = ap.parse_args()

    df = pd.read_sql(SQL, connect())
    print(f"ดึงมา {len(df):,} แถว · {len(df.columns)} คอลัมน์")

    # ชื่อสินค้ามีภาษาไทย + คอมมา + ขึ้นบรรทัดใหม่ได้
    # utf-8-sig ให้ Excel อ่านไทยออก · quoting ให้ pandas จัดการเอง
    df.to_csv(OUT, index=False, encoding="utf-8-sig", lineterminator="\n")
    size = OUT.stat().st_size
    print(f"เขียน {OUT}  ({size/1024/1024:.1f} MB)")

    empty = int(df.ItemName.isna().sum() + (df.ItemName.astype(str).str.strip() == "").sum())
    print(f"ItemName ว่าง {empty:,} แถว ({empty/len(df):.2%})")

    if not args.bucket:
        print("ไม่ได้ระบุ --bucket · ข้ามการอัป")
        return

    import boto3
    key = f"{args.prefix.strip('/')}/{OUT.name}"
    boto3.client("s3", region_name=args.region).upload_file(
        str(OUT), args.bucket, key,
        ExtraArgs={"ContentType": "text/csv; charset=utf-8"})
    print(f"อัปแล้ว s3://{args.bucket}/{key}")
    print(f"บน EC2 ดึงด้วย:  aws s3 cp s3://{args.bucket}/{key} .")


if __name__ == "__main__":
    main()
