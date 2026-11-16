# -*- coding: utf-8 -*-
"""ส่งข้อความเข้า LINE OA ด้วย Messaging API (push message)

env (ห้ามเขียนลงไฟล์ / ห้าม commit)
  LINE_CHANNEL_TOKEN   Channel access token (long-lived) ของ LINE OA ทีม EV7
  LINE_TO              userId / groupId ปลายทาง (ขึ้นต้น U… / C…)

หมายเหตุ: push message นับโควตาข้อความของ OA ต่อผู้รับ → รวมรถทุกคันเป็นข้อความสรุปวันละชุด
"""
import os
import uuid

import requests

API = "https://api.line.me/v2/bot/message/push"


def push(texts, to=None, token=None):
    token = token or os.environ.get("LINE_CHANNEL_TOKEN")
    to = to or os.environ.get("LINE_TO")
    if not (token and to):
        raise SystemExit("ต้องตั้ง env LINE_CHANNEL_TOKEN และ LINE_TO ก่อนส่งจริง")
    for i in range(0, len(texts), 5):                     # 1 request ส่งได้สูงสุด 5 ข้อความ
        body = {"to": to, "messages": [{"type": "text", "text": t[:5000]} for t in texts[i:i + 5]]}
        key = str(uuid.uuid4())                           # ส่งซ้ำด้วย key เดิมได้ไม่เบิ้ล
        for attempt in range(3):
            r = requests.post(API, json=body, timeout=30,
                              headers={"Authorization": f"Bearer {token}", "X-Line-Retry-Key": key})
            if r.status_code == 200 or r.status_code == 409:   # 409 = key นี้ส่งสำเร็จไปแล้ว
                break
            if r.status_code < 500 and r.status_code != 429:
                raise RuntimeError(f"LINE push ล้มเหลว {r.status_code}: {r.text[:300]}")
        else:
            raise RuntimeError(f"LINE push ล้มเหลวหลังลอง 3 ครั้ง: {r.status_code} {r.text[:300]}")
