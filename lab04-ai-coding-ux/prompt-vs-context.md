# การเปรียบเทียบ Prompt Engineering กับ Context Engineering - Lab 04

เอกสารฉบับนี้เป็นการทดลองและวิเคราะห์เปรียบเทียบการสั่งงาน AI Coding Assistant เพื่อสร้างเมธอดการขายสินค้าหลายรายการพร้อมกัน (Batch Sell) โดยเปรียบเทียบระหว่างการใช้ **Prompt สั้นที่ขาดบริบท** กับ **Prompt ที่มี Context ครบถ้วน** ภายใต้ระบบ Inventory Management เดิม

---

## 1. การทดลองรอบที่ 1: Prompt สั้น ขาด Context (Prompt-Only)

### คำสั่ง Prompt (รอบที่ 1)
```text
เขียน function ลด stock ในคลังสินค้าหลายรายการพร้อมกันด้วยภาษา Python
```

### ผลลัพธ์โค้ดที่ AI สร้างขึ้น (รอบที่ 1)
```python
def reduce_stock(inventory_dict, orders):
    """
    ลดจำนวนสต็อกสินค้าหลายรายการพร้อมกัน
    orders: dict เช่น {"item_a": 2, "item_b": 5}
    """
    for item, qty in orders.items():
        if item in inventory_dict:
            if inventory_dict[item] >= qty:
                inventory_dict[item] -= qty
            else:
                print(f"Error: {item} not enough stock")
        else:
            print(f"Error: {item} not found")
    return inventory_dict
```

### การวิเคราะห์ผลลัพธ์รอบที่ 1
1. **ไม่เข้ากับสถาปัตยกรรมเดิม (Architectural Incompatibility)**: AI สร้างฟังก์ชันแบบ Standalone ที่รับ `dict` ธรรมดา ไม่รู้จักคลาส `Inventory` หรือ `InventoryItem` ของระบบเดิม ทำให้ไม่สามารถนำไปใช้งานในโปรเจกต์ได้เลย
2. **ไม่เป็น Atomic (Non-Atomic Execution)**: โค้ดวนลูปตัดสต็อกไปทีละรายการ หากสินค้าตัวที่ 2 หรือ 3 สต็อกไม่พอ รายการตัวแรกก็ถูกตัดสต็อกไปเรียบร้อยแล้ว ไม่มีการ Rollback คืนค่า ส่งผลให้ข้อมูลสต็อกในคลังเพี้ยนทันที
3. **การจัดการข้อผิดพลาดบกพร่อง**: ใช้คำสั่ง `print()` แทนที่จะ raise Exception ตามแบบแผนมาตรฐานซอฟต์แวร์ ทำให้โค้ดภายนอกที่เรียกใช้งานไม่สามารถดักจับ (Catch) ข้อผิดพลาดได้

---

## 2. การทดลองรอบที่ 2: Prompt ที่มี Context ครบถ้วน (Context Engineering)

