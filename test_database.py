"""
Script សាកល្បងមុខងារ Database ទាំងអស់ដោយស្វ័យប្រវត្តិ
"""
import os
import shutil
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import database as db

TEST_DB_PATH = "test_inventory.db"


def run_tests():
    print("🧪 កំពុងចាប់ផ្តើមធ្វើតេស្ត Database...")

    # ប្តូរ DB Path ទៅ Test DB
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    db.DATABASE_PATH = TEST_DB_PATH

    # 1. Init DB
    db.init_db()
    print("✅ 1. បង្កើតតារាង Database ជោគជ័យ!")

    # 2. Register Users
    admin_user = db.register_or_update_user(111222333, "admin_boss", "លោកប្រធាន")
    staff_user = db.register_or_update_user(444555666, "staff_john", "បុគ្គលិក ឃ្លាំង")

    # Manually update admin_user role for testing
    with db.get_connection() as conn:
        conn.execute("UPDATE users SET role = 'admin' WHERE user_id = 111222333;")
        conn.commit()

    assert db.is_admin(111222333) is True
    assert db.is_admin(444555666) is False
    print("✅ 2. ចុះឈ្មោះ និងផ្ទៀងផ្ទាត់សិទ្ធិ User (Admin vs Staff) ជោគជ័យ!")

    # 3. Add Products
    ok, msg, pid1 = db.add_product(
        code="BAR-001",
        name="Coca Cola កំប៉ុង 330ml",
        category="ភេសជ្ជៈ",
        unit="កំប៉ុង",
        cost_price=0.45,
        sell_price=0.75,
        quantity=20,
        min_quantity=5,
        location="ធ្នើរ A-1"
    )
    assert ok is True and pid1 is not None

    ok2, msg2, pid2 = db.add_product(
        code="BAR-002",
        name="ទឹកបរិសុទ្ធ គូលែន 500ml",
        category="ភេសជ្ជៈ",
        unit="ដប",
        cost_price=0.20,
        sell_price=0.50,
        quantity=3,
        min_quantity=10,
        location="ធ្នើរ A-2"
    )
    assert ok2 is True and pid2 is not None

    # Test Duplicate code rejection
    ok_dup, msg_dup, _ = db.add_product(code="BAR-001", name="Duplicated")
    assert ok_dup is False
    print("✅ 3. បន្ថែមទំនិញ និងទប់ស្កាត់កូដស្ទួន (Unique SKU) ជោគជ័យ!")

    # 4. Search Products
    results = db.search_products("coca")
    assert len(results) == 1
    assert results[0]['code'] == "BAR-001"

    results_by_code = db.search_products("BAR-002")
    assert len(results_by_code) == 1
    print("✅ 4. ស្វែងរកទំនិញតាមឈ្មោះ និងលេខកូដជោគជ័យ!")

    # 5. Stock In
    ok_in, msg_in, updated1 = db.record_stock_in(
        product_id=pid1,
        quantity=30,
        unit_price=0.42,
        reference="ទិញបន្ថែមពីអ្នកផ្គត់ផ្គង់",
        user_id=staff_user['user_id']
    )
    assert ok_in is True
    assert updated1['quantity'] == 50  # 20 + 30
    print("✅ 5. នាំចូលទំនិញ (Stock In) បូកស្តុកត្រឹមត្រូវ!")

    # 6. Stock Out
    ok_out, msg_out, updated_out = db.record_stock_out(
        product_id=pid1,
        quantity=46,
        unit_price=0.75,
        reference="លក់ចេញអតិថិជនរាយ",
        user_id=staff_user['user_id']
    )
    assert ok_out is True
    assert updated_out['quantity'] == 4  # 50 - 46
    print("✅ 6. នាំចេញទំនិញ (Stock Out) កាត់ស្តុកត្រឹមត្រូវ!")

    # Test Over-stock deduction prevention
    ok_bad, msg_bad, _ = db.record_stock_out(
        product_id=pid1,
        quantity=10,
        unit_price=0.75,
        reference="ព្យាយាមដកលើសស្តុក",
        user_id=staff_user['user_id']
    )
    assert ok_bad is False
    print("✅ 7. ទប់ស្កាត់ការកាត់ស្តុកលើសពីចំនួនជាក់ស្តែង (Prevent Negative Stock) ជោគជ័យ!")

    # 8. Low Stock Alert
    lows = db.get_low_stock_products()
    # pid1 is now 4 (min is 5) -> low!
    # pid2 is 3 (min is 10) -> low!
    assert len(lows) == 2
    print("✅ 8. ពិនិត្យទំនិញជិតអស់ពីស្តុក (Low Stock Alert) ជោគជ័យ!")

    # 9. Daily Summary
    summary = db.get_daily_summary()
    assert summary['stock_in']['transactions'] == 1
    assert summary['stock_in']['quantity'] == 30
    assert summary['stock_out']['transactions'] == 1
    assert summary['stock_out']['quantity'] == 46
    assert summary['total_products'] == 2
    assert summary['low_stock_count'] == 2
    print("✅ 9. គណនារបាយការណ៍សង្ខេបប្រចាំថ្ងៃ (Daily Summary) ត្រឹមត្រូវ 100%!")

    # Clean up test DB
    import gc
    gc.collect()
    try:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
    except Exception:
        pass

    print("\n🎉 ការធ្វើតេស្តទាំងអស់បានជោគជ័យពេញលេញ (All tests passed)!\n")


if __name__ == "__main__":
    run_tests()
