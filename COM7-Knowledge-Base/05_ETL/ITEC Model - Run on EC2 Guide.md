# ITEC Model — Run on EC2 Guide

> คู่มือรันโมเดลจัดหมวดสินค้าบน EC2 GPU
> บันทึก 2026-09-14 · **แก้ 2026-09-15** · คู่กับ `scripts/itec/category/itec_recategorization.ipynb`
> เกี่ยวข้อง → [[ITEC Category Toolkit]] · [[ITEC Category Model (ML)]] · [[Network & VPN]]

---

# 🛑 ap-southeast-7 ไม่มี GPU instance ขายเลย — ยืนยันแล้ว 2026-09-15

```bash
aws ec2 describe-instance-type-offerings --location-type region --region ap-southeast-7 \
  --output table --query "InstanceTypeOfferings[?starts_with(InstanceType,'g')].InstanceType"
# ว่าง
```

**ทั้งคู่มือฉบับนี้เขียนบนสมมติฐานว่าไทยมี `g4dn` ซึ่งผิด**

## อาการที่เจอ อธิบายได้ทุกข้อจากเรื่องนี้

| เจอ | สาเหตุจริง |
|---|---|
| โควตา G and VT เป็น `0.0` | **ไม่มีของให้ใช้ ก็ไม่มีโควตา** |
| ขอเพิ่มแล้วได้ `CASE_CLOSED` ไม่บอกผล | ปิดเคสเพราะให้ไม่ได้ ไม่ใช่เพราะปฏิเสธ |
| หา `g4dn.xlarge` ใน Console ไม่เจอ | ไม่มีจริง |

> ⚠️ **บทเรียน** — ตอนเช็คครั้งแรกผมใช้คำสั่งที่ชี้ไป `us-east-1` แล้วเข้าใจว่าไทยมีด้วย
> **เช็ค availability ของ region ที่จะใช้จริงก่อนเสมอ** ก่อนจะไปยื่นโควตาหรือสร้างอะไร

## ใช้อะไรแทน

| | สถานะ | หมายเหตุ |
|---|---|---|
| **Kaggle Notebooks** ⭐ | **ฟรี 30 ชม./สัปดาห์ · T4 x2** | dataset อยู่ถาวร ไม่ต้องอัปใหม่ทุกรอบ |
| Google Colab | ฟรีแต่**โควตาหมดแล้ว** (2026-09-15) | Colab Pro ~$10/เดือน |
| เครื่องตัวเอง (CPU) | ใช้ได้ | TF-IDF ได้ `f1_macro 0.9336` ใน 160 วินาที |
| EC2 `ap-southeast-1` สิงคโปร์ | ต้องเริ่มใหม่หมด | **โควตา · AMI · key pair · SG ผูกกับ region ทั้งหมด** |

**โน้ตบุ๊กรันได้ทั้ง local · Colab · Kaggle ด้วยไฟล์เดียว** — Cell 1 ตรวจเอง → [[ITEC Category Toolkit]]

**ส่วนที่เหลือของคู่มือนี้ยังใช้ได้ถ้าย้ายไปสิงคโปร์** แค่เปลี่ยน region และหา AMI ใหม่

---

## ทำไมต้อง EC2 GPU

bge-m3 embed 216,009 แถว บน **CPU ~14 ชม.** → บน **GPU (g4dn) ~30 นาที** · ค่าใช้จ่าย ~$0.15-0.30 (spot)

| Instance          | GPU       | On-Demand  | Spot       | เหมาะกับ                     |
| ----------------- | --------- | ---------- | ---------- | ---------------------------- |
| **g4dn.xlarge** ⭐ | T4 16GB   | ~$0.53/ชม. | ~$0.15/ชม. | embedding + fine-tune งานนี้ |
| g5.xlarge         | A10G 24GB | ~$1.01/ชม. | ~$0.30/ชม. | fine-tune ที่แรงขึ้น         |

> ราคา us-east-1 · ap-southeast (สิงคโปร์/กรุงเทพ) แพงกว่า ~10-20%

---

