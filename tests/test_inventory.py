import pytest

from inventory import Inventory, InventoryItem

# ==============================================================================
# ขั้นที่ 2: TDD Red Phase - ทดสอบเมธอด low_stock_items(threshold)
# ==============================================================================

def test_low_stock_items_all_above_threshold():
    """กรณีที่ 1: สินค้าทุกรายการมีจำนวนมากกว่า threshold -> คืน list ว่าง"""
    inv = Inventory()
    inv.add_item("Keyboard", 10, 500.0)
    inv.add_item("Mouse", 15, 250.0)
    assert inv.low_stock_items(5) == []


def test_low_stock_items_exact_threshold():
    """กรณีที่ 2: มีสินค้าที่จำนวนเท่ากับ threshold พอดี -> ต้องถูกนับรวมด้วย"""
    inv = Inventory()
    inv.add_item("Monitor", 5, 3000.0)
    inv.add_item("Cable", 12, 100.0)
    assert inv.low_stock_items(5) == ["Monitor"]


def test_low_stock_items_sorted_by_name():
    """กรณีที่ 3: มีสินค้าเข้าเกณฑ์หลายรายการ -> ผลลัพธ์เรียงตามชื่อตัวอักษร ไม่ใช่ตามลำดับที่เพิ่ม"""
    inv = Inventory()
    inv.add_item("Zebra Cable", 2, 50.0)
    inv.add_item("Apple Adapter", 1, 150.0)
    inv.add_item("Mango Stand", 3, 200.0)
    assert inv.low_stock_items(4) == ["Apple Adapter", "Mango Stand", "Zebra Cable"]


def test_low_stock_items_empty_inventory():
    """กรณีที่ 4: คลังสินค้าว่างเปล่า -> คืน list ว่าง ไม่ใช่ error"""
    inv = Inventory()
    assert inv.low_stock_items(5) == []


def test_low_stock_items_zero_threshold():
    """กรณีที่ 5: threshold เป็น 0 -> คืนเฉพาะสินค้าที่เหลือ 0 ชิ้นพอดี"""
    inv = Inventory()
    inv.add_item("Out of stock item", 0, 99.0)
    inv.add_item("Available item", 1, 99.0)
    assert inv.low_stock_items(0) == ["Out of stock item"]


def test_low_stock_items_negative_threshold():
    """กรณีที่ 6: threshold ติดลบ -> คืน list ว่าง (เนื่องจากสต็อกสินค้าไม่ติดลบ จึงไม่มีสินค้าใด <= ค่าติดลบ)"""
    inv = Inventory()
    inv.add_item("Item A", 0, 10.0)
    inv.add_item("Item B", 5, 20.0)
    assert inv.low_stock_items(-1) == []


# ==============================================================================
# ขั้นที่ 4: ทดสอบเมธอด sell - กรณีที่ AI ให้มา vs กรณีที่เขียนเสริมเพื่อดัก Edge Cases
# ==============================================================================

# --- กรณีที่ AI ให้มา (Happy Path & Basic Error) ---
def test_sell_basic_success():
    """กรณีพื้นฐานที่ AI ให้มา: ขายสินค้าสำเร็จเมื่อสต็อกเพียงพอ"""
    inv = Inventory()
    inv.add_item("Pen", 10, 20.0)
    remaining = inv.sell("Pen", 3)
    assert remaining == 7


def test_sell_insufficient_stock_basic():
    """กรณีพื้นฐานที่ AI ให้มา: ขายมากกว่าสต็อกที่มี -> เกิด ValueError"""
    inv = Inventory()
    inv.add_item("Notebook", 5, 50.0)
    with pytest.raises(ValueError, match="ไม่เพียงพอสำหรับการขาย"):
        inv.sell("Notebook", 10)


# --- กรณีที่เขียนเสริม (Human-Added Edge Cases & Boundary Tests) ---
def test_sell_exact_all_stock():
    """[กลุ่มค่าขอบ] ขายเท่ากับจำนวนที่เหลือทั้งหมดพอดี -> ต้องสำเร็จและคงเหลือ 0 ชิ้น"""
    inv = Inventory()
    inv.add_item("Flash Drive", 8, 300.0)
    remaining = inv.sell("Flash Drive", 8)
    assert remaining == 0
    assert inv._items["Flash Drive"].quantity == 0


def test_sell_zero_amount():
    """[กลุ่มค่าที่ไม่ควรรับ] ขายจำนวน 0 ชิ้น -> ต้อง raise ValueError('จำนวนที่ขายต้องมากกว่าศูนย์')"""
    inv = Inventory()
    inv.add_item("Desk Pad", 10, 450.0)
    with pytest.raises(ValueError, match="จำนวนที่ขายต้องมากกว่าศูนย์"):
        inv.sell("Desk Pad", 0)
    # ยืนยันว่าสต็อกไม่เปลี่ยน
    assert inv._items["Desk Pad"].quantity == 10


