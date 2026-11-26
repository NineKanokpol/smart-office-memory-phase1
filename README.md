# Smart Office Memory · Phase 1

โครงงานจบ ปวส. สำหรับจัดการโครงการ งาน และเอกสารสำนักงาน ใช้ Python 3.12, Streamlit และ Supabase สำหรับบัญชี ฐานข้อมูล และไฟล์ต้นฉบับ

- **ภาพรวม** แสดงยอดโครงการ เอกสาร งาน งานที่ยังไม่เสร็จ กำหนดส่ง และกิจกรรมล่าสุด
- **โครงการและงาน** เพิ่ม แก้ไข ลบ และกำหนดผู้รับผิดชอบได้ งานเชื่อมกับโครงการ
- **เอกสาร** ค้นตามชื่อ อัปโหลด PDF, DOCX หรือ UTF-8 TXT ไม่เกิน 3 MB เชื่อมโครงการและดาวน์โหลดผ่านลิงก์อายุ 60 วินาที
- **บัญชี** Supabase Auth ตรวจรหัสผ่านและอีเมล เว็บอ่านข้อมูลตามเจ้าของด้วย Row Level Security (RLS)

ใช้บัญชีและข้อมูลสมมติระหว่างสาธิต ตัวอย่างไฟล์อยู่ใน `samples/` ผลทดสอบจริงและสถานะเผยแพร่อยู่ใน [TEST_REPORT.md](TEST_REPORT.md) และ [PROJECT_STATUS.md](PROJECT_STATUS.md)

ซอร์สโค้ดอยู่บน branch `main` ของ [GitHub repository สาธารณะ](https://github.com/NineKanokpol/smart-office-memory-phase1) เปิด [เว็บ Smart Office Memory](https://smart-office-memory.streamlit.app/) ได้โดยตรง เว็บขอให้เข้าสู่ระบบก่อนแสดงข้อมูลสำนักงาน

## Burgundy Liquid Glass

แดชบอร์ดแสดงยอดจริง สถานะโครงการ ความคืบหน้าจากงาน และกำหนดส่ง เลือก Light, Dark หรือ System จากเมนู Settings ของ Streamlit หรือใช้พื้นผิวทึบจากเมนูธีมและบัญชี ดู [คู่มือหน้าจอ](UI_UX_GUIDE.md)

## เริ่มต้น

1. ทำตาม [คู่มือติดตั้ง](SETUP_GUIDE.md) เพื่อเตรียม Python 3.12, Supabase และตั้งค่าแอป
2. เปิดแอปด้วย `python -m streamlit run app.py`
3. ทำตาม [คู่มือผู้ใช้](USER_MANUAL.md) เพื่อทดลองด้วยบัญชีสมมติ
4. ใช้ [คู่มือเผยแพร่](DEPLOYMENT_GUIDE.md) สำหรับ GitHub และ Streamlit Community Cloud

## ไฟล์สำคัญ

| ไฟล์ | หน้าที่ |
| --- | --- |
| `app.py` | หน้าจอ ฟอร์ม การยืนยันตัวตน และการอ่าน/เขียนข้อมูล |
| `file_utils.py` | ตรวจไฟล์และอ่านข้อความที่อ่านได้ |
| `schema.sql` | สร้างตาราง ข้อบังคับ RLS ประวัติ และ private bucket |
| `.streamlit/config.toml` | สี Light/Dark การแสดงข้อผิดพลาด และขนาดอัปโหลด |
| `tests/` | Unit tests และ Playwright E2E บน Supabase local |

## เอกสารส่งมอบ

[ตรวจความปลอดภัย](SECURITY_CHECKLIST.md) · [รายการเปลี่ยนแปลง](CHANGELOG.md) · [แนวทางนำเสนอ](PRESENTATION_GUIDE.md) · [แผน Phase 2](PHASE2_AI_ROADMAP.md)