## ขั้น 0 · เตรียมก่อน — ทำจริงแล้ว 2026-09-14

| # | ทำอะไร | สถานะ |
|---|---|---|
| 1 | Key pair สำหรับ SSH | ✅ |
| 2 | Security Group เปิด SSH 22 จาก My IP | ✅ |
| 3 | ข้อมูล `dim_item_itec.csv` อยู่บน S3 | ✅ |
| 4 | **IAM instance profile** ที่มีสิทธิ์ S3 | ❗ ต้องสร้างใหม่ |
| 5 | **Service Quota ของ GPU** | ❗ **เป็น 0 ต้องขอเพิ่ม** |

> ⚠️ **PDPA:** ItemName เป็นชื่อสินค้า ไม่ใช่ PII → รันบน EC2 ได้ · ถ้ามี PII ต้องอยู่ใน VPC COM7 เท่านั้น (ดู [[Consent & PDPA]])

### 0.1 · Security Group

```bash
myip=$(curl -s https://checkip.amazonaws.com)
sg=$(aws ec2 create-security-group --group-name itec-embed-sg \
       --description "SSH for ITEC embedding" --region ap-southeast-7 \
       --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id $sg \
       --protocol tcp --port 22 --cidr "$myip/32" --region ap-southeast-7
```

**`/32` เท่านั้น ห้าม `0.0.0.0/0`** · **IP เปลี่ยน = SSH ค้างโดยไม่มี error** ต้อง `authorize` ใหม่

### 0.2 · IAM instance profile — ขาดไม่ได้

**ไม่มีตัวนี้ `aws s3 cp` บน instance จะขึ้น `Unable to locate credentials`**

ตรวจก่อนว่ามีของเดิมใช้ได้ไหม

```bash
for p in $(aws iam list-instance-profiles --query "InstanceProfiles[].InstanceProfileName" --output text); do
  r=$(aws iam get-instance-profile --instance-profile-name $p --query "InstanceProfile.Roles[0].RoleName" --output text)
  echo "== $p -> $r"; aws iam list-attached-role-policies --role-name "$r" --query "AttachedPolicies[].PolicyName" --output text
done
```

> **ผลจริง 2026-09-14** — profile เดิม 3 ตัว (`com7-cert-workstation` · `com7-sql-bridge` · `IAMInstanceRole`) **ไม่มีสิทธิ์ S3 เลยสักตัว** มีแต่ `AmazonSSMManagedInstanceCore` → ต้องสร้างใหม่

```bash
aws iam create-role --role-name itec-embed-role \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name itec-embed-role --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam attach-role-policy --role-name itec-embed-role --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam create-instance-profile --instance-profile-name itec-embed-profile
aws iam add-role-to-instance-profile --instance-profile-name itec-embed-profile --role-name itec-embed-role
```

**ต้องเป็น `S3FullAccess` ไม่ใช่ ReadOnly** เพราะต้องอัป embedding และ model กลับขึ้น S3
**IAM propagate ~10 วินาที** — สร้างเสร็จ launch ทันทีอาจเจอ `Invalid IAM Instance Profile name`

> **ทั้ง 3 profile เดิมมี SSM เหมือนกันหมด = องค์กรใช้ Session Manager เป็นมาตรฐาน ไม่ใช่ SSH** จึงใส่ SSM ไว้ด้วย เข้าเครื่องได้โดยไม่ต้องเปิด port 22

### 0.3 · ⚠️ Service Quota — ด่านจริงที่บล็อกทุกอย่าง

**บัญชีที่ไม่เคยใช้ GPU จะมีโควตา = 0 · launch ไปจะได้ `VcpuLimitExceeded`**

```bash
aws service-quotas list-service-quotas --service-code ec2 --region ap-southeast-7 \
  --output table --query "Quotas[?contains(QuotaName,'G and VT')].[QuotaName,QuotaCode,Value]"
```

> **ผลจริง 2026-09-14 — เป็น `0.0` ทั้งสองตัว**
> ```
> All G and VT Spot Instance Requests    0.0
> Running On-Demand G and VT instances   0.0
> ```

