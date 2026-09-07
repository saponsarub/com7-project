# Git & GitHub

> **หมายเหตุที่มา:** วิธีใช้ git/GitHub ของ repo `my-first-project` — **ค่าที่เขียนไว้คือของจริงที่ตั้งอยู่บนเครื่อง `Sapon.S` ณ 2026-09-03** ส่วนคำสั่งทั่วไปเป็นความรู้ทั่วไปของ git

repo นี้เก็บทั้ง **vault** (`COM7-Knowledge-Base/`) · **สคริปต์** (`scripts/`) · **SQL** (`sql/`)

---

## ตั้ง SSH key — กรณีมี 2 GitHub account

เครื่องนี้ใช้ 2 บัญชี: **ส่วนตัว** (`saponsarub@gmail.com`) และ **บริษัท** (`sapon.s@comseven.com`)

GitHub ไม่ยอมให้ key ดอกเดียวผูกกับ 2 บัญชี จึงต้องสร้าง 2 ดอกแล้วแยกด้วย SSH config

### 1 · สร้าง key

```bash
# ดอกแรก (ส่วนตัว) — ใช้ชื่อไฟล์ default
ssh-keygen -t ed25519 -C "saponsarub@gmail.com"

# ดอกที่สอง (บริษัท) — ต้องตั้งชื่อไฟล์เอง ไม่งั้นทับดอกแรก
ssh-keygen -t ed25519 -C "sapon.s@comseven.com" -f C:\Users\Sapon.S\.ssh\id_ed25519_work
```

**`-f` ขาดไม่ได้สำหรับดอกที่สอง** — ไม่ใส่แล้วกด Enter ผ่าน จะเขียนทับดอกแรกทันที

### 2 · เอา public key ไปใส่ใน GitHub

```bash
cat ~/.ssh/id_ed25519.pub          # ของส่วนตัว
cat ~/.ssh/id_ed25519_work.pub     # ของบริษัท
```

GitHub → **Settings → SSH and GPG keys → New SSH key** — ต้องล็อกอินด้วยบัญชีที่ตรงกับ key ดอกนั้น

> ใส่ไฟล์ `.pub` เท่านั้น · **ไฟล์ที่ไม่มี `.pub` คือ private key ห้ามส่งให้ใครและห้ามขึ้น git**

### 3 · ไฟล์ `~/.ssh/config` ที่ใช้อยู่จริง

```
Host joe
    HostName github.com
    User git
    IdentityFile C:\Users\Sapon.S\.ssh\id_ed25519

Host com7
    HostName github.com
    User git
    IdentityFile C:\Users\Sapon.S\.ssh\id_ed25519_work
```

**`joe` กับ `com7` เป็นชื่อเล่นที่ตั้งเอง** — เวลาใช้งานเขียน `git@joe:` แทน `git@github.com:` แล้ว ssh จะหยิบ key ดอกที่ถูกให้เอง

### 4 · ทดสอบ

```bash
ssh -T git@joe      # ควรตอบชื่อบัญชีส่วนตัว
ssh -T git@com7     # ควรตอบชื่อบัญชีบริษัท
```

**ต้องทดสอบด้วยชื่อเล่น ไม่ใช่ `ssh -T git@github.com`** — เพราะ `git@github.com` ไม่ตรงกับ Host ไหนใน config เลย ssh จะเดา key เอง อาจได้บัญชีผิด

ข้อความ `successfully authenticated, but GitHub does not provide shell access` = **สำเร็จแล้ว** ไม่ใช่ error

---

## ตั้งชื่อผู้เขียน — จุดที่พลาดง่ายที่สุด

```bash
# ค่ากลาง ใช้กับทุก repo ที่ไม่ได้ตั้งเฉพาะ
git config --global user.name  "Sarub Sapon"
git config --global user.email "sapon.s@comseven.com"

# repo ส่วนตัว ตั้งทับเฉพาะ repo นั้น (รันในโฟลเดอร์ repo)
git config user.email "saponsarub@gmail.com"
```

**SSH key คุมว่า push ได้ไหม · `user.email` คุมว่าชื่อใครขึ้นบน commit** — คนละเรื่องกัน

ลืมตั้ง per-repo จะได้ commit ที่ **push ขึ้นบัญชีส่วนตัว แต่ชื่อผู้เขียนเป็นอีเมลบริษัท** ซึ่งแก้ย้อนหลังยาก

### เช็คก่อน commit ครั้งแรกของ repo ใหม่เสมอ

```bash
git config user.email
git config --global user.email
```

**สถานะปัจจุบันของ repo นี้ — ถูกต้องแล้ว**

