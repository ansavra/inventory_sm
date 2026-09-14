import csv
import io
from typing import List, Dict, Any


def generate_products_csv(products: List[Dict[str, Any]], is_admin: bool = False) -> str:
    """បង្កើតទិន្នន័យ CSV នៃទំនិញទាំងអស់ ដោយប្រើ UTF-8 BOM សម្រាប់ Microsoft Excel"""
    output = io.StringIO()
    # សរសេរ UTF-8 BOM (\ufeff) ដើម្បីឱ្យ Excel បង្ហាញភាសាខ្មែរត្រឹមត្រូវ ១០០%
    output.write('\ufeff')
    writer = csv.writer(output)

    if is_admin:
        headers = [
            "កូដទំនិញ (Code)", "ឈ្មោះទំនិញ (Name)", "ប្រភេទ (Category)",
            "ចំនួនស្តុក (Quantity)", "ឯកតា (Unit)", "តម្លៃដើម (Cost $)",
            "តម្លៃលក់ (Sell $)", "កម្រិតជូនដំណឹង (Min Qty)", "ទីតាំង (Location)",
            "ផុតកំណត់ជិតបំផុត (Nearest Expiry)", "ឡូតិ៍ផុតកំណត់ទាំងអស់ (Batches)",
            "កាលបរិច្ឆេទបង្កើត"
        ]
    else:
        headers = [
            "កូដទំនិញ (Code)", "ឈ្មោះទំនិញ (Name)", "ប្រភេទ (Category)",
            "ចំនួនស្តុក (Quantity)", "ឯកតា (Unit)",
            "តម្លៃលក់ (Sell $)", "កម្រិតជូនដំណឹង (Min Qty)", "ទីតាំង (Location)",
            "ផុតកំណត់ជិតបំផុត (Nearest Expiry)", "ឡូតិ៍ផុតកំណត់ទាំងអស់ (Batches)",
            "កាលបរិច្ឆេទបង្កើត"
        ]
    writer.writerow(headers)

    for p in products:
        created = p.get('created_at', '')
        nearest = p.get('nearest_expiry') or ''
        batches_str = "; ".join(f"{b['expiry_date']} x{b['quantity']}" for b in (p.get('batches') or []))
        if is_admin:
            writer.writerow([
                p.get('code', ''),
                p.get('name', ''),
                p.get('category', ''),
                p.get('quantity', 0),
                p.get('unit', ''),
                f"{float(p.get('cost_price') or 0.0):.2f}",
                f"{float(p.get('sell_price') or 0.0):.2f}",
                p.get('min_quantity', 5),
                p.get('location', ''),
                nearest,
                batches_str,
                created
            ])
        else:
            writer.writerow([
                p.get('code', ''),
                p.get('name', ''),
                p.get('category', ''),
                p.get('quantity', 0),
                p.get('unit', ''),
                f"{float(p.get('sell_price') or 0.0):.2f}",
                p.get('min_quantity', 5),
                p.get('location', ''),
                nearest,
                batches_str,
                created
            ])
    return output.getvalue()


def generate_transactions_csv(transactions: List[Dict[str, Any]], is_admin: bool = False) -> str:
    """បង្កើតទិន្នន័យ CSV នៃប្រវត្តិប្រតិបត្តិការទាំងអស់"""
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)

    headers = [
        "កាលបរិច្ឆេទ & ម៉ោង", "ប្រភេទ", "កូដទំនិញ", "ឈ្មោះទំនិញ",
        "ចំនួន", "ឯកតា", "ថ្ងៃផុតកំណត់ (Expiry)", "តម្លៃរាយ ($)", "តម្លៃសរុប ($)",
        "កំណត់ចំណាំ / វិក្កយបត្រ", "អ្នកកត់ត្រា"
    ]
    writer.writerow(headers)

    for t in transactions:
        tx_type = "នាំចូល (IN)" if t.get('type') == 'IN' else "នាំចេញ (OUT)"
        is_in = t.get('type') == 'IN'
        if is_in and not is_admin:
            unit_price = "🔒"
            total_price = "🔒"
        else:
            unit_price = f"{float(t.get('unit_price') or 0.0):.2f}"
            total_price = f"{float(t.get('total_price') or 0.0):.2f}"

        writer.writerow([
            t.get('created_at', ''),
            tx_type,
            t.get('product_code', ''),
            t.get('product_name', ''),
            t.get('quantity', 0),
            t.get('product_unit', ''),
            t.get('expiry_date') or '',
            unit_price,
            total_price,
            t.get('reference', ''),
            t.get('user_name', '')
        ])
    return output.getvalue()
