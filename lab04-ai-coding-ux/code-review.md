# รายงานผลการ Code Review และการวิเคราะห์โค้ดที่สร้างโดย AI - Lab 04

**ไฟล์เป้าหมาย**: `inventory_service.py` (Pull Request: Add batch selling, stock reservation, and reporting service)  
**ผู้ทำการ Review**: นักศึกษาวิศวกรรมซอฟต์แวร์ (ECP RMUTI)  
**สถานการณ์**: โค้ดใน PR นี้ถูกสร้างขึ้นโดย AI Coding Assistant โดยสังเคราะห์ผ่าน Syntax สมบูรณ์ รันได้ และอ้างว่าตรงตามโจทย์ทุกประการ แต่มี Bug ร้ายแรงแฝงอยู่หลายจุด ทั้งในด้านความถูกต้องเชิงตรรกะ (Correctness), ภาวะการทำงานพร้อมกัน (Concurrency / Race Conditions), การละเมิด Encapsulation, และขอบเขตเงื่อนไข (Boundary Conditions)

---

## 1. ผลการตรวจหา Bug และ Review Comments รายละเอียด 4 องค์ประกอบ

การเขียน Review Comment ในส่วนนี้ปฏิบัติตามมาตรฐานวิศวกรรมซอฟต์แวร์ระดับสากล โดยมีองค์ประกอบครบทั้ง 4 ด้าน:
1. **ตำแหน่ง**: ระบุชื่อเมธอดและหมายเลขบรรทัดที่เกิดปัญหา
2. **ปัญหาคืออะไร**: อธิบายพฤติกรรมที่ผิดพลาดและสาเหตุเชิงลึก
3. **กรณีที่ทำให้พัง**: ยกตัวอย่าง Input หรือ Scenarios ที่ส่งผลให้ระบบทำงานผิดพลาดหรือเกิด Data Corruption
4. **ข้อเสนอแนะเชิงสร้างสรรค์ (Constructive Solution)**: เสนอโค้ดและแนวทางแก้ไขที่รัดกุม

---

### เมธอดที่ 1: `sell_batch`
- **ตำแหน่ง**: เมธอด `sell_batch(orders)` บรรทัดที่ 16–22
- **ปัญหาคืออะไร**: **ขาดคุณสมบัติ Atomicity (Non-atomic Transaction)**  
  เมธอดใช้วิธีวนลูปตัดสต็อกผ่าน `self._inv.sell(name, amount)` ไปทีละรายการ หากคำสั่งซื้อมีหลายรายการและเกิดความผิดพลาดในรายการช่วงท้าย (เช่น สต็อกไม่พอ หรือระบุชื่อสินค้าผิด) รายการก่อนหน้าที่ตัดสต็อกสำเร็จไปแล้วจะไม่ถูกย้อนกลับ (No Rollback) ทำให้ระบบตกค้างอยู่ในสถานะข้อมูลไม่สอดคล้อง (Corrupted / Partial Deducted State)
- **กรณีที่ทำให้พัง**:
  สมมติมีสินค้าในคลัง: `"เมาส์"` คงเหลือ 10 ชิ้น, `"คีย์บอร์ด"` คงเหลือ 0 ชิ้น  
  ลูกค้าเรียก: `sell_batch({"เมาส์": 2, "คีย์บอร์ด": 1})`  
  *ผลลัพธ์*: เมธอดหัก `"เมาส์"` ออกไป 2 ชิ้น (เหลือ 8 ชิ้น) จากนั้นพอถึง `"คีย์บอร์ด"` จะเกิด `ValueError: สินค้าคงเหลือไม่เพียงพอ` คำสั่งซื้อล้มเหลว แต่สต็อกของ `"เมาส์"` ถูกหักหายไปฟรี ๆ แล้ว 2 ชิ้น
