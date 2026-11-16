"""กฎ cleansing ลูกค้าที่ใช้ร่วมกันทุก BU (CRM · ITEC-Rep · K2 · ITOS · D365 …) — ชั้น CLEAN ของ SSOT

ทุกฟังก์ชันรับ pandas Series ทีละ chunk แล้วคืนค่า normalize + ธง · ค่าที่ใช้จับคู่ถูกแปลงเป็น hash (u8)
ในหน่วยความจำ ไม่เขียน PII ลงดิสก์ · ตัวอย่างที่แสดงต้องผ่าน mask_* เสมอ

ต้นฉบับกฎมาจาก scripts/crm/crm_cleansing.ipynb (รันเต็ม 2026-11-13) + เพิ่มสำหรับ ITEC:
เลขไทย ๐-๙ · ช่องเบอร์ที่มีหลายเบอร์ · นามสกุลที่เป็นแค่ . / - · เลขผู้เสียภาษีนิติบุคคล (ขึ้นต้น 0)
"""
import re, collections
import numpy as np, pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

pd.set_option('future.infer_string', False)   # ใช้ Python re (รองรับ backreference \1) แทน Arrow regex

# ── mask สำหรับแสดงตัวอย่าง ────────────────────────────────────────────────
def mask_tok(s, keep=2):
    s = '' if s is None else str(s)
    return ' '.join(t[:keep] + '•' * min(max(len(t) - keep, 0), 4) for t in s.split(' ')) if s else ''
def mask_phone(s):
    s = '' if s is None else str(s)
    return s[:3] + 'x' * max(len(s) - 5, 0) + s[-2:] if len(s) > 5 else ('x' * len(s))
def mask_email(s):
    s = '' if s is None else str(s)
    if '@' not in s: return mask_tok(s)
    a, d = s.rsplit('@', 1)
    return a[:2] + '•••@' + d
def mask_digits(s):
    return re.sub(r'(?<=\d{3})\d', 'x', str(s))
def mask_org(s):
    """ชื่อนิติบุคคล/บัญชีร้าน: แสดงเฉพาะคำที่ทำให้ถูกจัดกลุ่ม (บริษัท · จำกัด · Banana …) ที่เหลือ mask
    เพราะชื่อบริษัทหรือชื่อร้านอาจมีชื่อคนอยู่ด้วย"""
    out = []
    for t in str(s or '').split():
        m = ORG_RE.search(t)
        out.append(('•' if m.start() else '') + m.group(0) + ('•' if m.end() < len(t) else '') if m else mask_tok(t))
    return ' '.join(out)
def pattern(s, n=20):
    """รูปแบบของค่า (9 = ตัวเลข · A = อังกฤษ · ก = ไทย) ใช้นับว่าข้อมูลผิดแบบไหน โดยไม่เปิดเผยค่า"""
    return re.sub(r'[฀-๿]', 'ก', re.sub(r'[A-Za-z]', 'A', re.sub(r'\d', '9', str(s or ''))))[:n]

# ── dictionary + regex ─────────────────────────────────────────────────────
TH_DIGIT = str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789')
TH_CONS = 'ก-ฮ'
TITLE = re.compile(
    r'^\s*(นางสาว|น\.ส\.?|นส\.|เด็กชาย|เด็กหญิง|ด\.ช\.|ด\.ญ\.|ดร\.|'
    r'นาย(?=[\s' + TH_CONS + r'])|นาง(?=[\s' + TH_CONS + r'])|คุณ(?=[\s' + TH_CONS + r'])|'
    r'mrs\.|mr\.|ms\.|dr\.|(?:mrs|mr|ms|miss|dr|khun)(?=\s))\s*', re.I)
