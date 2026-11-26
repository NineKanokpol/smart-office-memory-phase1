# รายงานทดสอบ Phase 1

วันที่ 26 พฤศจิกายน 2569 · CPython 3.12.16 · Streamlit 1.67.0 · Supabase CLI 3.4.0 พร้อม PostgreSQL, Auth, Storage และ Mailpit ใน Docker · Chromium ผ่าน Playwright

## ผลบนเครื่อง

| กลุ่ม | ผล | สิ่งที่ทดสอบ |
| --- | --- | --- |
| Syntax และ dependencies | PASS | `compileall` และ `uv pip check` |
| Unit / configuration | PASS · 23 กรณี | PDF, DOCX, UTF-8 TXT, ขนาดและประเภทไฟล์, ขอบเขตวันกำหนดส่ง, การแบ่งหน้า, ยืนยันอีเมล, ประเภท key และคอนทราสต์สี |
| Schema | PASS | รัน `schema.sql` สองรอบใน Supabase local แล้วเริ่มระบบจากฐานข้อมูลเดิม |
| Auth | PASS | บัญชีสมมติ A/B สมัครผ่านหน้าเว็บ รับลิงก์ที่ Mailpit เข้าระบบไม่ได้ก่อนยืนยัน เข้าระบบได้หลังยืนยัน และออกจากระบบได้ |
| โครงการ งาน และเอกสาร | PASS | เพิ่ม แก้ไข ลบยืนยัน และบันทึกทุกโมดูลผ่านเบราว์เซอร์ ค้นชื่อ อัปโหลดและดาวน์โหลด TXT พร้อมตรวจไบต์และ response attachment |
| Dashboard และประวัติ | PASS | A เห็นยอดของตัวเอง, B เห็นศูนย์, ประวัติสะท้อนการเพิ่มกับการแก้ไข และข้อมูลอยู่หลังออกเข้าใหม่ |
| การแยกบัญชี | PASS | B อ่าน แก้ไข ลบรายการของ A ผ่าน PostgREST ไม่ได้ ผู้ใช้ไม่มี session อ่านตารางไม่ได้ ตรวจ FK ข้ามบัญชี และป้องกันลบโครงการที่มีเอกสาร |
| Storage | PASS | Bucket ปฏิเสธ public URL และปฏิเสธดาวน์โหลดหรือสร้าง signed URL ข้ามบัญชี A ดาวน์โหลดต้นฉบับได้ |
| ธีมและจอ | PASS | System ตามค่าที่ Chromium จำลองเป็น Light บน 1440×900 และ Dark บน 390×844 รวมค่าสีพื้นหลังและความกว้าง mobile |
| Dependency advisories | PASS | `pip-audit -r requirements.txt` รายงานว่าไม่พบช่องโหว่ที่รู้จักในขณะตรวจ |
| ตรวจไฟล์ก่อน commit | PASS | `.env`, `.env.local` และ `.streamlit/secrets.toml` ตรงกับกฎ ignore ตรวจชื่อไฟล์ที่ stage และรูปแบบ credential ที่พบบ่อย โดยไม่มีไฟล์ที่ตรงรูปแบบ |
| รีสตาร์ต Streamlit | PASS | หยุดและเริ่มกระบวนการ Streamlit ใหม่บนพอร์ต 8502 จากนั้นเข้าสู่ระบบ เห็นเอกสาร 2 รายการ และอ่านต้นฉบับจาก Storage ได้ตรงไบต์ |
| อัปโหลด PDF/DOCX ผ่าน UI | PASS | อัปโหลด DOCX ที่มีข้อความและ PDF ตัวอย่างที่ไม่มีชั้นข้อความ ตรวจไฟล์ใน Storage |
| อุปกรณ์มือถือจริงและ WCAG ทั้งระบบ | NOT TESTED | ตรวจ Chromium mobile emulation และทดสอบคอนทราสต์ของข้อความ ลิงก์ ขอบฟอร์ม และปุ่มหลักตามค่าธีม |

ไลบรารี Supabase ส่ง deprecation warnings เกี่ยวกับตัวเลือก timeout/verify ของ client ระหว่างทดสอบ เส้นทางที่ครอบคลุมรันสำเร็จ

## รันทดสอบซ้ำ

```bash
python -m pip install -r requirements.txt pytest playwright
python -m playwright install chromium
python -m pytest -q
```

สำหรับ Playwright ให้ใช้ Supabase local ทดสอบที่แยกจากข้อมูลอื่น เปิด Email confirmation และ Mailpit รัน `schema.sql` แล้วเปิด Streamlit ที่ `127.0.0.1:8501` ให้ `OFFICE_E2E_SECRETS` ชี้ไฟล์ TOML ของ local instance ในการเขียนค่า config ให้ตั้ง Supabase Site URL เป็น URL local เดียวกับแอปและกำหนดโควตาอีเมลทดสอบให้พอสำหรับ A และ B

```bash
OFFICE_E2E_SECRETS=/path/to/local/secrets.toml python -m pytest -s tests/test_local_e2e.py
```

ถ้าเปลี่ยนพอร์ต ให้ตั้ง `OFFICE_E2E_APP` หรือ `OFFICE_E2E_MAILPIT` ตามบริการที่จะทดสอบ

## Public E2E

**NOT TESTED** ยังไม่มี URL ของแอปที่ deploy แล้ว เมื่อมี URL ให้ตรวจ HTTP, เปิด Incognito โดยไม่ลงชื่อเข้า GitHub/Streamlit, สมัครและยืนยันอีเมล, อัปโหลด/ดาวน์โหลด, เข้าบัญชี A/B, รีสตาร์ตแอปแล้วตรวจข้อมูลเดิม และทดสอบ Light/Dark บนเดสก์ท็อปและมือถือ
