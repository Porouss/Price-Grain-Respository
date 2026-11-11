#!/usr/bin/env python3
"""อัปเดต prices.json ทุกวัน
  1) ราคาดีเซล (B7) จากเว็บราคาน้ำมันวันนี้
  2) ราคารับซื้อล่าสุดของ CPF แต่ละโรงงาน จาก Google Sheet ที่เผยแพร่เป็น CSV
ใช้เฉพาะไลบรารีมาตรฐานของ Python ถ้าส่วนไหนอ่านไม่ได้ จะคงค่าเดิมของส่วนนั้นไว้
แล้วจบด้วย error เพื่อให้แท็บ Actions ขึ้นสีแดง"""
import csv, datetime, html, io, json, os, re, sys, urllib.request

OIL_URL = ("https://xn--42cah7d0cxcvbbb9x.com/"
           "%E0%B8%A3%E0%B8%B2%E0%B8%84%E0%B8%B2%E0%B8%99%E0%B9%89%E0%B8%B3"
           "%E0%B8%A1%E0%B8%B1%E0%B8%99%E0%B8%A7%E0%B8%B1%E0%B8%99%E0%B8%99"
           "%E0%B8%B5%E0%B9%89/")
BCP_URL = "https://oil-price.bangchak.co.th/ApiOilPrice2/th"   # ราคาน้ำมันบางจาก (สำรอง)
SHEET_URL = ("https://docs.google.com/spreadsheets/d/e/"
             "2PACX-1vQOdbeAEEqDkKBN-B9fKAMv98py1CZKmNPvOv3gy8ho44EPJY8mSYim4MpCWmphzOTffdX6-551WKYk"
             "/pub?gid=1956129598&single=true&output=csv")
OUT = "prices.json"
MONTHS = ("มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|"
          "กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม")
