"""โมดูลคำนวณราคาและส่วนลดของระบบ Inventory (Refactored Version)

ปรับปรุงโครงสร้างจาก pricing_legacy.py ให้อ่านง่าย มี Type Hints ครบถ้วน
แยกฟังก์ชันย่อยตามหลัก Single Responsibility และขจัด Magic Numbers
โดยยังคงรักษาพฤติกรรม ตรรกะ และผลลัพธ์เดิมไว้ 100%
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence

# ==============================================================================
# ค่าคงที่นโยบายราคาและส่วนลด (Named Constants)
# ==============================================================================
TAX_RATE: float = 0.07

BULK_TIER_2_MIN_QTY: int = 100
BULK_TIER_2_DISCOUNT_FACTOR: float = 0.90  # ลด 10%

BULK_TIER_1_MIN_QTY: int = 50
BULK_TIER_1_DISCOUNT_FACTOR: float = 0.95  # ลด 5%

MEMBER_DISCOUNT_FACTOR: float = 0.95       # สมาชิกลด 5%
MEMBER_POINTS_PER_BAHT: int = 100          # 1 แต้มต่อ 100 บาท

COUPON_SAVE50_AMOUNT: float = 50.0
COUPON_HALF_DISCOUNT_FACTOR: float = 0.50
COUPON_NEWYEAR_DISCOUNT_FACTOR: float = 0.80

# สถานะส่วนกลางเพื่อรักษาความเข้ากันได้กับโค้ดเดิม (Backward Compatibility)
member_points: dict[str, int] = {}
LOG: list[tuple[str | None, float]] = []


def _calculate_item_subtotal(quantity: int, unit_price: float) -> float:
    """คำนวณราคาย่อยของสินค้าแต่ละรายการ พร้อมส่วนลดตามปริมาณการซื้อ (Bulk Discount)"""
    if quantity <= 0:
        return 0.0

    subtotal = quantity * unit_price
    if quantity >= BULK_TIER_2_MIN_QTY:
        subtotal *= BULK_TIER_2_DISCOUNT_FACTOR
    elif quantity >= BULK_TIER_1_MIN_QTY:
        subtotal *= BULK_TIER_1_DISCOUNT_FACTOR

    return subtotal


def _apply_member_discount_and_points(
    current_total: float,
    member: str | None,
) -> float:
    """คำนวณส่วนลดสมาชิก 5% และบันทึกแต้มสะสม (1 แต้มต่อทุก 100 บาท)"""
    if member is None:
        return current_total

    if member not in member_points:
        member_points[member] = 0

    discounted_total = current_total * MEMBER_DISCOUNT_FACTOR
    earned_points = int(discounted_total / MEMBER_POINTS_PER_BAHT)
    member_points[member] += earned_points

    return discounted_total


def _apply_coupon_discount(
    current_total: float,
    coupon: str | None,
    today: datetime.date | None,
) -> float:
    """ตรวจสอบและหักส่วนลดตามรหัสคูปองโปรโมชัน"""
    if coupon is None:
        return current_total

    if coupon == "SAVE50":
        return current_total - COUPON_SAVE50_AMOUNT

    if coupon == "HALF":
        return current_total * COUPON_HALF_DISCOUNT_FACTOR

    if coupon == "NEWYEAR":
        effective_date = today if today is not None else datetime.date.today()
        if effective_date.month == 1:
            return current_total * COUPON_NEWYEAR_DISCOUNT_FACTOR

    return current_total


def calc(
    items: Sequence[tuple[str, int, float]],
    member: str | None = None,
    coupon: str | None = None,
    today: datetime.date | None = None,
) -> float:
    """คำนวณราคาสุทธิรวมภาษีมูลค่าเพิ่มสำหรับรายการสินค้าที่สั่งซื้อ

    Args:
        items: ลำดับของข้อมูลสินค้าแต่ละรายการ ในรูปแบบ (ชื่อ, จำนวน, ราคาต่อหน่วย)
        member: ชื่อหรือรหัสสมาชิก (ถ้ามี)
        coupon: รหัสคูปองส่วนลด เช่น 'SAVE50', 'HALF', 'NEWYEAR' (ถ้ามี)
        today: วันที่สำหรับตรวจสอบเงื่อนไขเวลาของคูปอง (ถ้าไม่ระบุใช้วันปัจจุบัน)

    Returns:
        ราคาสุทธิหลังหักส่วนลดทุกขั้นและรวมภาษีมูลค่าเพิ่ม 7% ปัดเศษทศนิยม 2 ตำแหน่ง
    """
    # 1. คำนวณราคารวมสินค้าทุกรายการ (พร้อมส่วนลด Bulk)
    running_total = sum(
        _calculate_item_subtotal(quantity=item[1], unit_price=item[2])
        for item in items
    )

    # 2. คิดส่วนลดสมาชิกและคำนวณแต้มสะสม
    running_total = _apply_member_discount_and_points(running_total, member)

    # 3. คิดส่วนลดคูปอง
    running_total = _apply_coupon_discount(running_total, coupon, today)

    # 4. ป้องกันยอดติดลบ (Clamping at zero)
    if running_total < 0:
        running_total = 0.0

    # 5. บวกภาษีมูลค่าเพิ่ม (VAT 7%) และปัดเศษทศนิยม 2 ตำแหน่ง
    total_with_tax = running_total + (running_total * TAX_RATE)
    final_price = round(total_with_tax, 2)

    # 6. บันทึก Audit Log
    LOG.append((member, final_price))

    return final_price
