import pytest
from inventory import Inventory


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
    # เพิ่มตามลำดับ: Zebra, Apple, Mango
    inv.add_item("Zebra Cable", 2, 50.0)
    inv.add_item("Apple Adapter", 1, 150.0)
    inv.add_item("Mango Stand", 3, 200.0)
    # คาดหวังการเรียงตามตัวอักษร: Apple Adapter, Mango Stand, Zebra Cable
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
