# บันทึกการ Debug โค้ดแบบมีหลักฐาน (Evidence-Based Debugging Log) - Lab 04

**ไฟล์เป้าหมาย**: `discount.py` และ `tests/test_discount.py`  
**แนวคิดหลัก**: การแก้ปัญหาอย่างมีหลักฐานทางวิทยาศาสตร์ 5 ขั้นตอน (Reproduce -> Traceback -> Hypothesis -> Verification -> Fix & Re-run) โดยไม่แก้โค้ดแบบสุ่มตามที่ AI แนะนำ

---

## 1. ขั้นที่ 1: การจำลองปัญหา (Reproduce)

รันคำสั่งทดสอบด้วย `pytest` จากโฟลเดอร์ `lab04-ai-coding-ux/`:

```bash
python -m pytest tests/test_discount.py -v
```

### ผลลัพธ์ Traceback ดั้งเดิมที่บันทึกได้ (Original Test Failure Output)
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: C:\Users\Wichakorn44\swe-inventory-67332110038-9\lab04-ai-coding-ux
collected 6 items

tests/test_discount.py::test_apply_discount_basic FAILED                 [ 16%]
tests/test_discount.py::test_apply_discount_zero PASSED                  [ 33%]
tests/test_discount.py::test_bulk_total FAILED                           [ 50%]
tests/test_discount.py::test_average_price PASSED                        [ 66%]
tests/test_discount.py::test_average_price_empty FAILED                  [ 83%]
tests/test_discount.py::test_cheapest_n FAILED                           [100%]

================================== FAILURES ===================================
__________________________ test_apply_discount_basic __________________________

    def test_apply_discount_basic():
        # ลด 10% จาก 100 บาท ควรเหลือ 90 บาท
>       assert apply_discount(100.0, 10) == 90.0
E       assert 99.9 == 90.0
E        +  where 99.9 = apply_discount(100.0, 10)

tests\test_discount.py:8: AssertionError
_______________________________ test_bulk_total _______________________________

    def test_bulk_total():
        # (100 + 100 + 100) = 300 ลด 10% ควรเหลือ 270
>       assert bulk_total([100.0, 100.0, 100.0], 10) == 270.0
E       assert 299.9 == 270.0
E        +  where 299.9 = bulk_total([100.0, 100.0, 100.0], 10)

tests\test_discount.py:18: AssertionError
__________________________ test_average_price_empty ___________________________

    def test_average_price_empty():
        # คลังว่างควรได้ 0.0 ไม่ใช่ crash
>       assert average_price([]) == 0.0
tests\test_discount.py:28: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
prices = []
    def average_price(prices: list) -> float:
>       return sum(prices) / len(prices)
E       ZeroDivisionError: division by zero

discount.py:18: ZeroDivisionError
_______________________________ test_cheapest_n _______________________________

    def test_cheapest_n():
        # ถูกสุด 2 รายการของ [50, 10, 30, 20] = [10, 20]
>       assert cheapest_n([50.0, 10.0, 30.0, 20.0], 2) == [10.0, 20.0]
E       assert [20.0] == [10.0, 20.0]
E         At index 0 diff: 20.0 != 10.0
E         Right contains one more item: 20.0
E         Full diff:
E           [
E         -     10.0,
E               20.0,
E           ]

