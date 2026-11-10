#!/usr/bin/env python3
"""ดึงราคาดีเซล (B7) วันนี้ แล้วเขียนลง prices.json
ใช้เฉพาะไลบรารีมาตรฐานของ Python ไม่ต้องติดตั้งอะไรเพิ่ม
ถ้าอ่านราคาไม่ได้ สคริปต์จะจบด้วย error และไม่แตะไฟล์เดิม"""
import datetime, html, json, re, sys, urllib.request

URL = ("https://xn--42cah7d0cxcvbbb9x.com/"
       "%E0%B8%A3%E0%B8%B2%E0%B8%84%E0%B8%B2%E0%B8%99%E0%B9%89%E0%B8%B3"
       "%E0%B8%A1%E0%B8%B1%E0%B8%99%E0%B8%A7%E0%B8%B1%E0%B8%99%E0%B8%99"
       "%E0%B8%B5%E0%B9%89/")
OUT = "prices.json"
MONTHS = ("มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|"
          "กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม")
DAYS = "จันทร์|อังคาร|พุธ|พฤหัสบดี|ศุกร์|เสาร์|อาทิตย์"


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "th,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def to_text(raw):
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw))


def parse(text):
    # "ดีเซล 41.79" (ไม่รวม ดีเซล B20 / ดีเซลพรีเมี่ยม / ฟิวเซฟ ดีเซล Shell)
    m = re.search(r"ดีเซล (\d{2}\.\d{2})(?!\d)", text)
    if not m:
        raise ValueError("ไม่พบราคาดีเซลในหน้าเว็บ (โครงหน้าอาจเปลี่ยน)")
    price = float(m.group(1))
    if not 15 <= price <= 100:
        raise ValueError(f"ราคาผิดปกติ: {price}")
    d = re.search(rf"(?:{DAYS})ที่ (\d{{1,2}}) ({MONTHS}) (\d{{4}})", text)
    return price, (f"{d.group(1)} {d.group(2)} {d.group(3)}" if d else None)


def main():
    price, date_th = parse(to_text(fetch(URL)))
    bkk = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    if not date_th:  # ไม่เจอวันที่ในหน้า ใช้วันที่วันนี้ (พ.ศ.)
        date_th = f"{bkk.day} {MONTHS.split('|')[bkk.month - 1]} {bkk.year + 543}"
    data = {"diesel": price, "date_th": date_th,
            "updated_at": bkk.strftime("%Y-%m-%d"),
            "source": "ทองคําราคา.com/ราคาน้ำมันวันนี้"}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("OK", data)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)
