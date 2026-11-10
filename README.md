# เว็บคำนวณราคาประกาศรับซื้อข้าวโพด + ดึงราคาดีเซลและราคา CPF รายวัน

ไฟล์ในชุดนี้
- `index.html`  หน้าเว็บคำนวณ
- `prices.json`  ราคาดีเซลล่าสุด (ถูกอัปเดตอัตโนมัติ)
- `scripts/update_prices.py`  สคริปต์ดึงราคา
- `.github/workflows/update-prices.yml`  ตั้งเวลาให้รันทุกวัน 07:30 และ 15:00

## ขั้นตอน (ครั้งเดียว)
1. สมัคร github.com แล้วสร้าง Repository ใหม่ ตั้งชื่อเช่น `corn-price` (เลือก Public)
2. อัปโหลดไฟล์ทั้งหมดในโฟลเดอร์นี้ (รวมโฟลเดอร์ `.github` และ `scripts`) ด้วยการลากวางที่ "Add file > Upload files"
3. Settings > Actions > General > Workflow permissions เลือก "Read and write permissions" แล้ว Save
4. Settings > Pages > Source เลือก "Deploy from a branch" > Branch `main` โฟลเดอร์ `/ (root)` > Save
5. แท็บ Actions > "Update diesel price" > Run workflow เพื่อทดสอบ ถ้าขึ้นเครื่องหมายถูกสีเขียว แสดงว่าดึงราคาได้
6. เว็บจะอยู่ที่ `https://ชื่อผู้ใช้.github.io/corn-price/`

## ใช้ Netlify แทน GitHub Pages
เชื่อม Repository นี้กับ Netlify (Add new site > Import from Git) เมื่อสคริปต์อัปเดต prices.json เว็บจะ deploy ใหม่เอง

## ถ้าราคาไม่ขึ้น
- แท็บ Actions ขึ้นสีแดง: เปิดดู log ถ้าเขียนว่า "ไม่พบราคาดีเซล" แปลว่าเว็บต้นทางเปลี่ยนโครงหน้า หรือบล็อกการดึงข้อมูล แจ้งชั้นพร้อม log เพื่อแก้สคริปต์
- ราคายังเป็นค่าเก่า: ดูวันที่ใน prices.json และรันใหม่ด้วย Run workflow

## ราคา CPF จาก Google Sheet
สคริปต์อ่านชีตที่เผยแพร่เป็น CSV (ลิงก์อยู่ในตัวแปร SHEET_URL ใน `scripts/update_prices.py`) แล้วเก็บราคาล่าสุดของแต่ละโรงงานไว้ใน `prices.json`
- เมื่อเลือกโรงงานปลายทาง ช่องราคา FG จะมีเลขจางเป็นราคาล่าสุดของโรงงานนั้น พร้อมวันที่และลิงก์ "ใช้ราคานี้"
- ถ้าชีตเปลี่ยนชื่อหัวคอลัมน์ ให้แก้รายชื่อในตัวแปร CPF ให้ตรงกัน
- ถ้าเลิกเผยแพร่ชีตหรือเปลี่ยนลิงก์ แท็บ Actions จะขึ้นสีแดง ให้เปลี่ยน SHEET_URL
- โรงงานที่ไม่มีในชีต (เช่น CPF สระบุรี, BKP) จะไม่มีเลขจาง