### คำสั่ง Prompt (รอบที่ 2)
```text
ช่วยปรับปรุงและเพิ่มเมธอด sell_many() ให้กับคลาส Inventory ด้านล่าง เพื่อรองรับการขายสินค้าหลายรายการพร้อมกัน (Batch Order Processing)

[Context 1: โค้ดฐานระบบเดิม inventory.py]
class InventoryItem:
    def __init__(self, name: str, quantity: int, price: float):
        if not name or not name.strip():
            raise ValueError("ชื่อสินค้าต้องไม่ว่างเปล่า")
        if quantity < 0:
            raise ValueError("จำนวนสินค้าต้องไม่ติดลบ")
        if price <= 0:
            raise ValueError("ราคาต้องมากกว่าศูนย์")
        self.name = name.strip()
        self.quantity = quantity
        self.price = price

class Inventory:
    def __init__(self):
        self._items: dict[str, InventoryItem] = {}

    def add_item(self, name: str, quantity: int, price: float) -> InventoryItem:
        if name in self._items:
            raise ValueError(f"สินค้า '{name}' มีอยู่ในระบบแล้ว")
        item = InventoryItem(name, quantity, price)
        self._items[name] = item
        return item

    def restock(self, name: str, amount: int) -> int:
        if name not in self._items:
            raise KeyError(f"ไม่พบสินค้า '{name}' ในระบบ")
        if amount <= 0:
            raise ValueError("จำนวนที่เติมต้องมากกว่าศูนย์")
        self._items[name].quantity += amount
        return self._items[name].quantity

    def sell(self, name: str, amount: int) -> int:
        if name not in self._items:
            raise KeyError(f"ไม่พบสินค้า '{name}' ในระบบ")
        if amount <= 0:
            raise ValueError("จำนวนที่ขายต้องมากกว่าศูนย์")
        if self._items[name].quantity < amount:
            raise ValueError(
                f"สินค้า '{name}' คงเหลือ {self._items[name].quantity} ชิ้น "
                f"ไม่เพียงพอสำหรับการขาย {amount} ชิ้น"
            )
        self._items[name].quantity -= amount
        return self._items[name].quantity

    def get_total_value(self) -> float:
        return sum(item.quantity * item.price for item in self._items.values())

[Context 2: ข้อกำหนดทางเทคนิค (Technical Specifications & Constraints)]
- เพิ่มเมธอด sell_many(orders: dict[str, int]) -> dict[str, int] โดยคืนค่าเป็น {ชื่อสินค้า: จำนวนคงเหลือล่าสุด}
- คุณสมบัติ Atomicity: ทุกรายการใน orders ต้องขายสำเร็จพร้อมกันทั้งหมด หากมีแม้แต่รายการเดียวที่ stock ไม่พอ หรือไม่มีสินค้า หรือ amount <= 0 ต้อง raise Exception และต้องไม่หักยอดสินค้าตัวใดเลยเด็ดขาด (Rollback / No partial deduction)
- รูปแบบ Exception ต้องสอดคล้องกับคลาสเดิม:
  * raise KeyError หากมีสินค้าใดใน orders ที่ไม่มีอยู่ในระบบ
  * raise ValueError หาก amount <= 0 หรือ stock ไม่เพียงพอ
- ห้ามใช้ไลบรารีภายนอก ใช้เฉพาะ Standard Python 3.11+
- มี Type Hints ชัดเจน และเคารพ Encapsulation เดิมของคลาส Inventory

[Context 3: ชุด Unit Test ที่โค้ดต้องผ่าน]
1. test_sell_many_success: ขาย 2 รายการพร้อมกันสำเร็จ คืนยอดคงเหลือถูกต้อง
2. test_sell_many_insufficient_stock_rollback: รายการแรกพอ แต่รายการสองไม่พอ -> ต้อง raise ValueError และยอดคงเหลือของรายการแรกต้องไม่ลดลงเลย (Atomic Rollback)
3. test_sell_many_missing_item: มีชื่อสินค้าที่ไม่มีในคลัง -> raise KeyError และไม่หักยอดใด ๆ
```

### ผลลัพธ์โค้ดที่ AI สร้างขึ้น (รอบที่ 2)
```python
    def sell_many(self, orders: dict[str, int]) -> dict[str, int]:
        """
        ขายสินค้าหลายรายการพร้อมกันแบบ Atomic (Transaction-safe)
        หากมีรายการใดรายการหนึ่งไม่ผ่าน จะไม่หักสต็อกของสินค้าตัวใดเลย
        คืนค่า {ชื่อสินค้า: จำนวนคงเหลือล่าสุด}
        """
        if not orders:
            return {}

        # 1. Validation Phase (ตรวจสอบความถูกต้องและปริมาณสต็อกของทุกรายการก่อนหักจริง)
        for name, amount in orders.items():
            if name not in self._items:
                raise KeyError(f"ไม่พบสินค้า '{name}' ในระบบ")
            if amount <= 0:
                raise ValueError(f"จำนวนที่ขายสำหรับสินค้า '{name}' ต้องมากกว่าศูนย์")
            if self._items[name].quantity < amount:
                raise ValueError(
                    f"สินค้า '{name}' คงเหลือ {self._items[name].quantity} ชิ้น "
                    f"ไม่เพียงพอสำหรับการขาย {amount} ชิ้น"
                )

        # 2. Execution Phase (หักสต็อกเมื่อทุกรายการผ่านการตรวจสอบแล้ว 100%)
        result: dict[str, int] = {}
        for name, amount in orders.items():
            self._items[name].quantity -= amount
            result[name] = self._items[name].quantity

        return result
```