- **ข้อเสนอแก้**:
  ต้องแยกการทำงานออกเป็น 2 เฟส (2-Phase Validation & Execution): ตรวจสอบว่าสินค้าทุกตัวใน `orders` มีอยู่จริงและมีสต็อกเพียงพอก่อนเริ่มหัก หรือหากต้องการใช้เมธอดเดิม ต้องเก็บประวัติการหักเพื่อทำ Rollback ในบล็อก `try...except` ดังนี้:
  ```python
  def sell_batch(self, orders: dict[str, int]) -> dict[str, int]:
      """ตรวจสอบความพร้อมทั้งหมดก่อนตัดสต็อก (Atomic Execution)"""
      if not orders:
          return {}
      # Phase 1: Validate all items
      for name, amount in orders.items():
          if name not in self._inv._items:
              raise KeyError(f"ไม่พบสินค้า '{name}' ในระบบ")
          if amount <= 0:
              raise ValueError(f"จำนวนที่ขายต้องมากกว่าศูนย์สำหรับ '{name}'")
          if self._inv._items[name].quantity < amount:
              raise ValueError(f"สินค้า '{name}' คงเหลือไม่เพียงพอ")
      # Phase 2: Execute deductions
      result = {}
      for name, amount in orders.items():
          result[name] = self._inv.sell(name, amount)
      return result
  ```

---

### เมธอดที่ 2: `reserve`
- **ตำแหน่ง**: เมธอด `reserve(name, amount)` บรรทัดที่ 24–31
- **ปัญหาคืออะไร**: 
  1. **ตรรกะผลลัพธ์ผิดพลาดและกำกวม (Silent Failure)**: หากจำนวนที่ขอจองเกินกว่าสต็อกที่ว่างอยู่ (`amount > item.quantity - already`) โค้ดจะไม่เพิ่มยอดจองใน `_reserved` แต่ยังคงรันไปบรรทัด return คืนค่าตัวเลขสต็อกคงเหลือเดิม ทำให้ผู้เรียกไม่ทราบว่าการจองสำเร็จหรือไม่ และอาจเข้าใจผิดว่าระบบจองสำเร็จแล้ว
  2. **ละเมิด Encapsulation และเสี่ยงต่อ `KeyError`**: เรียก `self._inv._items[name]` ตรง ๆ หากชื่อสินค้าไม่มีในระบบจะเกิด `KeyError` ที่ไม่ได้จัดการ
  3. **ไม่มีการล็อกเพื่อความปลอดภัยในระบบมัลติเธรด (Thread-safety Issue)**: เมธอดเข้าถึงและอัปเดต `self._reserved` โดยไม่ได้ครอบด้วย `self._lock` ทำให้เสี่ยงเกิด Race Condition เมื่อมีการจองเข้ามาพร้อมกัน
- **กรณีที่ทำให้พัง**:
  สินค้า `"จอภาพ"` มีจำนวน 5 ชิ้น มีการจองอยู่แล้ว 4 ชิ้น (เหลือให้จองได้ 1 ชิ้น)  
  ผู้ใช้เรียก `reserve("จอภาพ", 3)` -> เงื่อนไข `if` เป็นเท็จ ทำให้ไม่มีการจอง แต่ฟังก์ชัน return `5 - 4 = 1` ออกไป ผู้ใช้เห็นตัวเลข 1 แล้วเข้าใจว่าตนเองได้จองสินค้าสำเร็จ 1 ชิ้น หรือจองผ่านเรียบร้อย ทั้งที่ระบบไม่ได้บันทึกอะไรเลย
