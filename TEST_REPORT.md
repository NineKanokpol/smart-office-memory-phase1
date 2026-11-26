# รายงานทดสอบ Phase 1

วันที่ 26 พฤศจิกายน 2569 · CPython 3.12.16 · Streamlit 1.67.0 · Supabase CLI 3.4.0 พร้อม PostgreSQL, Auth, Storage และ Mailpit ใน Docker · Chromium ผ่าน Playwright

ชุดทดสอบ Liquid Glass บน localhost ผ่าน 24 กรณี รวม 23 unit/configuration และ 1 เส้นทาง Browser E2E พร้อมการตรวจ API ของสองบัญชี เส้นทางเอกสารตรวจการอัปโหลดผ่าน dialog และยืนยันลบหลังเตรียมดาวน์โหลด

ตรวจแดชบอร์ดที่ 375, 390, 768, 1366 และ 1920 พิกเซลใน Chromium ด้วยข้อมูลสมมติจาก Supabase local ตรวจฟอนต์ไทยและการล้นแนวนอนทุกขนาด ตรวจการเปิดหน้าตั้งค่าด้วยแป้นพิมพ์และสวิตช์พื้นผิวทึบที่ 1366 พิกเซล

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
| ตรวจไฟล์ก่อน push | PASS | ตรวจชื่อไฟล์และรูปแบบ credential ที่พบบ่อยตลอด Git history ไม่พบไฟล์ secrets จริง พบเฉพาะอีเมลทดสอบบน `example.com` และไฟล์ตัวอย่างที่ระบุว่าเป็นข้อมูลสมมติ |
| GitHub | PASS | ตรวจยืนยัน repository เป็น Public และ `main` เป็น branch หลักหลัง push |
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

เว็บอยู่ที่ [smart-office-memory.streamlit.app](https://smart-office-memory.streamlit.app/) บน deployment เดิมของ Streamlit Community Cloud

| รายการ | ผล |
| --- | --- |
| ก่อนปรับ Liquid Glass | ผ่าน login/logout, CRUD โครงการ งาน เอกสาร และค้นเอกสารบน Cloud ไฟล์ TXT ดาวน์โหลดแล้วตรงกับต้นฉบับทุกไบต์ |
| หลังปรับ Liquid Glass | ผ่าน login A/B เพิ่มโครงการและงานผ่าน UI, KPI งานเสร็จและกราฟแสดง 100% ตามข้อมูลจริง อัปโหลด TXT ผ่าน dialog สร้างลิงก์ดาวน์โหลด และลบข้อมูลทดสอบบน Cloud |
| Public URL และธีม | ผ่าน HTTP 200 จาก Chromium ที่ไม่มีคุกกี้ที่ 375, 390, 768, 1366 และ 1920 พิกเซล หน้าเข้าสู่ระบบโหลด Noto Sans Thai และไม่ล้นแนวนอน ทดสอบสลับ Dark, Light แล้วกลับ System ผ่านเมนู Streamlit |
| ไฟล์ดาวน์โหลดบน Liquid Glass | ผ่านเทียบไบต์ใน Browser E2E บน local การทดสอบกดดาวน์โหลดบน Cloud รอบใหม่หมดอายุระหว่างที่เครื่องมือรอ ส่วนรอบ Cloud ก่อนปรับ UI ดาวน์โหลดและเทียบไบต์ผ่านแล้ว |
| การแยกบัญชีบน Cloud | ผ่าน A เห็นข้อมูลของตัวเอง B เห็นยอดว่าง ตรวจ SQL ด้วยตัวตน A/B และ anonymous รวม Storage RLS และ URL ที่ไม่มีลายเซ็นซึ่งถูกปฏิเสธ |
| หลัง Cloud reboot | ผ่าน ยอดข้อมูลและประวัติยังอยู่หลังขั้นตอนเปิดแอปใหม่และเข้าสู่ระบบ |
| สมัครบน Cloud | ส่งฟอร์มจริงและตรวจว่ามีแถวผู้สมัครที่ยังไม่ยืนยัน ผู้สมัครเข้าใช้ Dashboard ไม่ได้จนกว่าจะยืนยัน |
| รับอีเมลยืนยันจากกล่องทดสอบภายนอก | **รอทดสอบ** โปรเจกต์ใช้ SMTP เริ่มต้นของ Supabase ซึ่งจำกัดการส่งอีเมลไว้ที่สมาชิกทีม การส่งไปยังกล่องภายนอกต้องตั้ง custom SMTP ก่อน รันทดสอบคลิกลิงก์ยืนยันผ่าน Mailpit บน localhost สำเร็จแล้ว |

บัญชีทดสอบ Cloud สองบัญชีสร้างด้วย Dashboard เพื่อทดสอบเส้นทางหลังยืนยันอีเมล ใช้ข้อมูลสมมติและลบแถวโครงการ งาน และเอกสารที่ใช้ทดสอบผ่าน UI แล้ว