**มี 2 โควตาแยกกัน ขออันเดียวไม่พอ**

| โควตา | ใช้ตอน |
|---|---|
| Running On-Demand G and VT instances | launch ปกติ |
| All G and VT Spot Instance Requests | launch แบบ Spot |

```bash
aws service-quotas request-service-quota-increase --service-code ec2 \
  --quota-code <รหัส> --desired-value 4 --region ap-southeast-7
```

**ขอ 4 พอ** — `g4dn.xlarge` = 4 vCPU · ขอเยอะจะถูกถามเหตุผลและช้าลง · **ตัวเลขคือ vCPU ไม่ใช่จำนวนเครื่อง**

ดูสถานะ

```bash
aws service-quotas list-requested-service-quota-change-history --service-code ec2 \
  --region ap-southeast-7 --output table --query "RequestedQuotas[].[QuotaName,DesiredValue,Status]"
```

| สถานะ | หมายถึง |
|---|---|
| `PENDING` | ระบบประเมินอัตโนมัติ · อาจไม่กี่ชั่วโมง |
| `CASE_OPENED` | **AWS เปิดเคสให้คนดู** · 24–48 ชม. |

**ยื่นที่ `ap-southeast-1` คู่ไปด้วยได้** — ภูมิภาคไทยเพิ่งเปิด GPU อาจจำกัด `[อนุมาน]` · QuotaCode เป็นรหัสเดียวกันทุก region · ItemName ไม่ใช่ PII จึงออกนอก region ได้

---

## ⚠️ กับดักที่เสียเวลาไปจริง

### `--filters` บน PowerShell ทำให้ผลว่างแบบเงียบ ๆ

```powershell
# แบบนี้คืนค่าว่างทั้งที่ของมีอยู่
--filters "Name=instance-type,Values=g4dn.xlarge,g5.xlarge"
```

**คอมมาซ้อนในสตริงที่มีคอมมาอยู่แล้ว ทำให้ filter ไม่ตรงอะไรเลย และ `--output table` ไม่พิมพ์อะไรเมื่อผลว่าง**

หลงคิดว่า **ไทย สิงคโปร์ เวอร์จิเนีย ไม่มี GPU** ทั้งที่ `g4dn` มีครบทุกขนาด

**เขียนแบบนี้แทน** — ค่าเดียวต่อครั้ง หรือใช้ `--query` กรองที่เครื่อง

```bash
aws ec2 describe-instance-type-offerings --location-type availability-zone \
  --region us-east-1 --filters Name=instance-type,Values=g4dn.xlarge --output table
```

```bash
aws ec2 describe-instance-type-offerings --region ap-southeast-7 --output table \
  --query "InstanceTypeOfferings[?starts_with(InstanceType,'g4dn')].InstanceType"
```

### แยกให้ออก — "ไม่มีขาย" กับ "เราไม่มีสิทธิ์"

| คำสั่ง | ตอบอะไร |
|---|---|
| `describe-instance-type-offerings` | region นี้ **มีขายไหม** |
| `list-service-quotas` | บัญชีเรา **ใช้ได้กี่ vCPU** |

**ทั้งสองอย่างว่างหน้าตาเหมือนกัน แต่แก้คนละทาง**

### `chmod 400` ใช้ไม่ได้บน Windows

```powershell
icacls .\itec-embed.pem /inheritance:r
icacls .\itec-embed.pem /grant:r "$($env:USERNAME):R"
```

ไม่ทำจะเจอ `Permissions for 'xxx.pem' are too open. This private key will be ignored.`

---

## ขั้น 1 · สร้าง EC2 Instance

### 1.1 หา AMI

```bash
aws ec2 describe-images --owners amazon --region ap-southeast-7 \
  --filters 'Name=name,Values=Deep Learning*Ubuntu 22.04*' \
  --query "reverse(sort_by(Images,&CreationDate))[:3].[ImageId,Name]" --output table
```

