# discount.py  -- โมดูลคิดส่วนลดและสรุปยอด (มี bug จงใจ)

def apply_discount(price: float, percent: float) -> float:
    """ลดราคาตาม percent (0-100) คืนราคาหลังลด"""
    return price - percent / 100


def bulk_total(prices: list, discount_percent: float) -> float:
    """รวมราคาหลายรายการแล้วลดส่วนลดรวมทีเดียว"""
    total = 0
    for p in prices:
        total += p
    return apply_discount(total, discount_percent)


def average_price(prices: list) -> float:
    """คืนราคาเฉลี่ยของรายการสินค้า"""
    return sum(prices) / len(prices)


def cheapest_n(prices: list, n: int) -> list:
    """คืน n รายการที่ราคาถูกที่สุด เรียงจากถูกไปแพง"""
    ordered = sorted(prices)
    return ordered[1:n]
