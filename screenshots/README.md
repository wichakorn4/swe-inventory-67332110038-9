# บันทึกภาพหน้าจอการทดสอบ CI Pipeline (CI/CD Screenshots Log) - Lab 05

โฟลเดอร์นี้ใช้จัดเก็บภาพหน้าจอผลการทำงานของ GitHub Actions CI บน Pull Request ตามข้อกำหนดในขั้นที่ 11:

---

## ไฟล์ที่ต้องจัดเก็บในโฟลเดอร์นี้
1. **`ci-green.png`**: ภาพหน้าจอตอน GitHub Actions รันผ่านทั้งหมด (เครื่องหมายถูกสีเขียว `All checks have passed`) แสดงรายการตรวจสอบ:
   - `ruff check .` ผ่านสมบูรณ์
   - `pytest` ผ่านครบทุกข้อ และ Code Coverage ถึงเกณฑ์ 85% (ระบบทำได้ 100%)
2. **`ci-red.png`**: ภาพหน้าจอตอน GitHub Actions ทำงานล้มเหลว (เครื่องหมายกากบาทสีแดง `Some checks were not successful`) จากการจงใจแก้ไขค่าคงที่หรือ Test Case ให้พัง พร้อมแสดง Log บรรทัดที่เกิดข้อผิดพลาด

---

## ขั้นตอนการสร้างภาพและบันทึกผล
1. Push branch `main` ขึ้นสู่ GitHub:
   ```bash
   git push origin main
   ```
2. สร้างและสลับไปยัง branch ฟีเจอร์:
   ```bash
   git switch -c feat/low-stock-alert
   git push -u origin feat/low-stock-alert
   ```
3. เปิด Pull Request บน GitHub จาก `feat/low-stock-alert` เข้าสู่ `main`
4. รอให้ GitHub Actions รันเสร็จ แล้วจับภาพหน้าจอเก็บเป็น `screenshots/ci-green.png`
5. แก้ไขโค้ดใน branch ให้พังชั่วคราว (เช่น แก้ assert ใน `tests/test_inventory.py` บรรทัดที่ 14 จาก `[]` เป็น `["Ghost"]`)
6. Commit และ Push ขึ้น branch เดิม:
   ```bash
   git add tests/test_inventory.py
   git commit -m "test: simulate CI failure on purpose"
   git push
   ```
7. เมื่อ CI ใน PR ขึ้นสีแดง ให้เปิดดู Log และจับภาพหน้าจอเก็บเป็น `screenshots/ci-red.png`
8. แก้โค้ดกลับให้ถูกต้อง (หรือ `git revert HEAD`), นำภาพ `ci-green.png` และ `ci-red.png` มาวางในโฟลเดอร์ `screenshots/` นี้ แล้ว Commit:
   ```bash
   git add screenshots/
   git commit -m "docs: add green and red CI run screenshots"
   git push
   ```
9. เมื่อ CI กลับมาเขียว ให้กด Merge Pull Request เข้าสู่ `main`