PLACEHOLDER = {'ลูกค้า','ลูกค้าทั่วไป','ลูกค้าเงินสด','คุณลูกค้า','ไม่ระบุ','ไม่ระบุชื่อ','ไม่มี','ไม่มีชื่อ','ไม่ทราบ',
               'ทดสอบ','สมาชิก','ชื่อ','test','tester','testing','customer','cash','walkin','guest','unknown',
               'none','null','na','n/a','no','noname','name','firstname','member','user','admin','-','--','---',
               '.','..','...','x','xx','xxx','xxxx','a','aa','abc','asd'}
PLACE_PREFIX = r'^(?:test|ทดสอบ|ลูกค้า|ไม่ระบุ|ไม่มีชื่อ|customer)'
KEYBOARD     = r'qwer|wert|asdf|sdfg|dfgh|fghj|ghjk|hjkl|zxcv|xcvb|ฟหกด|หกดเ|กดเ้|ๅ/-ภ|พะัี'
JURISTIC     = (r'บริษัท|บจก|บมจ|ห้างหุ้นส่วน|หจก|หสน|จำกัด|มหาชน|co\.?\s*,?\s*ltd|company|limited|\bltd\b|'
                r'corporation|\bcorp\b|\binc\b|มูลนิธิ|สมาคม|สหกรณ์|โรงเรียน|มหาวิทยาลัย|วิทยาลัย|โรงพยาบาล|'
                r'สำนักงาน|องค์การ|องค์กร|เทศบาล|กระทรวง|ร้าน|\bshop\b|\bstore\b|school|university|hospital|foundation')
DOMAIN_FIX = {**{d: 'gmail.com' for d in ['gmail.con','gmil.com','gamil.com','gmai.com','gnail.com','gmsil.com',
                                          'gmali.com','gmal.com','gmaol.com','gmail.co','gmail.cm','gmail.om',
                                          'gmaill.com','gmial.com','gmaik.com','gmail.comm','gmail.co.th','gmeil.com']},
              **{d: 'hotmail.com' for d in ['hotmail.con','hotmial.com','hotmai.com','hotmil.com','hotmal.com',
                                            'homail.com','hmail.com','hotmali.com','hotmail.cm']}}
EMAIL_OK     = r'^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$'
EMAIL_DUMMY  = r'^(?:no|none|noemail|nomail|test|x+|na|abc|a|-+|null|0+)@|@(?:example|test|xxx)\.com$'
INTERNAL     = r'\bID\d{2,}|บานาน่า|banana|studio\s?7|สตูดิโอ\s?7|comseven|คอมเซเว่น|\bbnn\b'
COMPANY_DOM  = r'@(?:[a-z0-9\-]+\.)*(?:comseven\.com|studio7thailand\.com)$'
PHONE_DUMMY  = r'(\d)\1{6,}|^0123456789$|^0812345678$|^0987654321$'
PHONE_SEP    = r'[,/;|]|\s{2,}|\bหรือ\b|\bor\b'
LAST_EMPTY   = r'[\s.\-_/*]*'
ORG_RE       = re.compile(JURISTIC + '|' + INTERNAL, re.I)

# ชั้นของตัวอักษรต้นชื่อ ไทย ↔ อังกฤษ (กฎข้ามภาษา R6)
TH2C = {**dict.fromkeys('กขฃคฅฆ','K'), 'ง':'N', **dict.fromkeys('จฉชฌ','J'), 'ซ':'S', 'ญ':'Y', 'ฎ':'D',
        **dict.fromkeys('ฏฐฑฒตถทธ','T'), 'ณ':'N', 'ด':'D', 'น':'N', 'บ':'B', **dict.fromkeys('ปผพภ','P'),
        **dict.fromkeys('ฝฟ','F'), 'ม':'M', 'ย':'Y', **dict.fromkeys('รฤ','R'), **dict.fromkeys('ลฦฬ','L'),
        'ว':'W', **dict.fromkeys('ศษส','S'), **dict.fromkeys('หฮ','H'), 'อ':'A'}
EN2C = {**dict.fromkeys('KGQ','K'), **dict.fromkeys('CJ','J'), **dict.fromkeys('SZX','S'), 'D':'D', 'T':'T',
        'B':'B', 'P':'P', 'F':'F', 'M':'M', 'N':'N', 'Y':'Y', 'R':'R', 'L':'L', **dict.fromkeys('WV','W'),
        'H':'H', **dict.fromkeys('AEIOU','A')}