AMI ที่ต้องการคือ **Deep Learning OSS Nvidia Driver AMI (Ubuntu 22.04)** — มี CUDA + PyTorch มาแล้ว ไม่ต้องลง driver เอง

### 1.2 Launch แบบ Spot

```bash
aws ec2 run-instances --region ap-southeast-7 \
  --image-id <ami-xxxx> \
  --instance-type g4dn.xlarge \
  --key-name <key> \
  --security-group-ids <sg-xxxx> \
  --iam-instance-profile Name=itec-embed-profile \
  --instance-market-options MarketType=spot \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=itec-embed}]'
```

### 1.3 ⚠️ Spot ต่างจาก On-Demand ตรงนี้

**AWS ดึงเครื่องคืนได้ทุกเมื่อ เตือนล่วงหน้า 2 นาที แล้ว terminate** · กับ `DeleteOnTermination: true` แปลว่า**ของบนเครื่องหายหมด**

```bash
curl -s http://169.254.169.254/latest/meta-data/spot/instance-action
```

`404` = ปกติ · ได้ JSON = **เหลือ 2 นาที รีบอัปขึ้น S3**

**วิธีที่ปลอดภัยกว่าคือเซฟเป็นช่วง** — embed ทีละ 20,000 แถวแล้วอัปขึ้น S3 ทันที ถูกดึงคืนก็เสียแค่ก้อนสุดท้าย

---

## ขั้น 2 · เชื่อมต่อ + เตรียม environment

### 2.1 หา IP แล้วเข้า

```bash
aws ec2 describe-instances --region ap-southeast-7 \
  --filters Name=tag:Name,Values=itec-embed Name=instance-state-name,Values=running \
  --query "Reservations[].Instances[].[InstanceId,PublicIpAddress]" --output table

ssh -i <key>.pem ubuntu@<IP>
```

**หรือเข้าโดยไม่ต้องใช้ SSH เลย** (ถ้าแนบ SSM role ไว้)

```bash
aws ssm start-session --target <i-xxxx> --region ap-southeast-7
```

ไม่ต้องมี key · ไม่ต้องเปิด port 22 · IP เปลี่ยนก็ไม่พัง

### 2.2 เช็ค GPU + ลง library

```bash
nvidia-smi                    # ต้องเห็น Tesla T4
pip install sentence-transformers scikit-learn pandas joblib pyyaml
```

### 2.3 ดึงข้อมูล + โค้ด

```bash
aws s3 cp s3://<bucket>/itec/model-input/dim_item_itec.csv .
aws s3 cp s3://<bucket>/itec/code/ . --recursive
```

---

## ขั้น 3 · รันโค้ด (embedding + เทรน)

### 3.1 รันเป็น script (แนะนำ — ไม่ต้องเปิด Jupyter)
แปลง notebook เป็น .py หรือเขียน `run.py`:
```bash
jupyter nbconvert --to script itec_recategorization_full.ipynb
python itec_recategorization_full.py
```

### 3.2 หรือเปิด Jupyter ผ่าน SSH tunnel
```bash
# บน EC2
jupyter notebook --no-browser --port=8888
# บนเครื่องคุณ (terminal ใหม่)
ssh -i key.pem -L 8888:localhost:8888 ubuntu@<ip>
# เปิด browser: http://localhost:8888
```

> บน GPU: Cell 8 จะ detect `device=cuda` อัตโนมัติ → ใช้ bge-m3 · embed 216k ~30 นาที

---

## ขั้น 4 · เทสต์

```python
# ใน notebook/script — เทสต์ subset ก่อน (Cell 7 ปลด comment)
data = data.sample(5000, random_state=42).reset_index(drop=True)
# → ดู Accuracy + Macro-F1 (Cell 11) ว่าโอเคไหม ก่อนรันเต็ม
```
- เทสต์ผ่าน → เอา comment ออก รันเต็ม 216k
- ⚡ **เซฟ embedding เป็น .npy** หลัง embed เสร็จ → จ่าย GPU ครั้งเดียว:
```python
np.save("item_embeddings.npy", X1)
aws s3 cp item_embeddings.npy s3://your-bucket/   # เก็บไว้ เทรนซ้ำบน CPU ได้
```