- **ข้อเสนอแก้**:
  ต้องตรวจสอบการมีอยู่ของสินค้า, ตรวจสอบ `amount > 0`, ใช้ `with self._lock:` และหากจองไม่สำเร็จควร raise `ValueError` หรือคืนค่า Boolean/Status ที่ชัดเจน:
  ```python
  def reserve(self, name: str, amount: int) -> int:
      if amount <= 0:
          raise ValueError("จำนวนที่ต้องการจองต้องมากกว่าศูนย์")
      with self._lock:
          if name not in self._inv._items:
              raise KeyError(f"ไม่พบสินค้า '{name}' ในระบบ")
          item = self._inv._items[name]
          already = self._reserved.get(name, 0)
          available_to_reserve = item.quantity - already
          if amount > available_to_reserve:
              raise ValueError(f"สต็อกสินค้า '{name}' ไม่เพียงพอสำหรับการจอง {amount} ชิ้น (เหลือจองได้ {available_to_reserve} ชิ้น)")
          self._reserved[name] = already + amount
          return item.quantity - self._reserved[name]
  ```

---

### เมธอดที่ 3: `items_in_price_range`
- **ตำแหน่ง**: เมธอด `items_in_price_range(low, high)` บรรทัดที่ 33–40
- **ปัญหาคืออะไร**: **ข้อผิดพลาดขอบเขตเงื่อนไข (Off-by-boundary / Exclusive vs Inclusive)**  
  Docstring ระบุอย่างชัดเจนว่าต้องการค้นหาสินค้าที่ราคาอยู่ในช่วงปิด `[low, high]` (Closed Interval ซึ่งในทางคณิตศาสตร์หมายถึงรวมค่า low และ high) แต่โค้ดเขียนเงื่อนไขเป็น `low < item.price < high` (Strict Inequality) ทำให้สินค้าที่มีราคาเท่ากับขอบเขตล่าง (`low`) หรือขอบเขตบน (`high`) พอดี จะถูกตัดทิ้งไปอย่างเงียบ ๆ
- **กรณีที่ทำให้พัง**:
  มีสินค้า `"สายชาร์จ"` ราคา 100.0 บาท, `"หูฟัง"` ราคา 300.0 บาท, `"พาวเวอร์แบงก์"` ราคา 500.0 บาท  
  ผู้ใช้เรียก: `items_in_price_range(100.0, 500.0)`  
  *ผลลัพธ์ที่คาดหวังตาม docstring*: ต้องได้สินค้าทั้ง 3 รายการ  
  *ผลลัพธ์จริงจากโค้ด*: ได้เฉพาะ `"หูฟัง"` เพียงรายการเดียว ส่วนสินค้าขอบ 100.0 และ 500.0 หลุดหายไปทั้งหมด
- **ข้อเสนอแก้**:
  ปรับเครื่องหมายเปรียบเทียบเป็น `<=`:
  ```python
  def items_in_price_range(self, low: float, high: float) -> list:
      if low > high:
          raise ValueError("ขอบเขตราคาเริ่มต้น (low) ต้องไม่มากกว่าราคาขอบเขตบน (high)")
      names = []
      for name, item in self._inv._items.items():
          if low <= item.price <= high:
              names.append(name)
      return names
  ```

---

### เมธอดที่ 4: `low_stock_report`
- **ตำแหน่ง**: เมธอด `low_stock_report()` บรรทัดที่ 42–48
- **ปัญหาคืออะไร**: **ข้อผิดพลาดขอบเขตเงื่อนไขตกหล่น (Boundary Condition Mismatch)**  
  Docstring ระบุว่า *"คืนรายชื่อสินค้าที่ stock ต่ำกว่าหรือเท่ากับเกณฑ์"* แต่เงื่อนไขในโค้ดเขียนว่า `if item.quantity < self.LOW_STOCK_THRESHOLD:` ซึ่งขาดเครื่องหมายเท่ากับ (`=`) ส่งผลให้สินค้าที่มีสต็อกเท่ากับ 5 ชิ้นพอดี (ซึ่งเป็นค่า Threshold) ไม่ถูกรวมในรายงานเตือนภัย
- **กรณีที่ทำให้พัง**:
  คลังสินค้ามีสินค้า `"สวิตช์ไฟ"` คงเหลือ 5 ชิ้น พอดีกับ `LOW_STOCK_THRESHOLD = 5`  
  เมื่อเรียก `low_stock_report()` รายการสินค้านี้จะไม่ปรากฏในรายงาน ทำให้พนักงานคลังไม่รู้ว่าสินค้าถึงจุดสั่งซื้อแล้ว และไม่สั่งของมาเติม จนสินค้าขาดสต็อกในที่สุด