TH_FIRST = r'^[เแโใไ]?(?:ห(?=[งญนมยรลว]))?([ก-ฮ])'
CLS = {c: i + 1 for i, c in enumerate('KJSDTBPFMNYRLWHA')}

STATUS = {0: 'person', 1: 'no-identity', 2: 'juristic', 3: 'junk-name', 4: 'internal'}


# ── Name standardization ──────────────────────────────────────────────────
def clean_names(first, last, title_col=None):
    f0 = first.fillna('').astype(str); l0 = last.fillna('').astype(str)
    f = f0.str.replace(r'\s+', ' ', regex=True).str.strip()
    l = l0.str.replace(r'\s+', ' ', regex=True).str.strip()
    last_ph = (l != '') & l.str.fullmatch(LAST_EMPTY)                 # นามสกุล '.' '-' = ไม่ได้กรอก
    l = l.where(~last_ph, '')
    t = f.str.extract(TITLE, expand=False)
    f = f.str.replace(TITLE, '', regex=True)
    t2 = f.str.extract(TITLE, expand=False)                            # คำนำหน้าซ้อน เช่น 'คุณ นาย'
    f = f.str.replace(TITLE, '', regex=True).str.strip()
    title = t.fillna(t2)
    title_in = title.notna()
    if title_col is not None:
        title = title.fillna(title_col.replace('', np.nan))
    split = (l == '') & f.str.contains(' ', regex=False)               # ชื่อ+นามสกุลอยู่ช่องเดียว
    if split.any():
        p = f[split].str.split(' ', n=1)
        f.loc[split] = p.str[0]; l.loc[split] = p.str[1]
    dupl = (l != '') & pd.Series([a.endswith(' ' + b) for a, b in zip(f, l)], index=f.index)
    if dupl.any():
        f.loc[dupl] = [a[:-len(b) - 1] for a, b in zip(f[dupl], l[dupl])]
    middle = f.str.contains(' ', regex=False)
    th = f.str.contains('[ก-๏]'); en = f.str.contains('[A-Za-z]')
    lang = np.select([th & ~en, en & ~th, th & en], [1, 2, 3], 0).astype('u1')
    lth = l.str.contains('[ก-๏]'); len_ = l.str.contains('[A-Za-z]')
    key = (f + l).str.replace(r'[\s.\-]', '', regex=True).str.lower()
    fk = f.str.replace(r'[\s.\-]', '', regex=True).str.lower()
    reason = np.select(
        [fk == '',
         fk.isin(PLACEHOLDER) | fk.str.contains(PLACE_PREFIX),
         f.str.contains(r'[0-9๐-๙]'),
         ~f.str.contains('[A-Za-zก-ฮ]'),
         fk.str.contains(r'(.)\1\1'),
         fk.str.contains(KEYBOARD),
         (lang == 2) & fk.str.fullmatch(r'[bcdfghjklmnpqrstvwxz]{4,}'),
         fk.str.len() < 2],
        ['empty/title-only', 'placeholder', 'digit', 'no-letter', 'repeat-char', 'keyboard', 'no-vowel', 'too-short'], '')
    full = (f + ' ' + l).str.strip()
    return dict(first=f, last=l, title=title, title_in=title_in, split=split, dup_last=dupl, middle=middle, lang=lang,
                last_lang=np.select([lth & ~len_, len_ & ~lth], [1, 2], 0), key=key, junk=pd.Series(reason, index=f.index),
                last_placeholder=last_ph, juristic=full.str.contains(JURISTIC, case=False),
                internal=full.str.contains(INTERNAL, case=False),
                same_fl=(fk != '') & (fk == l.str.replace(r'[\s.\-]', '', regex=True).str.lower()))