def test_sell_negative_amount():
    """[กลุ่มค่าที่ไม่ควรรับ] ขายจำนวนติดลบ -> ต้อง raise ValueError('จำนวนที่ขายต้องมากกว่าศูนย์')"""
    inv = Inventory()
    inv.add_item("Webcam", 5, 1200.0)
    with pytest.raises(ValueError, match="จำนวนที่ขายต้องมากกว่าศูนย์"):
        inv.sell("Webcam", -3)
    assert inv._items["Webcam"].quantity == 5


def test_sell_non_existent_item():
    """[กลุ่มเส้นทาง error] ขายสินค้าที่ไม่มีในคลัง -> ต้อง raise KeyError พร้อมชื่อสินค้า"""
    inv = Inventory()
    with pytest.raises(KeyError, match="ไม่พบสินค้า 'Ghost Item' ในระบบ"):
        inv.sell("Ghost Item", 1)


def test_sell_insufficient_stock_state_unaltered():
    """[กลุ่มเส้นทาง error] เมื่อขายไม่สำเร็จเนื่องจากสต็อกไม่พอ สต็อกเดิมต้องคงที่ ไม่ถูกหักลบ"""
    inv = Inventory()
    inv.add_item("Headset", 4, 1500.0)
    with pytest.raises(ValueError):
        inv.sell("Headset", 10)
    # ยืนยันว่าค่าคงเหลือยังคงเป็น 4 ชิ้น ไม่ใช่ค่าติดลบหรือเปลี่ยนไป
    assert inv._items["Headset"].quantity == 4


def test_sell_from_zero_stock():
    """[กลุ่มค่าขอบ] สินค้าเหลือ 0 ชิ้น แล้วพยายามขาย 1 ชิ้น -> raise ValueError"""
    inv = Inventory()
    inv.add_item("Empty Box", 0, 10.0)
    with pytest.raises(ValueError, match="ไม่เพียงพอสำหรับการขาย"):
        inv.sell("Empty Box", 1)


# ==============================================================================
# เพิ่มเติม: Unit Tests สำหรับเมธอดอื่น ๆ เพื่อความสมบูรณ์และ Coverage สูง
# ==============================================================================

def test_inventory_item_validation():
    """ทดสอบ Validation ของ InventoryItem"""
    with pytest.raises(ValueError, match="ชื่อสินค้าต้องไม่ว่างเปล่า"):
        InventoryItem("", 10, 100.0)
    with pytest.raises(ValueError, match="ชื่อสินค้าต้องไม่ว่างเปล่า"):
        InventoryItem("   ", 10, 100.0)
    with pytest.raises(ValueError, match="จำนวนสินค้าต้องไม่ติดลบ"):
        InventoryItem("Item", -1, 100.0)
    with pytest.raises(ValueError, match="ราคาต้องมากกว่าศูนย์"):
        InventoryItem("Item", 10, 0.0)
    with pytest.raises(ValueError, match="ราคาต้องมากกว่าศูนย์"):
        InventoryItem("Item", 10, -50.0)


def test_add_item_duplicate():
    """ทดสอบเพิ่มสินค้าซ้ำชื่อเดิม"""
    inv = Inventory()
    inv.add_item("Cup", 5, 50.0)
    with pytest.raises(ValueError, match="มีอยู่ในระบบแล้ว"):
        inv.add_item("Cup", 10, 60.0)


def test_restock_success_and_errors():
    """ทดสอบการเติมสต็อก ทั้งกรณีปกติและ Error paths"""
    inv = Inventory()
    inv.add_item("Paper", 100, 1.5)
    new_qty = inv.restock("Paper", 50)
    assert new_qty == 150

    with pytest.raises(KeyError, match="ไม่พบสินค้า"):
        inv.restock("Unknown", 10)
    with pytest.raises(ValueError, match="จำนวนที่เติมต้องมากกว่าศูนย์"):
        inv.restock("Paper", 0)
    with pytest.raises(ValueError, match="จำนวนที่เติมต้องมากกว่าศูนย์"):
        inv.restock("Paper", -10)


def test_get_total_value():
    """ทดสอบคำนวณมูลค่ารวมสินค้าในคลัง"""
    inv = Inventory()
    assert inv.get_total_value() == 0.0
    inv.add_item("Item1", 2, 100.0)  # 200.0
    inv.add_item("Item2", 3, 50.0)   # 150.0
    assert inv.get_total_value() == 350.0