- **ข้อเสนอแก้**:
  เปลี่ยนเงื่อนไขเป็น `<=` ให้ตรงตามข้อกำหนดของ Docstring:
  ```python
  def low_stock_report(self) -> list:
      report = []
      for name, item in self._inv._items.items():
          if item.quantity <= self.LOW_STOCK_THRESHOLD:
              report.append(name)
      return report
  ```

---

### เมธอดที่ 5: `concurrent_restock`
- **ตำแหน่ง**: เมธอด `concurrent_restock(name, amount)` บรรทัดที่ 50–57
- **ปัญหาคืออะไร**: **ข้อบกพร่องร้ายแรงด้าน Concurrency: อ่านค่านอกล็อกทำให้เกิด Lost Update (Race Condition)**  
  ในบรรทัดที่ 53 โค้ดทำการอ่านค่า `current = self._inv._items[name].quantity` **ก่อนที่จะเข้าสู่บล็อก `with self._lock:`**  
  หากมี 2 เธรดทำงานพร้อมกัน ทั้งสองเธรดจะอ่านค่า `current` เดียวกันออกมาก่อนเข้าล็อก เมื่อเธรดแรกเข้าล็อกและบวกค่าเสร็จ เธรดที่สองเข้าล็อกต่อมาจะนำค่า `current` เก่าที่ตนจำไว้มาบวกและเขียนทับ ทำให้การเติมสต็อกของเธรดแรกสูญหายไปทั้งหมด (Classic Lost Update Bug) นอกจากนี้ยังข้ามการเรียกใช้ `self._inv.restock(name, amount)` ซึ่งมี Validation ตรวจสอบ `amount <= 0` และสินค้าไม่มีในคลัง
- **กรณีที่ทำให้พัง**:
  สินค้า `"สายแลน"` มีสต็อกเดิม 10 ชิ้น  
  เธรด A สั่งเติม 5 ชิ้น และ เธรด B สั่งเติม 10 ชิ้น ทำงานพร้อมกัน  
  1. เธรด A อ่าน `current = 10`  
  2. เธรด B อ่าน `current = 10`  
  3. เธรด A คว้า lock -> เขียนยอด `10 + 5 = 15` -> คืน lock  
  4. เธรด B คว้า lock -> เขียนยอด `10 + 10 = 20` (ทับค่า 15 ทิ้งไป!)  
  *ผลลัพธ์*: เติมของไป 15 ชิ้น แต่สต็อกขึ้นเพียง 20 ชิ้น (ยอดเติม 5 ชิ้นของเธรด A หายไปจากระบบทันที)
- **ข้อเสนอแก้**:
  ต้องย้ายการอ่านค่าและการคำนวณเข้าไปอยู่ภายในบล็อกล็อกทั้งหมด หรือเรียกผ่านเมธอด `restock()` ของ `Inventory` ภายใต้ Lock:
  ```python
  def concurrent_restock(self, name: str, amount: int) -> int:
      with self._lock:
          return self._inv.restock(name, amount)
  ```

---

### เมธอดที่ 6: `average_unit_value`
- **ตำแหน่ง**: เมธอด `average_unit_value()` บรรทัดที่ 59–64
- **ปัญหาคืออะไร**:
  1. **ความหมายตัวหารผิดอย่างสิ้นเชิง (Semantic Bug)**: Docstring ระบุว่าต้องการคำนวณ *"มูลค่าเฉลี่ยต่อชิ้น (unit)"* แต่โค้ดกลับใช้ `total_items = len(self._inv._items)` ซึ่งเป็นการนับจำนวน "ชนิดสินค้า (SKU / Product Variety)" ไม่ใช่ "จำนวนชิ้นทั้งหมดในคลัง (`total_quantity`)"
  2. **เกิดข้อผิดพลาดรันไทม์หารด้วยศูนย์ (Unhandled ZeroDivisionError)**: หากคลังสินค้าว่างเปล่า `_items` ไม่มีสินค้า จะเกิดข้อผิดพลาด `ZeroDivisionError: division by zero` และทำให้ระบบล่ม