# ── Contact validation ────────────────────────────────────────────────────
def clean_phone(s):
    raw = s.fillna('').astype(str).str.translate(TH_DIGIT)
    multi = raw.str.contains(PHONE_SEP) & (raw.str.replace(r'\D', '', regex=True).str.len() > 10)
    first = raw.str.split(PHONE_SEP, n=1, regex=True).str[0].where(multi, raw)  # หลายเบอร์ → ใช้เบอร์แรก
    d = first.str.replace(r'\D', '', regex=True)
    glued = (d.str.len() >= 19) & d.str[:10].str.fullmatch(r'0[689]\d{8}')      # 2 เบอร์ติดกันไม่มีตัวคั่น
    d = d.where(~glued, d.str[:10]); multi = multi | glued
    had_sym = first.str.contains(r'\D') & (d != '')
    m66 = (d.str.len() == 11) & d.str.startswith('66'); d = d.where(~m66, '0' + d.str[2:])
    m0 = (d.str.len() == 9) & d.str[:1].isin(list('689')); d = d.where(~m0, '0' + d)
    mobile = d.str.fullmatch(r'0[689]\d{8}')
    ok = mobile | d.str.fullmatch(r'0[2-7]\d{7}')
    dummy = ok & d.str.contains(PHONE_DUMMY)
    status = np.select([d == '', dummy, ~ok], ['empty', 'dummy', 'invalid'], 'ok')
    val = np.where(status == 'ok', pd.to_numeric(d.where(status == 'ok', '0'), errors='coerce'), 0).astype('i8')
    return dict(norm=d, status=pd.Series(status, index=s.index), fixed=(had_sym | m66 | m0 | multi) & (status == 'ok'),
                multi=multi & (status == 'ok'), mobile=(mobile & (status == 'ok')).to_numpy(), val=val)

def clean_email(s):
    e = s.fillna('').astype(str).str.strip().str.lower()
    dom = e.str.rsplit('@', n=1).str[-1].where(e.str.contains('@'), '')
    fix = dom.isin(DOMAIN_FIX.keys())
    e = e.where(~fix, e.str.rsplit('@', n=1).str[0] + '@' + dom.map(DOMAIN_FIX))
    ok = e.str.fullmatch(EMAIL_OK)
    dummy = ok & e.str.contains(EMAIL_DUMMY)
    status = np.select([e == '', dummy, ~ok], ['empty', 'dummy', 'invalid'], 'ok')
    good = status == 'ok'
    h = np.where(good, pd.util.hash_array(e.to_numpy(object)), 0).astype('u8')
    return dict(norm=e, status=pd.Series(status, index=s.index), fixed_domain=fix & good,
                company=good & e.str.contains(COMPANY_DOM), hash=h)

def clean_birth(s):
    t = s.astype(str).str[:10]
    y = pd.to_numeric(t.str[:4], errors='coerce'); m = pd.to_numeric(t.str[5:7], errors='coerce'); d = pd.to_numeric(t.str[8:10], errors='coerce')
    be = y > 2400; y = y.where(~be, y - 543)                           # ปี พ.ศ. → ค.ศ.
    ok = y.between(1920, 2026) & m.between(1, 12) & d.between(1, 31)
    jan1 = ok & (m == 1) & (d == 1)                                    # น่าจะเป็นค่า default
    val = np.where(ok & ~jan1, (y * 10000 + m * 100 + d).fillna(0), 0).astype('i4')
    present = s.notna() & ~t.isin(['None', 'NaT', '0000-00-00', 'nan', ''])
    return dict(val=val, be_fixed=be & ok, invalid=present & ~ok, jan1=jan1)