| | |
|---|---|
| global | `sapon.s@comseven.com` |
| repo `my-first-project` | `saponsarub@gmail.com` |
| remote | `git@joe:saponsarub/my-first-project.git` |

---

## Remote

```bash
git remote -v                                              # ดูของปัจจุบัน
git remote set-url origin git@joe:saponsarub/repo.git      # ชี้ไปบัญชีส่วนตัว
git remote set-url origin git@com7:org/repo.git            # ชี้ไปบัญชีบริษัท
git clone git@com7:org/repo.git                            # clone ด้วยบัญชีบริษัท
```

**ต้องใช้ชื่อเล่น (`joe` / `com7`) ไม่ใช่ `github.com`** ไม่งั้น ssh หยิบ key ผิดดอก

---

## คำสั่งใช้ประจำ

```bash
git status                    # ตอนนี้มีอะไรเปลี่ยนบ้าง
git diff                      # ดูว่าเปลี่ยนตรงไหน (ยังไม่ add)
git diff --cached             # ดูของที่ add แล้ว
git add <file>                # เลือกทีละไฟล์
git add -A                    # ทั้งหมด
git commit -m "ข้อความ"
git push
git pull
git log --oneline -10
git log --oneline --graph --all -20
```

**ดูประวัติของไฟล์เดียว**

```bash
git log --oneline -- "COM7-Knowledge-Base/04_DataLake/Redshift.md"
git log -p -- <file>          # เห็น diff ทุก commit ของไฟล์นั้น
```

---

## สาขาและ Pull Request

```bash
git switch -c feature/redshift-notes    # สร้างสาขาใหม่และย้ายไป
git switch main                          # กลับ main
git branch                               # ดูสาขาทั้งหมด
git push -u origin feature/redshift-notes

git merge feature/redshift-notes         # รวมเข้า main (ต้องอยู่ที่ main ก่อน)
git branch -d feature/redshift-notes     # ลบสาขาที่ merge แล้ว
```

**ผ่าน GitHub CLI**

```bash
gh pr create --title "เพิ่มโน้ต Redshift" --body "..."
gh pr list
gh pr view --web
```

---

## แก้เมื่อพลาด

| อยากทำ | คำสั่ง |
|---|---|
| ยกเลิกการแก้ไฟล์ที่ยังไม่ add | `git restore <file>` |
| เอาไฟล์ออกจาก staging (ไม่ลบการแก้) | `git restore --staged <file>` |
| แก้ข้อความ commit ล่าสุด (**ยังไม่ push**) | `git commit --amend -m "ใหม่"` |
| ถอย commit ล่าสุดแต่เก็บไฟล์ไว้ | `git reset --soft HEAD~1` |
| ถอย commit และทิ้งการแก้ทั้งหมด | `git reset --hard HEAD~1` ⚠️ |
| ยกเลิก commit ที่ **push ไปแล้ว** | `git revert <sha>` |
| พักงานที่ทำค้างไว้ | `git stash` แล้ว `git stash pop` |
| กู้ของที่หาย | `git reflog` แล้ว `git reset --hard <sha>` |

**`reset` ใช้กับ commit ที่ยังไม่ push · `revert` ใช้กับที่ push ไปแล้ว** — reset ของที่คนอื่นดึงไปแล้วจะทำให้ประวัติเขาพัง

---

## บทเรียนจริง — ไฟล์ใหญ่ทำให้ push ไม่ผ่าน

**เกิดขึ้นจริง 2026-09-03**

```
remote: error: File COM7-Knowledge-Base/.../K2 - OD6 Selection Logic.md is 136.77 MB;
        this exceeds GitHub file size limit of 100.00 MB
! [remote rejected] main -> main (pre-receive hook declined)
```

**สาเหตุ** — ไฟล์โน้ตมีเนื้อหาซ้ำตัวเอง 31,836 รอบ (1.46 ล้านบรรทัด) จากอุบัติเหตุตอนแก้ไฟล์

**จุดสำคัญ: ไฟล์บนดิสก์ปกติแล้ว แต่ commit เก่ายังพกเวอร์ชันบวมไปด้วย** — `git push` ส่งทั้งประวัติ ไม่ใช่แค่ไฟล์ปัจจุบัน

### หาว่า blob ใหญ่อยู่ไหน

```bash
git rev-list --objects --all |
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' |
  awk '$1=="blob" && $3 > 5000000 {printf "%8.1f MB  %s\n", $3/1048576, $4}' | sort -rn
```

**ดูขนาดไฟล์เดียวกันในแต่ละ commit**

```bash
for c in <sha1> <sha2> <sha3>; do
  b=$(git rev-parse "$c:path/to/file.md")
  echo "$c  $(git cat-file -s "$b") bytes"
done
```

### แก้ — ยุบ commit ที่ยังไม่ push