- **กรณีที่ทำให้พัง**:
  - *กรณีความหมายผิด*: คลังมี `"เซิร์ฟเวอร์"` 1 เครื่อง ราคา 100,000 บาท และ `"หัวต่อ RJ45"` 1,000 ตัว ตัวละ 2 บาท  
    มูลค่ารวม = 102,000 บาท, จำนวนชิ้นทั้งหมด = 1,001 ชิ้น  
    มูลค่าเฉลี่ยต่อชิ้นที่แท้จริง = `102,000 / 1,001 = 101.89 บาท/ชิ้น`  
    แต่โค้ดคำนวณ: `102,000 / 2 (SKUs) = 51,000.00 บาท` (ค่าเพี้ยนไป 500 เท่า!)
  - *กรณีระบบล่ม*: คลังสินค้าเปิดใหม่ยังไม่มีสินค้า (`self._inv._items == {}`) เมื่อเรียกเมธอดจะ crash ทันทีด้วย `ZeroDivisionError`
- **ข้อเสนอแก้**:
  คำนวณผลรวมจำนวนชิ้นทั้งหมด (`total_units`) และดักจับกรณีที่จำนวนชิ้นรวมเป็นศูนย์:
  ```python
  def average_unit_value(self) -> float:
      total_units = sum(item.quantity for item in self._inv._items.values())
      if total_units == 0:
          return 0.0
      total_value = self._inv.get_total_value()
      return total_value / total_units
  ```

---

## 2. ตารางสรุปการจัดหมวดหมู่ข้อบกพร่อง (Defect Classification Table)