def thai_id(s):
    """เลข 13 หลัก + checksum → (digits, valid, kind) · kind 1 = บุคคล (ขึ้นต้น 1-8) · 2 = นิติบุคคล/ผู้เสียภาษี (ขึ้นต้น 0)"""
    d = s.fillna('').astype(str).str.translate(TH_DIGIT).str.replace(r'[^0-9]', '', regex=True)
    ok = (d.str.len() == 13).to_numpy()
    valid = np.zeros(len(d), bool)
    if ok.any():
        a = np.frombuffer(''.join(d[ok]).encode('ascii'), 'u1').reshape(-1, 13).astype('i8') - 48
        chk = (11 - (a[:, :12] * np.arange(13, 1, -1)).sum(1) % 11) % 10
        valid[ok] = (chk == a[:, 12]) & ~(a == a[:, :1]).all(1)
    first = d.str[:1].to_numpy(object)
    kind = np.where(valid, np.where(first == '0', 2, np.where(first == '9', 0, 1)), 0).astype('u1')
    return d, valid, kind

def id_hash(d, keep):
    return np.where(keep, pd.util.hash_array(d.to_numpy(object)), 0).astype('u8')

def init_class(first, last, lang):
    def th(x): return x.str.extract(TH_FIRST, expand=False).map(TH2C)
    def en(x): return x.str[:1].str.upper().map(EN2C)
    a = np.where(lang == 1, th(first), np.where(lang == 2, en(first), None))
    b = np.where(lang == 1, th(last), np.where(lang == 2, en(last), None))
    a = pd.Series(a).map(CLS).fillna(0).astype('u2').to_numpy(); b = pd.Series(b).map(CLS).fillna(0).astype('u2').to_numpy()
    return (a * 32 + b).astype('u2')

def name_hash(key, junk):
    return np.where(junk, 0, pd.util.hash_array(key.to_numpy(object))).astype('u8')


# ── Record classification: shared contacts / employee email ──────────────
def distinct_per_key(key, name, mask):
    """จำนวน name ไม่ซ้ำต่อ key (vectorized ด้วย sort) · คืนค่าต่อแถว"""
    idx = np.flatnonzero(mask & (key != 0) & (name != 0))
    out = np.zeros(len(key), 'u4')
    if len(idx) == 0: return out
    k, n = key[idx], name[idx]
    o = np.lexsort((n, k)); k, n, ii = k[o], n[o], idx[o]
    newk = np.r_[True, k[1:] != k[:-1]]; newn = newk | np.r_[True, n[1:] != n[:-1]]
    grp = np.cumsum(newk) - 1
    nd = np.bincount(grp, weights=newn).astype('u4')
    out[ii] = nd[grp]
    return out

def shared_contacts(a, c, th=5):
    """เบอร์/อีเมลที่มี ≥ th ชื่อ ไม่ใช้เป็นคีย์ · อีเมลพนักงาน 1 ชื่อ = พนักงาน · ≥ 2 ชื่อ = ลบอีเมล"""
    person = a['status'] == 0
    dp = distinct_per_key(a['phone'], a['name'], person)
    de = distinct_per_key(a['email'], a['name'], person)
    shp = dp >= th; she = de >= th
    c['shared_phone_rows'] = int(shp.sum()); c['shared_phone_keys'] = int(len(np.unique(a['phone'][shp])))
    c['shared_email_rows'] = int(she.sum()); c['shared_email_keys'] = int(len(np.unique(a['email'][she])))
    comp = a['company'] & person
    c['company_rows'] = int(comp.sum())
    c['company_1name'] = int((comp & (de == 1)).sum()); c['company_multi'] = int((comp & (de >= 2)).sum())
    a['employee'] = comp & (de == 1) | (a.get('staff', np.zeros(len(person), 'u1')) > 0)
    a['phone_m'] = np.where(shp, 0, a['phone']); a['email_m'] = np.where(she | (comp & (de >= 2)), 0, a['email'])
    c['company_dist'] = {int(k): int(v) for k, v in sorted(collections.Counter(np.minimum(de[comp], 5)).items())}


# ── Duplicate matching (union-find) ───────────────────────────────────────
def mix(*ks):
    h = np.zeros(len(ks[0]), 'u8')
    with np.errstate(over='ignore'):
        for k in ks: h = (h ^ k.astype('u8')) * np.uint64(0x9E3779B97F4A7C15) + np.uint64(0x632BE59BD9B4E019)
    return h

