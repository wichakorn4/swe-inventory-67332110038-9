import datetime

import pytest

import pricing_service as pricing_legacy
from pricing_service import calc


@pytest.fixture(autouse=True)
def reset_globals():
    """ล้างสถานะ Global Mutable State (member_points และ LOG) ก่อนเริ่มทุก test"""
    pricing_legacy.member_points.clear()
    pricing_legacy.LOG.clear()
    yield
    pricing_legacy.member_points.clear()
    pricing_legacy.LOG.clear()


# ==============================================================================
# กลุ่มที่ 1: ราคาปกติ (Normal Price)
# สินค้าหนึ่งรายการ จำนวนน้อย ไม่ใช้สิทธิ์สมาชิกหรือคูปองใด ๆ
# ==============================================================================
def test_normal_price_single_item():
    """สินค้า 1 รายการ 2 ชิ้น ชิ้นละ 100 บาท + ภาษี 7% = 214.0 บาท"""
    items = [("Pen", 2, 100.0)]
    assert calc(items) == 214.0


def test_normal_price_multiple_items():
    """สินค้าหลายรายการ จำนวนน้อย: (1*100) + (2*50) = 200 + ภาษี 7% = 214.0 บาท"""
    items = [("Notebook", 1, 100.0), ("Eraser", 2, 50.0)]
    assert calc(items) == 214.0


# ==============================================================================
# กลุ่มที่ 2: ซื้อจำนวนมาก (Bulk Purchase Tier Discounts)
# เกณฑ์ขั้นต่ำ: 50 ชิ้น ลด 5% (คูณ 0.95), 100 ชิ้น ลด 10% (คูณ 0.9)
# ==============================================================================
def test_bulk_discount_tier_50_exact():
    """จำนวนเท่ากับ 50 พอดี -> ลด 5%: 50 * 100 * 0.95 = 4750 + ภาษี 7% = 5082.5 บาท"""
    items = [("Paper", 50, 100.0)]
    assert calc(items) == 5082.5


def test_bulk_discount_tier_49_just_below():
    """จำนวน 49 ชิ้น (ต่ำกว่าเกณฑ์ 50) -> ไม่ได้ส่วนลด: 49 * 100 = 4900 + ภาษี 7% = 5243.0 บาท"""
    items = [("Paper", 49, 100.0)]
    assert calc(items) == 5243.0


def test_bulk_discount_tier_100_exact():
    """จำนวนเท่ากับ 100 พอดี -> ลด 10%: 100 * 100 * 0.9 = 9000 + ภาษี 7% = 9630.0 บาท"""
    items = [("Folder", 100, 100.0)]
    assert calc(items) == 9630.0


def test_bulk_discount_tier_99_just_below():
    """จำนวน 99 ชิ้น (เข้าเกณฑ์ขั้น 50 ไม่ถึง 100) -> ลด 5%: 99*100*0.95 = 9405 + ภาษี = 10063.35"""
    items = [("Folder", 99, 100.0)]
    assert calc(items) == 10063.35


# ==============================================================================
# กลุ่มที่ 3: จำนวนเป็นศูนย์หรือติดลบ (Zero & Negative Quantity)
# ==============================================================================
def test_quantity_zero():
    """สินค้าที่ใส่จำนวน 0 ชิ้น -> ถูกข้าม ไม่นำมาคิด ยอดรวมเป็น 0.0 บาท"""
    items = [("Sample", 0, 500.0)]
    assert calc(items) == 0.0


def test_quantity_negative():
    """สินค้าที่ใส่จำนวนติดลบ (-5 ชิ้น) -> ถูกข้าม ยอดรวมเป็น 0.0 บาท"""
    items = [("Return", -5, 100.0)]
    assert calc(items) == 0.0


# ==============================================================================
# กลุ่มที่ 4: สมาชิก (Member Discount & Loyalty Points)
# สมาชิกลด 5% และสะสมแต้ม 1 แต้มต่อ 100 บาท (int(t / 100))
# ==============================================================================
def test_member_discount_and_points():
    """สมาชิกใหม่ ซื้อ 200 บาท -> ลด 5% เหลือ 190 -> แต้ม int(190/100) = 1 แต้ม -> +ภาษี 7% = 203.3 บาท"""
    items = [("Pen", 2, 100.0)]
    total = calc(items, member="Somchai")
    assert total == 203.3
    assert pricing_legacy.member_points["Somchai"] == 1


def test_member_points_accumulation():
    """สมาชิกเดิม ซื้อซ้ำ แต้มต้องสะสมต่อเนื่อง"""
    pricing_legacy.member_points["Somchai"] = 5
    items = [("Pen", 2, 100.0)]
    calc(items, member="Somchai")
    # ได้เพิ่ม 1 แต้ม รวมเป็น 5 + 1 = 6 แต้ม
    assert pricing_legacy.member_points["Somchai"] == 6


# ==============================================================================
# กลุ่มที่ 5: คูปอง (Coupons: SAVE50, HALF, NEWYEAR)
# ==============================================================================
def test_coupon_save50():
    """คูปอง SAVE50: ลด 50 บาท (200 - 50 = 150) + ภาษี 7% = 160.5 บาท"""
    items = [("Pen", 2, 100.0)]
    assert calc(items, coupon="SAVE50") == 160.5


def test_coupon_half():
    """คูปอง HALF: ลด 50% (200 * 0.5 = 100) + ภาษี 7% = 107.0 บาท"""
    items = [("Pen", 2, 100.0)]
    assert calc(items, coupon="HALF") == 107.0


def test_coupon_newyear_in_january():
    """คูปอง NEWYEAR ใช้ในเดือนมกราคม -> ลด 20% (200 * 0.8 = 160) + ภาษี 7% = 171.2 บาท"""
    items = [("Pen", 2, 100.0)]
    january_date = datetime.date(2026, 1, 15)
    assert calc(items, coupon="NEWYEAR", today=january_date) == 171.2


def test_coupon_newyear_outside_january():
    """คูปอง NEWYEAR ใช้นอกเดือนมกราคม -> ไม่ได้ลด (200 บาท) + ภาษี 7% = 214.0 บาท"""
    items = [("Pen", 2, 100.0)]
    may_date = datetime.date(2026, 5, 20)
    assert calc(items, coupon="NEWYEAR", today=may_date) == 214.0


# ==============================================================================
# กลุ่มที่ 6: ยอดติดลบ (Negative Subtotal Clamping)
# ส่วนลดมากกว่าราคาสินค้า -> ต้อง clamp ยอดกลับมาเป็น 0.0 บาท
# ==============================================================================
def test_discount_exceeds_price_clamped_to_zero():
    """ราคาสินค้า 30 บาท ใช้คูปอง SAVE50 (30 - 50 = -20) -> ถูกปรับเป็น 0 + ภาษี = 0.0 บาท"""
    items = [("Eraser", 1, 30.0)]
    assert calc(items, coupon="SAVE50") == 0.0


# ==============================================================================
# กลุ่มที่ 7: ค่าที่ฟังก์ชันเก็บไว้ (Internal State & Side Effects)
# บันทึกประวัติการเรียกฟังก์ชันลง LOG = [(member, total)]
# ==============================================================================
def test_log_side_effect():
    """ฟังก์ชันต้องบันทึก tuple (member, total) ลงใน LOG ทุกครั้งที่เรียก"""
    items = [("Pen", 2, 100.0)]
    calc(items, member="Somchai")
    calc(items, member=None)
    assert len(pricing_legacy.LOG) == 2
    assert pricing_legacy.LOG[0] == ("Somchai", 203.3)
    assert pricing_legacy.LOG[1] == (None, 214.0)