| # | เมธอดที่พบ | หมวดหมู่ (Category) | ระดับความรุนแรง (Severity) | สรุปปัญหา (Issue Summary) | กรณีที่ทำให้พัง (Failure Scenario / Reproduction) |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | `sell_batch` | Correctness | **High** | ไม่เป็น Atomic; หากรายการท้ายไม่ผ่าน รายการแรกถูกหักสต็อกไปแล้วโดยไม่ Rollback | สั่งซื้อ 2 รายการ ชิ้นแรกพอ ชิ้นสองไม่พอ -> หักชิ้นแรกไปฟรี ๆ ข้อมูลสต็อกเพี้ยน |
| **2** | `reserve` | Correctness / Concurrency | **High** | หากจองไม่สำเร็จยังคง return ตัวเลขสต็อกเสมือนสำเร็จ (Silent Failure) และไม่ได้ป้องกัน Race Condition | จองเกินสต็อกที่มี แต่ฟังก์ชัน return ตัวเลขคงเหลือเดิม ทำให้ผู้เรียกเข้าใจผิดว่าจองสำเร็จ |
| **3** | `reserve` | Style / Architecture | **Medium** | ละเมิด Encapsulation เข้าถึง `_items` ภายในโดยตรง เสี่ยงต่อ `KeyError` หากชื่อสินค้าไม่มี | ส่งชื่อสินค้าที่ไม่มีในคลังสินค้าเข้าไป ฟังก์ชัน crash ทันทีด้วย `KeyError` |
| **4** | `items_in_price_range` | Correctness | **Medium** | ข้อผิดพลาดช่วงขอบเขต (Off-by-boundary); ใช้ `<` แทนที่จะเป็น `<=` ทำให้สินค้าที่ราคาเท่ากับขอบ low หรือ high หลุดหาย | สินค้าราคา 100 บาท เมื่อค้นช่วง [100, 500] สินค้านี้จะไม่ติดในผลลัพธ์ |
| **5** | `low_stock_report` | Correctness | **Medium** | ไม่รวมค่าเท่ากับเกณฑ์; ใช้ `<` แทนที่จะเป็น `<=` ทำให้สินค้าที่สต็อกเหลือเท่ากับ 5 พอดีไม่ถูกแจ้งเตือน | สินค้าเหลือ 5 ชิ้น (เท่าเกณฑ์พอดี) ไม่ถูกเตือน จนของหมดคลังในที่สุด |
| **6** | `concurrent_restock` | Concurrency | **High** | Critical Race Condition: อ่านค่าสต็อกเก่านอกล็อก ทำให้เกิด Lost Update เมื่อมีหลายเธรดทำงานพร้อมกัน | เธรด A และ B เติมของพร้อมกัน ยอดเติมของเธรด A ถูกเธรด B เขียนทับสูญหาย |
| **7** | `concurrent_restock` | Correctness / Architecture | **Medium** | ไม่ใช้เมธอด `restock()` เดิม ละเมิด Encapsulation และไม่ตรวจสอบ `amount <= 0` | เติมจำนวนติดลบ เช่น -10 ชิ้น ระบบยอมให้บันทึกโดยไม่เกิดการแจ้งเตือน |
| **8** | `average_unit_value` | Correctness | **High** | ความหมายตัวหารผิดอย่างร้ายแรง; เอาจำนวน SKU มาหารแทนที่จะเป็นจำนวนชิ้นทั้งหมด (Total Units) | สินค้า 1,000 ชิ้น 2 SKU ตัวหารกลายเป็น 2 ทำให้มูลค่าเฉลี่ยต่อชิ้นสูงเกินจริงมหาศาล |
| **9** | `average_unit_value` | Correctness | **High** | เกิด `ZeroDivisionError` เมื่อคลังสินค้าไม่มีสินค้า | เปิดระบบตอนคลังว่างเปล่า เรียกเมธอดแล้วโปรแกรมแครชทันที |

---

## 3. การเปรียบเทียบผลการ Review ของตนเอง กับ AI Reviewer

เมื่อนำโค้ด `inventory_service.py` ส่งให้ AI Reviewer ช่วยวิเคราะห์ พบข้อสังเกตและบทเรียนสำคัญดังนี้:

### จุดที่ AI Reviewer ทำได้ดี:
1. **การตรวจสอบ Boundary Condition ทั่วไป**: AI สามารถจับจุดบกพร่องใน `items_in_price_range` (เรื่อง `<` กับ `<=`) และ `low_stock_report` ได้อย่างรวดเร็ว โดยเทียบตัวอักษรใน Docstring กับ Code
2. **การจับ Syntax และ Exception พื้นฐาน**: AI สามารถเตือนเรื่องความเสี่ยงของ `ZeroDivisionError` ใน `average_unit_value` ได้อย่างแม่นยำ

### จุดที่ AI Reviewer มองข้าม หรือประเมินต่ำไป (AI Blindspots):
1. **Race Condition ใน `concurrent_restock`**: AI ส่วนใหญ่มองเห็นบล็อก `with self._lock:` แล้วด่วนสรุปทันทีว่า *"เมธอดนี้ Thread-safe แล้ว"* โดยมองข้ามว่าบรรทัด `current = ...` นั้นอยู่นอก Lock ทำให้เกิด Lost Update ซึ่งเป็น Bug ร้ายแรงที่สุดในมัลติเธรด
2. **Semantic Bug ใน `average_unit_value`**: AI ไม่เข้าใจความแตกต่างทางบริบทธุรกิจระหว่าง "จำนวนชิ้นสินค้าทั้งหมดในคลัง (Physical Unit Count)" กับ "จำนวนชนิดสินค้า (Distinct SKUs / len(_items))" โดยมองว่า `len(_items)` เป็นตัวแทนของจำนวนสินค้าแล้ว
3. **ปัญหาความไม่เป็น Atomic ของ `sell_batch`**: AI มักประเมินว่าโค้ดวนลูปตัดสต็อกทำงานถูกต้องแล้ว เพราะรันเทสต์กรณี Success ผ่าน โดยมองข้ามประเด็นเรื่อง State Consistency และ Transaction Rollback เมื่อเกิด Partial Failure