def edges_by_key(key, valid):
    sel = np.flatnonzero(valid)
    if len(sel) < 2: return np.empty((0, 2), 'i8')
    k = key[sel]; o = np.argsort(k, kind='stable'); k, s = k[o], sel[o]
    same = k[1:] == k[:-1]
    return np.c_[s[:-1][same], s[1:][same]]

def cross_lang_edges(a, contact, person):
    """แถว TH/EN ที่ contact เดียวกัน + init class เดียวกัน · กลุ่มต้องมีชื่อไทย 1 แบบ และอังกฤษ 1 แบบพอดี"""
    sel = np.flatnonzero(person & (contact != 0) & np.isin(a['lang'], [1, 2]) & (a['init'] % 32 > 0) & (a['init'] // 32 > 0))
    if len(sel) == 0: return np.empty((0, 2), 'i8')
    df = pd.DataFrame({'g': mix(contact[sel], a['init'][sel]), 'lang': a['lang'][sel], 'name': a['name'][sel], 'i': sel})
    st = df.groupby(['g', 'lang']).name.nunique().unstack(fill_value=0)
    ok = st.index[(st.get(1, 0) == 1) & (st.get(2, 0) == 1)]
    d = df[df.g.isin(ok)].sort_values('g')
    first = d.groupby('g').i.transform('first')
    m = d.i != first
    return np.c_[first[m].to_numpy(), d.i[m].to_numpy()]

R6 = 'R6 ข้ามภาษา TH↔EN'

def dedup(a, r0_label='R0 ชี้ record เดียวกัน'):
    """คืน (steps, n_person, unique, edges_r6) · เขียน a['cluster']"""
    n = len(a['status']); person = a['status'] == 0
    P, E, B, N, L = a['phone_m'], a['email_m'], a['birth'], a['name'], a['lang']
    th = person & (L == 1); en = person & (L == 2); anyn = person & (N != 0)
    rules = []
    if 'link' in a and (a['link'] != 0).any(): rules.append((r0_label, lambda: edges_by_key(a['link'], person & (a['link'] != 0))))
    if 'idno' in a: rules.append(('R1 เลขบัตร', lambda: edges_by_key(a['idno'], person & (a['idno'] != 0))))
    rules += [('R2 ชื่อไทย+เบอร์',    lambda: edges_by_key(mix(N, P), th & (P != 0))),
              ('R3 ชื่อไทย+อีเมล',    lambda: edges_by_key(mix(N, E), th & (E != 0))),
              ('R4 ชื่ออังกฤษ+เบอร์', lambda: edges_by_key(mix(N, P), en & (P != 0))),
              ('R5 ชื่ออังกฤษ+อีเมล', lambda: edges_by_key(mix(N, E), en & (E != 0))),
              (R6,                    lambda: np.r_[cross_lang_edges(a, P, person), cross_lang_edges(a, E, person)]),
              ('R7 ชื่อ+วันเกิด',      lambda: edges_by_key(mix(N, B), anyn & (B != 0) & (L != 3)))]
    pidx = np.flatnonzero(person); n_person = len(pidx)
    allE = [np.empty((0, 2), 'i8')]; steps = []; prev = n_person; e6 = None
    for name, fn in rules:
        e = fn(); allE.append(e)
        if name == R6: e6 = e
        EE = np.concatenate(allE)
        g = coo_matrix((np.ones(len(EE), 'i1'), (EE[:, 0], EE[:, 1])), shape=(n, n))
        _, lab = connected_components(g, directed=False)
        uniq = len(np.unique(lab[pidx]))
        steps.append(dict(rule=name, edges=int(len(e)), merged=int(prev - uniq), unique_after=int(uniq)))
        prev = uniq
        del g, EE
    a['cluster'] = lab
    return steps, n_person, prev, e6

def review_same_name(a):
    """ชื่อ-นามสกุลเดียวกัน แต่อยู่คนละกลุ่ม → ส่งตรวจ ไม่รวมอัตโนมัติ"""
    person = (a['status'] == 0) & (a['name'] != 0)
    df = pd.DataFrame({'n': a['name'][person], 'c': a['cluster'][person]})
    g = df.drop_duplicates(['n', 'c']).groupby('n').c.size()
    multi = g[g >= 2]
    return dict(name_groups=int(len(multi)), clusters=int(multi.sum()),
                groups_2_3=int(((multi >= 2) & (multi <= 3)).sum()), groups_4plus=int((multi >= 4).sum()),
                extra_if_merged=int((multi - 1).sum()))

def dedup_keys(n, person, rules):
    """dedup แบบทั่วไป — สำหรับระบบที่ 1 แถวมีหลายชื่อ (TH + EN) หรือหลายเบอร์
    rules = [(label, [(key_u8, valid_bool), ...]), ...] · คีย์หลายชุดในกฎเดียวใช้ร่วมกัน (เช่น ชื่อ+เบอร์1 กับ ชื่อ+เบอร์2)
    คืน (steps, n_person, unique, labels)"""
    pidx = np.flatnonzero(person); n_person = len(pidx)
    allE = [np.empty((0, 2), 'i8')]; steps = []; prev = n_person
    lab = np.arange(n)
    for name, keys in rules:
        ks = [(k, v & person) for k, v in keys]
        key = np.concatenate([k for k, _ in ks]); valid = np.concatenate([v for _, v in ks])
        row = np.concatenate([np.arange(n)] * len(ks))
        e = edges_by_key(key, valid)
        e = np.c_[row[e[:, 0]], row[e[:, 1]]] if len(e) else e
        e = e[e[:, 0] != e[:, 1]] if len(e) else e
        allE.append(e)
        EE = np.concatenate(allE)
        g = coo_matrix((np.ones(len(EE), 'i1'), (EE[:, 0], EE[:, 1])), shape=(n, n))
        _, lab = connected_components(g, directed=False)
        uniq = len(np.unique(lab[pidx]))
        steps.append(dict(rule=name, edges=int(len(e)), merged=int(prev - uniq), unique_after=int(uniq)))
        prev = uniq
    return steps, n_person, prev, lab


# ── นิติบุคคล: ทำชื่อบริษัทให้เป็นรูปเดียวกัน ─────────────────────────────
COMPANY_STRIP = re.compile(
    r'บริษัท|บจก\.?|บมจ\.?|ห้างหุ้นส่วนจำกัด|ห้างหุ้นส่วนสามัญ|ห้างหุ้นส่วน|หจก\.?|หสน\.?|จำกัด|\(?มหาชน\)?|'
    r'\(?สำนักงานใหญ่\)?|\(?สาขา(?:ที่)?\s*[\w\-]*\)?|head\s*office|\bbranch\b\s*\w*|'
    r'co\.?\s*,?\s*ltd\.?|company\s+limited|\blimited\b|\bltd\.?\b|public\s+company|\bpcl\b|\bcorp(?:oration)?\.?\b|\binc\.?\b|\(thailand\)|\bthailand\b',
    re.I)
def company_key(s):
    """ชื่อบริษัท → คีย์เทียบ: ตัดคำประเภทนิติ / สาขา / วรรคตอน · lower"""
    s = s.fillna('').astype(str).str.lower().str.replace(COMPANY_STRIP, ' ', regex=True)
    return s.str.replace(r'[\s\.\,\-\(\)\'\"&/]+', '', regex=True)


def cluster_any(a, flag):
    """ต่อกลุ่มลูกค้า (person) → มี flag อย่างน้อย 1 แถวไหม · คืนจำนวนกลุ่มที่มี"""
    person = a['status'] == 0
    lab = a['cluster'][person]
    hit = np.zeros(lab.max() + 1, bool)
    hit[lab[flag[person]]] = True
    return int(hit[np.unique(lab)].sum())
