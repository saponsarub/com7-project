# นับแถวจากไฟล์จริงบน S3 แล้วเติมกลับเข้า log ของ ingest
# ถูกเรียกแบบ async จาก com7-ingest-googlesheet-ev7 หลังเขียน log เสร็จ
# เอกสาร: docs/googlesheet-to-s3.md

import csv
import io
import os
import urllib.parse

import boto3

VERSION = "2.1.0"

s3 = boto3.client("s3")

# คอลัมน์ที่ฟังก์ชันนี้เติม
COL_S3_ROWS = "S3_row_count"
COL_STATUS = "Status_row_count"
COL_SRC_ROWS = "Table_row count"
COL_KEY = "S3_Key"
COL_ETAG = "Etag"
COL_TABLE_STATUS = "Job_status"

MAX_BYTES = int(os.environ.get("MAX_BYTES", str(200 * 1024 * 1024)))


def count_rows(bucket, key):
    """นับแถว CSV จากไฟล์บน S3 · อ่านผ่าน csv.reader ไม่ใช่นับ newline

    เซลล์ที่มีการขึ้นบรรทัดใหม่ (ที่อยู่ที่คนพิมพ์ในชีต) จะถูกครอบด้วย "
    การนับ \\n ตรง ๆ จะได้เกินจริง
    """
    body = s3.get_object(Bucket=bucket, Key=key)["Body"]
    text = io.TextIOWrapper(body, encoding="utf-8-sig", newline="")
    n = sum(1 for _ in csv.reader(text))
    return max(n - 1, 0)          # ลบบรรทัดหัวตาราง


def parse_event(event):
    """รับได้ 2 แบบ - S3 Event Notification และเรียกตรงตอนทดสอบ

    S3 ส่ง key มาแบบ URL-encoded ต้อง unquote ก่อน
    """
    recs = (event or {}).get("Records") or []
    if recs and "s3" in recs[0]:
        s3ev = recs[0]["s3"]
        return (s3ev["bucket"]["name"],
                urllib.parse.unquote_plus(s3ev["object"]["key"]))

    bucket = (event or {}).get("log_bucket")
    key = (event or {}).get("log_key")
    if not (bucket and key):
        raise Exception(
            "event ไม่ถูกต้อง - ต้องเป็น "
            '{"log_bucket": "...", "log_key": "ingest-log/.../<run_id>.csv"} '
            "หรือ S3 Event Notification | ได้มา: " + str(event)[:200])
    return bucket, key


def lambda_handler(event, context):
    print(f"========== rowcount START v{VERSION} ==========")

    log_bucket, log_key = parse_event(event)
    print("log:", f"s3://{log_bucket}/{log_key}")

    raw = s3.get_object(Bucket=log_bucket, Key=log_key)["Body"].read()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    fields = list(rows[0].keys()) if rows else []

    if not rows:
        print("log ว่าง - ไม่มีอะไรให้นับ")
        return {"statusCode": 200, "counted": 0}

    # แถวที่ควรนับ = tab ที่ ingest สำเร็จ
    ok_rows = [r for r in rows if r.get(COL_TABLE_STATUS) == "SUCCESS"]

    if not ok_rows:
        # ไม่ใช่ "นับไปแล้ว" แต่ "หาแถวที่ต้องนับไม่เจอ" - คนละเรื่องกัน
        found = sorted({str(r.get(COL_TABLE_STATUS)) for r in rows})
        print(f"ไม่มีแถวที่ {COL_TABLE_STATUS} = SUCCESS")
        print(f"  ค่าที่พบในไฟล์: {found}")
        print(f"  คอลัมน์ในไฟล์: {fields}")
        print("  -> Lambda 1 ที่ deploy อยู่เขียน log คนละรูปแบบกับที่ตัวนี้คาด")
        return {"statusCode": 400, "reason": "no rows with Job_status=SUCCESS",
                "found_status": found, "rows": len(rows)}

    # กัน loop: เราเขียนทับไฟล์เดิม S3 จึงยิง event มาอีกรอบ
    todo = [r for r in ok_rows if not r.get(COL_S3_ROWS)]
    if not todo:
        print(f"นับไปแล้วครบ {len(ok_rows)} แถว - ข้าม")
        return {"statusCode": 200, "skipped": "already counted",
                "rows": len(ok_rows)}

    print(f"ต้องนับ {len(todo)} จาก {len(ok_rows)} แถว")

    counted = skipped = mismatch = 0

    for r in rows:
        key = r.get(COL_KEY, "")
        if r.get(COL_TABLE_STATUS) != "SUCCESS" or not key:
            continue
        if r.get(COL_S3_ROWS):        # นับไปแล้วจากรอบก่อน
            continue

        bucket = r.get("Target_Bucket") or os.environ.get("DATA_BUCKET", "")
        if not bucket:
            print(f"  SKIP {key} - ไม่รู้ bucket")
            skipped += 1
            continue

        try:
            head = s3.head_object(Bucket=bucket, Key=key)

            # ไฟล์ถูกทับไปแล้วหลัง ingest - นับไปก็ไม่ตรงกับ log แถวนี้
            if r.get(COL_ETAG) and head["ETag"].strip('"') != r[COL_ETAG]:
                r[COL_STATUS] = "STALE"
                skipped += 1
                print(f"  SKIP {key} - etag ไม่ตรง ไฟล์ถูกทับแล้ว")
                continue

            if head["ContentLength"] > MAX_BYTES:
                r[COL_STATUS] = "SKIPPED_TOO_LARGE"
                skipped += 1
                print(f"  SKIP {key} - {head['ContentLength']} bytes เกินเพดาน")
                continue

            n = count_rows(bucket, key)
            r[COL_S3_ROWS] = n

            src = r.get(COL_SRC_ROWS, "")
            if str(src).isdigit():
                same = int(src) == n
                r[COL_STATUS] = "MATCH" if same else "MISMATCH"
                if not same:
                    mismatch += 1
                    print(f"  MISMATCH {key} - ต้นทาง {src} != S3 {n}")
            else:
                r[COL_STATUS] = "UNKNOWN"

            counted += 1
            print(f"  OK   {key:52} {n:>8} rows  {r[COL_STATUS]}")

        except Exception as e:
            r[COL_STATUS] = f"ERROR: {type(e).__name__}"
            skipped += 1
            print(f"  FAIL {key} -> {type(e).__name__}: {e}")

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator=chr(10),
                       extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

    s3.put_object(
        Bucket=log_bucket,
        Key=log_key,
        Body=buf.getvalue().encode("utf-8-sig"),
        ContentType="text/csv; charset=utf-8",
    )

    print(f"---------- SUMMARY ----------")
    print(f"counted {counted} · skipped {skipped} · mismatch {mismatch}")
    print("========== rowcount DONE ==========")

    return {
        "statusCode": 200 if not mismatch else 207,
        "log_key": log_key,
        "counted": counted,
        "skipped": skipped,
        "mismatch": mismatch,
    }