---

## 4. คำตอบแบบฝึกหัดส่งท้าย (Concluding Exercises)

### ข้อ 1: การวิเคราะห์ Bug ที่รันได้ปกติในกรณีทั่วไป แต่พังเฉพาะใน Edge Case หรือเมื่อหลาย Thread ทำงานพร้อมกัน
Bug 2 ข้อที่รันได้ปกติใน Happy Path แต่พังในสถานการณ์พิเศษ:
1. **`concurrent_restock` (Race Condition / Lost Update)**:
   - *ทำไมรันปกติได้*: หากรันแบบ Single Thread หรือรัน Unit Test ธรรมดาที่ทำงานแบบเรียงลำดับ (Sequential) โค้ดจะอ่านและบวกค่าได้ถูกต้อง 100% เสมอ
   - *ทำไม Test ธรรมดาจับไม่เจอ*: Unit Test ทั่วไปทดสอบฟังก์ชันในเธรดเดียว จึงไม่เกิดจังหวะที่ 2 เธรดแทรกกลางระหว่างการอ่านค่านอกล็อกกับการเขียนค่าในล็อก บั๊กนี้จะแสดงอาการเฉพาะเมื่อระบบขึ้น Production และมีผู้ใช้งานยิงคำสั่งพร้อมกันในระดับมิลลิวินาทีเท่านั้น
2. **`sell_batch` (Partial Deduct / Non-atomic State)**:
   - *ทำไมรันปกติได้*: เมื่อทดสอบด้วยคำสั่งซื้อที่สินค้าทุกรายการมีสต็อกเพียงพอ โค้ดจะวนลูปสำเร็จและคืนค่ายอดคงเหลืออย่างถูกต้องครบถ้วน
   - *ทำไม Test ธรรมดาจับไม่เจอ*: หากผู้ออกแบบ Test เขียนเฉพาะกรณีปกติ (Happy Path) หรือทดสอบคำสั่งซื้อที่มีเพียงรายการเดียว จะไม่เห็นปัญหาการคืนค่าสต็อกค้างกลางทางเลย ปัญหานี้จะโผล่เมื่อทดสอบ Edge Case ที่รายการที่ $N$ สต็อกไม่พอหลังจากที่รายการที่ $1$ ถึง $N-1$ ถูกตัดไปแล้วเท่านั้น

### ข้อ 2: การออกแบบ Test Case สำหรับ Concurrency Bug
เลือกทดสอบเมธอด `concurrent_restock` เพื่อพิสูจน์การเกิด Lost Update โดยใช้ `pytest` ร่วมกับ `threading` ในภาษา Python:

```python
import threading
import pytest
from inventory import Inventory
from inventory_service import InventoryService

def test_concurrent_restock_lost_update_race_condition():
    # Setup: มีสินค้า 1 รายการ สต็อกเริ่มต้น 0 ชิ้น
    inv = Inventory()
    inv.add_item("TestItem", 0, 100.0)
    service = InventoryService(inv)
    
    num_threads = 20
    restock_per_thread = 10
    expected_total = num_threads * restock_per_thread  # 20 * 10 = 200 ชิ้น
    
    barrier = threading.Barrier(num_threads)  # กลไกปล่อยให้ทุกเธรดเริ่มทำงานพร้อมกันในเสี้ยววินาทีเดียว
    
    def worker():
        barrier.wait()  # รอให้ทุกเธรดพร้อมที่จุดปล่อยตัว
        service.concurrent_restock("TestItem", restock_per_thread)
        
    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    actual_quantity = inv._items["TestItem"].quantity
    # หากโค้ดเดิมมี Lost Update ยอด actual_quantity จะน้อยกว่า expected_total อย่างมีนัยสำคัญ (เช่น ได้เพียง 30 หรือ 50)
    assert actual_quantity == expected_total, (
        f"เกิด Lost Update! คาดหวัง {expected_total} ชิ้น แต่ได้เพียง {actual_quantity} ชิ้น"
    )
```
*คำอธิบายการจำลอง*: การใช้ `threading.Barrier` เป็นเทคนิคหัวใจสำคัญที่บังคับให้เธรดทั้ง 20 เธรดเริ่มรันบรรทัด `concurrent_restock` พร้อมกันทันที เพื่อเพิ่มโอกาสสูงสุดที่เธรดจะอ่านค่า `current` นอกล็อกในจังหวะเดียวกัน ซึ่งจะทำให้ Assert ล้มเหลวและจับ Bug นี้ได้อย่างแน่นอน