ใช้ได้เมื่อ **commit ที่มีปัญหายังไม่ push** และเนื้อหาปัจจุบันถูกต้องแล้ว

```bash
git branch backup-before-squash          # กันเหนียว
git reset --soft <commit-ที่-push-แล้ว>  # ไม่แตะไฟล์ในเครื่องเลย
git commit -m "ข้อความรวม"

# ตรวจก่อน push ว่าไม่มี blob ใหญ่เหลือ
git rev-list --objects <base>..HEAD |
  git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)' |
  awk '$1=="blob"' | sort -k2 -rn | head -3

git push
git branch -D backup-before-squash       # ลบ backup หลัง push ผ่าน
```

`--soft` = เก็บไฟล์ทุกตัวไว้เหมือนเดิม เปลี่ยนแค่ประวัติ commit

**ถ้า push ไปแล้ว** ต้องใช้ `git filter-repo` เขียนประวัติใหม่ทั้ง repo ซึ่งกระทบทุกคนที่ clone ไป — ยากกว่ามาก **จึงควรกันไว้ตั้งแต่ต้น**

### กันไม่ให้เกิดอีก — pre-commit hook

ติดตั้งไว้แล้วที่ `.git/hooks/pre-commit`

```sh
#!/bin/sh
LIMIT=5242880
big=$(git diff --cached --name-only --diff-filter=ACM | while read -r f; do
  if [ -f "$f" ] && [ "$(wc -c < "$f")" -gt "$LIMIT" ]; then
    printf '  %s (%s MB)\n' "$f" "$(( $(wc -c < "$f") / 1048576 ))"
  fi
done)
if [ -n "$big" ]; then
  echo "ยกเลิก commit - เจอไฟล์ใหญ่เกิน 5 MB:"
  echo "$big"
  echo "ถ้าตั้งใจจริงให้ใช้: git commit --no-verify"
  exit 1
fi
```

```bash
chmod +x .git/hooks/pre-commit
```

> **hook อยู่ใน `.git/` จึงไม่ติดไปกับ repo** — เครื่องใหม่ต้องติดตั้งเอง

---

## ข้อมูลที่ห้ามขึ้น git

`.gitignore` ของ repo กันไว้แล้ว

```
data/          *.xlsx  *.xls  *.csv     ไฟล์ข้อมูลลูกค้าจริง
.env  .env.*  *credential*  *secret*   credential
__pycache__/  .venv/  .ipynb_checkpoints/
```

**ยกเว้น** `!COM7-Knowledge-Base/**/_raw/*.csv` — metadata ของฐานที่ไม่มี PII ใช้เป็น data dictionary ได้

| ห้ามขึ้น git | ดูเพิ่ม |
|---|---|
| ชื่อ · เลขบัตรประชาชน · ที่อยู่ · เบอร์โทร | [[Consent & PDPA]] |
| **ไฟล์ผลลัพธ์จาก `k2_termination.py`** — มี PII เต็ม | [[K2 - Termination Letter How-To]] |
| Pre-Shared Key ของ VPN · รหัสผ่าน | [[Network & VPN]] |
| private key (`id_ed25519` ที่ไม่มี `.pub`) | |

**ถ้าเผลอ commit ไปแล้ว** — ลบไฟล์อย่างเดียวไม่พอ ต้องล้างจากประวัติด้วย และ **ถือว่า credential นั้นรั่วแล้ว ต้องเปลี่ยนใหม่ทันที**

---

## Troubleshooting

| อาการ | สาเหตุ · วิธีแก้ |
|---|---|
| `Permission denied (publickey)` | ใช้ `git@github.com` แทนชื่อเล่น หรือยังไม่ได้ใส่ public key ใน GitHub · ทดสอบด้วย `ssh -T git@joe` |
| push แล้วขึ้นชื่อบัญชีผิด | ลืม `git config user.email` เฉพาะ repo |
| `failed to push some refs` | remote มี commit ใหม่กว่า → `git pull --rebase` แล้ว push ใหม่ |
| `pre-receive hook declined` + file size | ไฟล์ใหญ่ในประวัติ → ดูหัวข้อบทเรียนจริงข้างบน |
| commit หายหลัง `reset --hard` | `git reflog` แล้ว `git reset --hard <sha>` |
| แก้ ssh config แล้วยังไม่มีผล | ตรวจ path ใน `IdentityFile` ว่าตรงกับไฟล์จริง · `ssh -v git@joe` ดูว่าหยิบ key ดอกไหน |

---

## เชื่อมกับโน้ตอื่น

[[Consent & PDPA]] · [[Network & VPN]] · [[K2 - Termination Letter How-To]] · [[Source Inventory]] · [[Home]]