tests\test_discount.py:33: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_discount.py::test_apply_discount_basic - assert 99.9 == 90.0
FAILED tests/test_discount.py::test_bulk_total - assert 299.9 == 270.0
FAILED tests/test_discount.py::test_average_price_empty - ZeroDivisionError: ...
FAILED tests/test_discount.py::test_cheapest_n - assert [20.0] == [10.0, 20.0]
========================= 4 failed, 2 passed in 0.14s =========================
```

---

## 2. ตารางวิเคราะห์ Root Cause และแนวทางแก้ไขทีละ Test Case

| test ที่ไม่ผ่าน | traceback หรือ assertion ที่เห็น | สมมติฐาน root cause | วิธียืนยันสมมติฐาน | แนวทางการแก้ไขที่ถูกต้อง |
| :--- | :--- | :--- | :--- | :--- |
| **`test_apply_discount_basic`** | `assert 99.9 == 90.0` (where `99.9 = apply_discount(100.0, 10)`) | สูตรคำนวณทางคณิตศาสตร์ผิดพลาด โดยเขียน `price - percent / 100` ทำให้ตัวคูณราคาหายไป กลายเป็นการนำราคาไปลบด้วยสัดส่วนทศนิยมตรง ๆ (`100.0 - 0.1 = 99.9`) แทนที่จะคิดเปอร์เซ็นต์จากฐานราคา | คำนวณด้วยมือและทดสอบใน Python REPL: `100.0 - 10/100` ได้ `99.9` ส่วนสูตรที่ถูกคือ `100.0 * (1 - 10/100)` ได้ `90.0` | แก้เป็น `return price * (1.0 - percent / 100.0)` หรือ `return price - (price * percent / 100.0)` |
| **`test_bulk_total`** | `assert 299.9 == 270.0` (where `299.9 = bulk_total([100.0, 100.0, 100.0], 10)`) | เกิดจากผลกระทบสืบเนื่อง (Cascading Failure) ของ `apply_discount()` การหาผลรวมราคาทุกรายการ `total = 300.0` ถูกต้องแล้ว แต่เมื่อส่งเข้า `apply_discount(300.0, 10)` ทำให้เกิด `300.0 - 0.1 = 299.9` | ตรวจสอบค่า `total` ก่อนส่งเข้า `apply_discount`: ผลรวมได้ `300.0` เมื่อฟังก์ชัน `apply_discount` ถูกแก้ให้ถูกต้อง ข้อนี้จะผ่านทันทีโดยไม่ต้องแก้โค้ดใน `bulk_total` | เมื่อแก้ไข `apply_discount` ให้สมบูรณ์ `bulk_total` จะคำนวณ `apply_discount(300.0, 10) == 270.0` สำเร็จ |
| **`test_average_price_empty`** | `ZeroDivisionError: division by zero` ที่บรรทัด `return sum(prices) / len(prices)` | ไม่ได้ดักกรณีขอบเขตข้อมูลว่างเปล่า (Empty List Edge Case) เมื่อ `prices == []` จะทำให้ `len(prices) == 0` ส่งผลให้เกิดการหารด้วยศูนย์ | ทดสอบเรียก `len([])` ใน Python ได้ 0 และ `sum([])` ได้ 0 เมื่อนำมาหารกันจะเกิด `ZeroDivisionError` ทันที | เพิ่ม Guard Clause ตรวจสอบกรณีลิสต์ว่าง: `if not prices: return 0.0` ก่อนทำการคำนวณค่าเฉลี่ย |
| **`test_cheapest_n`** | `assert [20.0] == [10.0, 20.0]` (ขาด `10.0` และคืนค่าเพียงตัวเดียว) | ข้อผิดพลาดจากการทำ List Slicing (`ordered[1:n]`) โดยเข้าใจผิดเรื่อง 0-based indexing ทำให้ข้ามสมาชิกตัวแรกที่ถูกที่สุด (index 0) ไป และตัดช่วงถึงแค่ index `n-1` | นำลิสต์ `[10.0, 20.0, 30.0, 50.0]` มาทดสอบ Slicing: `ordered[1:2]` จะได้ `[20.0]` ซึ่งข้าม `10.0` ไป แต่ถ้าใช้ `ordered[:2]` หรือ `ordered[0:2]` จะได้ `[10.0, 20.0]` ตรงตามที่ต้องการ | แก้ไข Slicing Index จาก `ordered[1:n]` เป็น `ordered[:n]` (หรือ `ordered[0:n]`) และจัดการกรณี `n <= 0` |

---

## 3. กับดักที่ตั้งใจวางไว้ (The Latent Trap Analysis)

ในการทดสอบรอบแรก สังเกตพบว่า **`test_apply_discount_zero` ผ่าน (PASSED)** ทั้งที่ฟังก์ชัน `apply_discount` มีบั๊กคำนวณผิดสูตร:
- โค้ดเดิม: `price - percent / 100`
- เมื่อส่ง `price = 250.0` และ `percent = 0` เข้าไป:
  `250.0 - 0 / 100 = 250.0 - 0.0 = 250.0`
- ผลลัพธ์บังเอิญเท่ากับ `250.0` พอดี ทำให้ Assertion ผ่าน

> **บทเรียนสำคัญด้านการทดสอบ (Edge Case Coverage)**: การที่ Unit Test บางข้อผ่าน ไม่ได้แปลว่าโค้ดนั้นทำงานถูกต้อง การทดสอบต้องครอบคลุมทั้งกรณีปกติ (General Case), ค่าศูนย์ (Boundary/Zero Case), และกรณีหลายค่า เพื่อป้องกันการเกิด False Positive จากการที่บั๊กซ่อนตัวอยู่หลังเงื่อนไขพิเศษ

---

## 4. ผลการ Re-run ชุดทดสอบหลังการแก้ไขทั้งหมด

หลังจากแก้ไข `discount.py` ตาม Root Cause ครบถ้วนและ commit แยกทีละจุด:

```bash
python -m pytest tests/test_discount.py -v
```

### ผลลัพธ์ล่าสุด
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: C:\Users\Wichakorn44\swe-inventory-67332110038-9\lab04-ai-coding-ux
collected 6 items

tests/test_discount.py::test_apply_discount_basic PASSED                 [ 16%]
tests/test_discount.py::test_apply_discount_zero PASSED                  [ 33%]
tests/test_discount.py::test_bulk_total PASSED                           [ 50%]
tests/test_discount.py::test_average_price PASSED                        [ 66%]
tests/test_discount.py::test_average_price_empty PASSED                  [ 83%]
tests/test_discount.py::test_cheapest_n PASSED                           [100%]

============================== 6 passed in 0.04s ===============================
```

**สรุป**: การทดสอบผ่านครบ 6/6 รายการ (100% Passed) โดยไม่มีข้อผิดพลาดหลงเหลืออยู่