---

## ขั้น 5 · Fine-tune (บน GPU — ทำหลัง label สะอาด)

> ⚠️ ทำเมื่อ baseline ไม่พอ + label สะอาดแล้ว (ดู [[ITEC Category Model (ML)]])

```python
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

model = SentenceTransformer("BAAI/bge-m3", device="cuda")

# สร้างคู่ตัวอย่างจาก MyCategory ที่สะอาดแล้ว
examples = []
for cat, grp in data.groupby("MyCategory"):
    items = grp.ItemName.sample(min(len(grp), 200), random_state=0).tolist()
    for i in range(0, len(items)-1, 2):
        examples.append(InputExample(texts=[items[i], items[i+1]], label=1.0))  # หมวดเดียวกัน
# + คู่ลบ (คนละหมวด) ...

loader = DataLoader(examples, batch_size=16, shuffle=True)
loss = losses.MultipleNegativesRankingLoss(model)   # หรือ CosineSimilarityLoss
model.fit(train_objectives=[(loader, loss)], epochs=1, warmup_steps=100,
          output_path="bge-m3-itec-finetuned")
```
→ แล้วกลับไปรัน embedding + เทรน ใหม่ด้วย backbone `bge-m3-itec-finetuned` เทียบ accuracy

---

## ขั้น 6 · Dump Model + เก็บผล

```python
import joblib
joblib.dump({"backbone": backbone, "clf": clf1, "taxonomy": [...], "flag_rules": FLAG_RULES},
            "itec_category_model.joblib")
```
```bash
# อัปผลกลับ S3 ก่อนปิด instance!
aws s3 cp itec_category_model.joblib s3://your-bucket/
aws s3 cp item_embeddings.npy s3://your-bucket/
aws s3 cp suspect.csv s3://your-bucket/
aws s3 cp -r bge-m3-itec-finetuned s3://your-bucket/bge-m3-itec-finetuned/   # ถ้า fine-tune
```

---

## ขั้น 7 · ⚠️ ปิด Instance (สำคัญสุด — ลืม = เสียเงินทั้งวัน)

```bash
# วิธี 1: บน EC2
sudo shutdown -h now
# วิธี 2: EC2 Console → เลือก instance → Instance state → Terminate
```

| ลืมปิด | ค่าใช้จ่าย |
|---|---|
| g4dn.xlarge ทิ้งไว้ 1 วัน | ~$13 |
| ทิ้งไว้ 1 เดือน | ~$380 😱 |

> 💡 ตั้ง **billing alarm** หรือใช้ **auto-stop** (SageMaker Notebook มีให้) กันลืม

---

## Checklist สรุป

- [ ] สร้าง g4dn.xlarge + Deep Learning AMI (spot ถ้าประหยัด)
- [ ] SSH เข้า → `nvidia-smi` เห็น GPU → pip install
- [ ] ดึง data+code จาก S3
- [ ] เทสต์ subset 5,000 → ดู accuracy
- [ ] รันเต็ม → เซฟ embedding .npy
- [ ] (option) fine-tune หลัง label สะอาด
- [ ] dump model → อัป S3
- [ ] **Terminate instance** ✅

---

## ทางเลือกที่ง่าย/คุ้มกว่า

| | ข้อดี |
|---|---|
| **Google Colab (ฟรี)** | GPU ฟรี เทสต์ subset ก่อนได้ — เริ่มตรงนี้ถ้าแค่ทดลอง |
| **SageMaker Notebook** | ตั้ง auto-stop ได้ ลืมปิดไม่เปลืองมาก |
| **EC2 Spot** | ถูกสุด แต่อาจโดนดึงคืน |

---

## เชื่อมกับโน้ตอื่น

[[ITEC Category Model (ML)]] · [[ITEC Item Category Mapping (SQL to Python)]] · [[Network & VPN]] · [[AWS Services]] · [[Consent & PDPA]] · [[ITEC Category Toolkit]] · [[ITEC Model - Notebook Explained]]