### ข้อ 3: การประเมิน AI Reviewer และการแบ่งงานระหว่างคนกับ AI ให้ปลอดภัยที่สุด
จากการเปรียบเทียบ AI Reviewer มีจุดเด่นด้าน **"ความรวดเร็วในการตรวจทานไวยากรณ์ (Syntax), การเปรียบเทียบข้อความใน Docstring กับเงื่อนไขทางคณิตศาสตร์ (< vs <=), และการจับ Exception ทั่วไป"** แต่มีจุดอ่อนร้ายแรงด้าน **"การเข้าใจ Runtime Execution Flow, ปัญหาการประสานงานของเธรด (Concurrency), และเจตจำนงทางธุรกิจ (Business Semantics)"**

**แนวทางการแบ่งงานเพื่อความปลอดภัยสูงสุด (Human-AI Collaboration Matrix)**:
1. **ให้ AI ทำงานเป็น First-pass Linter / Static Auditor**: ตรวจสอบ Style Guide, Missing Type Hints, Dead Code, Boundary mismatch เบื้องต้น และร่างแบบสรุปสรุปความเปลี่ยนแปลงใน PR
2. **มนุษย์ (Senior Software Engineer) รับผิดชอบ Core Architecture Review**: โฟกัสไปที่ Concurrency Safety, Transaction Atomicity, Data Integrity, Security, และ Business Logic Validity เพราะเป็นมิติที่ AI มักละเลยหรือสร้างความมั่นใจผิด ๆ (False Confidence)

### ข้อ 4: การสะท้อนคิด (Reflection - 100 ถึง 150 คำ)
> จากการปฏิบัติการใน Lab 4 ทำให้ตระหนักว่าในยุค AI-Assisted Coding นั้น **"ทักษะการตรวจงาน (Code Review & Evaluation) มีความสำคัญและท้าทายกว่าการพิมพ์โค้ดเองหลายเท่า"** เพราะ AI สามารถสร้างโค้ดที่ดูสะอาด ถูกหลักไวยากรณ์ และรันผ่าน Happy Path ได้ในเวลาเพียงไม่กี่วินาที แต่กลับแฝงข้อบกพร่องระดับวิกฤต เช่น การอ่านค่านอก Lock ที่ทำให้ข้อมูลสูญหาย หรือตรรกะตัดสต็อกที่ไม่เป็น Atomic หากวิศวกรซอฟต์แวร์ขาดความเข้าใจเชิงลึกและเชื่อผลลัพธ์ของ AI อย่างไม่ตรวจสอบ ระบบที่ปล่อยสู่ Production จะพังทลายทันที บทบาทที่แท้จริงของวิศวกรในยุคนี้จึงไม่ใช่แค่ผู้เขียนคำสั่ง แต่คือ **"ผู้ตรวจการที่มีหลักฐาน (Evidence-based Verifier)"** ผู้ควบคุมคุณภาพ และรับผิดชอบต่อความถูกต้องปลอดภัยสูงสุดของซอฟต์แวร์