---

## 3. สรุปการเปรียบเทียบ: อะไรทำให้ผลลัพธ์ทั้งสองรอบต่างกัน?

| ประเด็นเปรียบเทียบ | รอบที่ 1: Prompt สั้น ขาด Context | รอบที่ 2: มี Context ครบถ้วน | ปัจจัยที่สร้างความแตกต่าง |
| :--- | :--- | :--- | :--- |
| **1. ความเข้ากันได้กับโค้ดเดิม** | สร้างฟังก์ชันอิสระ ไม่สามารถนำไปเสียบเข้ากับโปรเจกต์เดิมได้ | เป็นเมธอดในคลาส `Inventory` เชื่อมโยงกับ `self._items` และ `InventoryItem` เดิมได้อย่างสมบูรณ์แบบ | **Interface & Schema Context**: การแนบโค้ดเดิมทั้งไฟล์ทำให้ AI เข้าใจ Data Structure และ Class Architecture |
| **2. ความถูกต้องเชิงตรรกะ (Atomicity)** | ทำงานแบบ Step-by-step ที่เสี่ยงต่อการเกิด Partial State Corruption | แยกเป็น 2-Phase Commit (Validation Phase แล้วจึง Execution Phase) ทำให้มีคุณสมบัติ Atomic 100% | **Constraint & Safety Requirements**: การกำหนดชัดเจนว่าต้อง rollback และห้ามหักสินค้าตัวใดเลยหากมีข้อผิดพลาด |
| **3. มาตรฐานการจัดการข้อผิดพลาด (Exception Handling)** | ใช้ `print()` แสดงข้อความ ทำให้ไม่สามารถใช้ในระดับ Production หรือเขียน Unit Test ดักจับได้ | raise `KeyError` และ `ValueError` ที่มีข้อความสื่อความหมายตรงตาม convention ของคลาสเดิม | **Coding Convention Context**: การแนบ Exception Specification ทำให้ AI เลียนแบบการจัดการ error ของโค้ดเดิม |
| **4. การรองรับการทดสอบ (Testability)** | ไม่มีเกณฑ์ตรวจสอบ ไม่การันตีความถูกต้อง | ผ่าน Unit Test ทั้ง 3 กรณีที่แนบไปใน Prompt ทันทีตั้งแต่รอบแรก | **Test Cases as Specification**: การแนบ Test Scenarios ทำหน้าที่เป็น Acceptance Criteria ที่ตีกรอบพฤติกรรมของโค้ดให้แคบและแม่นยำที่สุด |

### บทเรียนสำคัญ (Key Takeaway)
> **Prompt Engineering** คือการบอกว่า *"ต้องการให้ทำอะไร ในรูปแบบใด"* (เช่น ขอเมธอด `sell_many`, มี Type Hint)  
> ส่วน **Context Engineering** คือการเตรียม *"สภาพแวดล้อม กฎเกณฑ์ ข้อจำกัด และข้อมูลเดิม"* (เช่น โค้ดฐาน `inventory.py`, พฤติกรรม Atomic, ชนิดของ Exception, และ Test Cases)  
> 
> หากไม่มี Context ต่อให้เขียน Prompt สวยหรูเพียงใด AI ก็จะทำได้เพียงการ **"เดาสุ่มตามความน่าจะเป็นทางสถิติ"** ซึ่งมักได้โค้ดที่รันเดี่ยว ๆ ได้แต่พังเมื่อนำไปประกอบเข้ากับระบบจริง การให้ Context ที่ครบถ้วนจึงเป็นกุญแจสำคัญที่สุดในการใช้วิศวกรรม AI ช่วยเขียนโค้ดได้อย่างปลอดภัย