DAYS = "จันทร์|อังคาร|พุธ|พฤหัสบดี|ศุกร์|เสาร์|อาทิตย์"
# ชื่อคอลัมน์ในชีต (ต้องตรงกับหัวตาราง)
CPF = ["CPF บางนา", "CPF ศรีราชา", "CPF กบินทร์บุรี", "CPF ราชบุรี", "CPF หนองแค",
       "CPF ท่าเรือ", "CPF โคกตูม", "CPF โคกกรวด", "CPF ปักธงชัย", "CPF ขอนแก่น",
       "CPF ศรีสะเกษ", "CPF พิษณุโลก", "CPF ลำพูน", "CPF สมุทปราการ"]
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json,text/csv;q=0.9,*/*;q=0.8",
        "Accept-Language": "th,en;q=0.8",
        "Referer": "https://www.google.com/",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8-sig", "replace")


# ---------- ดีเซล ----------
def to_text(raw):
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw))


def parse_diesel(text):
    m = re.search(r"ดีเซล (\d{2}\.\d{2})(?!\d)", text)  # ไม่รวม B20 / พรีเมี่ยม / Shell
    if not m:
        raise ValueError("ไม่พบราคาดีเซลในหน้าเว็บ (โครงหน้าอาจเปลี่ยน)")
    price = float(m.group(1))
    if not 15 <= price <= 100:
        raise ValueError(f"ราคาดีเซลผิดปกติ: {price}")
    d = re.search(rf"(?:{DAYS})ที่ (\d{{1,2}}) ({MONTHS}) (\d{{4}})", text)
    return price, (f"{d.group(1)} {d.group(2)} {d.group(3)}" if d else None)


def _walk(o):
    if isinstance(o, str):
        t = o.strip()
        if t[:1] in "[{":
            try:
                yield from _walk(json.loads(t))
            except ValueError:
                pass
    elif isinstance(o, list):
        for x in o:
            yield from _walk(x)
    elif isinstance(o, dict):
        yield o
        for x in o.values():
            yield from _walk(x)


def parse_bangchak(text):
    """ราคาดีเซลธรรมดา (ไฮดีเซล S) จาก API ของบางจาก ไม่เอา พรีเมียม / B20 / B10"""
    for d in _walk(json.loads(text)):
        name = str(d.get("OilName") or d.get("oilName") or "")
        price = d.get("PriceToday", d.get("priceToday"))
        if not name or price in (None, ""):
            continue
        if "ดีเซล" not in name and "diesel" not in name.lower():
            continue
        if re.search(r"พรีเมี|premium|B20|B10", name, re.I):
            continue
        try:
            v = float(price)
        except (TypeError, ValueError):
            continue
        if 15 <= v <= 100:
            return v
    raise ValueError("ไม่พบราคาดีเซลใน API บางจาก")


# ---------- ราคา CPF จากชีต ----------
def parse_date(s):
    """รับ m/d/yyyy, d/m/yyyy, yyyy-mm-dd และปี พ.ศ."""
    s = s.strip()
    m = re.fullmatch(r"(\d{1,4})[/-](\d{1,2})[/-](\d{1,4})", s)
    if not m:
        return None
    a, b, c = (int(x) for x in m.groups())
    if a > 31:
        y, mo, d = a, b, c            # yyyy-mm-dd
    else:
        y = c + 2000 if c < 100 else c
        mo, d = (a, b) if a <= 12 else (b, a)   # ปกติ m/d ถ้าเดือนเกิน 12 ให้สลับ
    if y > 2400:
        y -= 543
    try:
        return datetime.date(y, mo, d)
    except ValueError:
        return None


def parse_cpf(text, today=None):
    rows = list(csv.reader(io.StringIO(text)))
    hi = next((i for i, r in enumerate(rows[:10]) if any("CPF บางนา" in c for c in r)), None)
    if hi is None:
        raise ValueError("ไม่พบแถวหัวตาราง (CPF บางนา) ในชีต")
    head = [re.sub(r"\s+", " ", c).strip() for c in rows[hi]]
    idx = {n: head.index(n) for n in CPF if n in head}
    missing = [n for n in CPF if n not in idx]
    last = {}
    dated = 0
    newest = None
    for r in rows[hi + 1:]:                 # หลังหัวตาราง: รหัสย่อ แล้วต่อด้วยแถวรายวัน
        if not r:
            continue
        d = parse_date(r[0])
        if d is None:
            continue
        dated += 1
        newest = d if newest is None or d > newest else newest
        if today and d > today:             # ชีตมีวันที่ล่วงหน้าไว้ถึงปีหน้า ข้ามแถวอนาคต
            continue
        for n, i in idx.items():
            if i >= len(r):
                continue
            try:
                v = float(r[i].strip())
            except ValueError:              # ช่องว่าง, #REF!, #VALUE!
                continue
            if not 5 <= v <= 40:            # กันค่าหลุด เช่น 0.24 หรือ 1.23
                continue
            prev = last.get(n)
            if prev is None or d >= prev[1]:
                last[n] = (v, d)
    print(f"sheet: {len(rows)} rows, {dated} dated rows, newest date {newest}")
    if not dated:
        raise ValueError("ไม่พบแถวที่มีวันที่ในคอลัมน์แรก (รูปแบบวันที่อาจเปลี่ยน)")
    if not last:
        raise ValueError("ไม่พบราคา CPF ในชีต")
    return {n: {"price": v, "date": d.isoformat()} for n, (v, d) in last.items()}, missing


def main():
    data = {}
    if os.path.exists(OUT):
        try:
            data = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            data = {}
    bkk = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=7)
    errors = []

    sources = [
        ("เว็บราคาน้ำมันวันนี้", lambda: parse_diesel(to_text(fetch(OIL_URL))), "ทองคําราคา.com/ราคาน้ำมันวันนี้"),
        ("บางจาก", lambda: (parse_bangchak(fetch(BCP_URL)), None), "oil-price.bangchak.co.th (ไฮดีเซล S)"),
    ]
    fails = []
    for name, fn, src in sources:
        try:
            price, date_th = fn()
            if not date_th:
                date_th = f"{bkk.day} {MONTHS.split('|')[bkk.month - 1]} {bkk.year + 543}"
            data.update({"diesel": price, "date_th": date_th, "source": src})
            print("diesel OK via", name, price, date_th)
            fails = []
            break
        except Exception as e:
            fails.append(f"{name}: {e}")
            print("diesel source failed -", name, e, file=sys.stderr)
    if fails:
        errors.append("ดีเซล: " + " | ".join(fails))

    try:
        cpf, missing = parse_cpf(fetch(SHEET_URL), bkk.date())
        data["cpf"] = cpf
        print("cpf OK", len(cpf), "factories")
        if missing:
            print("WARN ไม่พบคอลัมน์:", ", ".join(missing), file=sys.stderr)
    except Exception as e:
        errors.append(f"ราคา CPF: {e}")

    if len(errors) < 2:
        data["updated_at"] = bkk.strftime("%Y-%m-%d")
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    for e in errors:
        print("ERROR:", e, file=sys.stderr)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
