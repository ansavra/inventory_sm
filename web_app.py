import os
import sys
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Response, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

import database as db
import auth
import export_service
import google_sheets_sync
import notifier

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Inventory Management Dashboard", version="1.0.0")

# Static & Templates setup
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "css").mkdir(exist_ok=True)
(STATIC_DIR / "js").mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")



# ==========================================
# Auth Dependencies
# ==========================================

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    token = request.cookies.get("session_token")
    return auth.get_session(token)


def require_auth(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="សូម Login ជាមុនសិន"
        )
    return user


def require_admin(user: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="មានតែ Admin ទើបមានសិទ្ធិអនុវត្តមុខងារនេះបាន!"
        )
    return user


# ==========================================
# Pydantic Request Models
# ==========================================

class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "staff"


class ProductCreateRequest(BaseModel):
    code: str
    name: str
    category: str = "ទូទៅ"
    unit: str = "ឯកតា"
    cost_price: float = 0.0
    sell_price: float = 0.0
    quantity: int = 0
    min_quantity: int = 5
    location: str = "ឃ្លាំងធំ"


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    cost_price: Optional[float] = None
    sell_price: Optional[float] = None
    min_quantity: Optional[int] = None
    location: Optional[str] = None


class StockInRequest(BaseModel):
    product_id: int
    quantity: int
    unit_price: float = 0.0
    reference: str = "នាំចូលតាម Web"


class StockOutRequest(BaseModel):
    product_id: int
    quantity: int
    unit_price: float = 0.0
    reference: str = "លក់ចេញតាម Web"


class StockAdjustRequest(BaseModel):
    product_id: int
    new_quantity: int
    reason: str = "កែសម្រួលតាម Web"


# ==========================================
# Frontend Routes (HTML)
# ==========================================

@app.get("/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    login_file = TEMPLATES_DIR / "login.html"
    if not login_file.exists():
        return HTMLResponse("<h3>Login page not found</h3>", status_code=404)
    return FileResponse(login_file)


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h3>Template index.html not found</h3>", status_code=404)
    return FileResponse(index_file)


# ==========================================
# Auth Endpoints
# ==========================================

@app.post("/api/login")
async def api_login(req: LoginRequest, response: Response):
    user = db.verify_user_credentials(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ឈ្មោះគណនី ឬលេខសម្ងាត់មិនត្រឹមត្រូវទេ!"
        )

    token = auth.create_session(user)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=auth.SESSION_EXPIRY_SECONDS
    )
    return {
        "success": True,
        "message": "Login ជោគជ័យ!",
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    }


@app.post("/api/logout")
async def api_logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    auth.delete_session(token)
    response.delete_cookie(key="session_token")
    return {"success": True, "message": "បានចាកចេញដោយជោគជ័យ"}


@app.get("/api/me")
async def api_me(user: Dict[str, Any] = Depends(require_auth)):
    """ព័ត៌មាន User បច្ចុប្បន្ន"""
    return user


# ==========================================
# User Management Endpoints (Admin Only)
# ==========================================

@app.get("/api/users")
async def get_users(admin: Dict[str, Any] = Depends(require_admin)):
    """បញ្ជី User ទាំងអស់សម្រាប់ Admin"""
    return db.list_web_users()


@app.post("/api/users")
async def create_user_endpoint(req: UserCreateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    """បង្កើតគណនីបុគ្គលិកថ្មី"""
    success, msg, new_id = db.create_web_user(
        username=req.username,
        password=req.password,
        full_name=req.full_name,
        role=req.role
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg, "id": new_id}


@app.delete("/api/users/{user_id}")
async def delete_user_endpoint(user_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    """លុបគណនី User"""
    success, msg = db.delete_user_by_id(user_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


# ==========================================
# Inventory & Transactions Endpoints
# ==========================================

@app.get("/api/stats")
async def get_dashboard_stats(user: Dict[str, Any] = Depends(require_auth)):
    """ស្ថិតិទូទៅ (លាក់តម្លៃដើមបើជា Staff)"""
    products = db.list_all_products(limit=1000)
    low_stocks = db.get_low_stock_products()
    daily_summary = db.get_daily_summary()

    is_admin = (user.get("role") == "admin")

    total_cost_val = sum(p['quantity'] * p['cost_price'] for p in products) if is_admin else 0.0
    total_sell_val = sum(p['quantity'] * p['sell_price'] for p in products)

    # Mask daily summary financials if staff
    if not is_admin:
        daily_summary["stock_in"]["amount"] = 0.0
        daily_summary["stock_out"]["amount"] = 0.0

    return {
        "total_products": len(products),
        "low_stock_count": len(low_stocks),
        "total_asset_cost": round(total_cost_val, 2),
        "total_potential_revenue": round(total_sell_val, 2),
        "daily_summary": daily_summary,
        "is_admin": is_admin
    }


@app.get("/api/products")
async def list_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    user: Dict[str, Any] = Depends(require_auth)
):
    """បញ្ជីទំនិញ (លាក់ cost_price បើជា Staff)"""
    if search:
        products = db.search_products(search, limit=100)
    else:
        products = db.list_all_products(limit=500)

    if category and category != "all":
        products = [p for p in products if p['category'] == category]

    is_admin = (user.get("role") == "admin")
    if not is_admin:
        # Mask cost price for staff
        for p in products:
            p['cost_price'] = 0.0

    return products


@app.get("/api/products/{product_id}")
async def get_product(product_id: int, user: Dict[str, Any] = Depends(require_auth)):
    prod = db.get_product_by_id(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="រកមិនឃើញទំនិញនេះទេ")
    if user.get("role") != "admin":
        prod['cost_price'] = 0.0
    return prod


@app.post("/api/products")
async def create_product(req: ProductCreateRequest, user: Dict[str, Any] = Depends(require_auth)):
    success, msg, prod_id = db.add_product(
        code=req.code,
        name=req.name,
        category=req.category,
        unit=req.unit,
        cost_price=req.cost_price,
        sell_price=req.sell_price,
        quantity=req.quantity,
        min_quantity=req.min_quantity,
        location=req.location
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)

    # Auto sync new product to Google Sheet
    google_sheets_sync.sync_product(
        code=req.code,
        name=req.name,
        category=req.category,
        unit=req.unit,
        cost_price=req.cost_price,
        sell_price=req.sell_price,
        quantity=req.quantity,
        location=req.location
    )

    if req.quantity > 0 and prod_id:
        db.record_stock_in(
            product_id=prod_id,
            quantity=req.quantity,
            unit_price=req.cost_price,
            reference="ស្តុកដំបូងពេលបង្កើតតាម Web",
            user_id=user["user_id"]
        )

    return {"success": True, "message": "បង្កើតទំនិញថ្មីបានជោគជ័យ", "id": prod_id}


@app.put("/api/products/{product_id}")
async def update_product_endpoint(
    product_id: int,
    req: ProductUpdateRequest,
    user: Dict[str, Any] = Depends(require_auth)
):
    cost_val = req.cost_price if user.get("role") == "admin" else None
    success, msg = db.update_product(
        product_id=product_id,
        name=req.name,
        category=req.category,
        unit=req.unit,
        cost_price=cost_val,
        sell_price=req.sell_price,
        min_quantity=req.min_quantity,
        location=req.location
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@app.delete("/api/products/{product_id}")
async def delete_product_endpoint(product_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    success, msg = db.delete_product(product_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@app.post("/api/stock-in")
async def stock_in_endpoint(req: StockInRequest, user: Dict[str, Any] = Depends(require_auth)):
    success, msg, updated = db.record_stock_in(
        product_id=req.product_id,
        quantity=req.quantity,
        unit_price=req.unit_price,
        reference=req.reference,
        user_id=user["user_id"]
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)

    # Auto sync to Google Sheets & Real-time Telegram Alert
    if updated:
        performer = user.get("full_name") or user.get("username") or "Web User"
        total = req.unit_price * req.quantity
        google_sheets_sync.sync_transaction(
            tx_type="IN",
            product_code=updated.get("code", ""),
            product_name=updated.get("name", ""),
            quantity=req.quantity,
            unit=updated.get("unit", "ឯកតា"),
            unit_price=req.unit_price,
            total_price=total,
            reference=req.reference,
            performed_by=performer,
            stock_remaining=updated.get("quantity", 0)
        )
        notifier.alert_stock_in(
            product=updated,
            quantity=req.quantity,
            cost_price=req.unit_price,
            total_price=total,
            new_stock=updated.get("quantity", 0),
            performed_by=f"🌐 {performer} (Web)",
            reference=req.reference
        )

    return {"success": True, "message": msg, "product": updated}


@app.post("/api/stock-out")
async def stock_out_endpoint(req: StockOutRequest, user: Dict[str, Any] = Depends(require_auth)):
    success, msg, updated = db.record_stock_out(
        product_id=req.product_id,
        quantity=req.quantity,
        unit_price=req.unit_price,
        reference=req.reference,
        user_id=user["user_id"]
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)

    # Auto sync to Google Sheets & Real-time Telegram Alert
    if updated:
        performer = user.get("full_name") or user.get("username") or "Web User"
        total = req.unit_price * req.quantity
        google_sheets_sync.sync_transaction(
            tx_type="OUT",
            product_code=updated.get("code", ""),
            product_name=updated.get("name", ""),
            quantity=req.quantity,
            unit=updated.get("unit", "ឯកតា"),
            unit_price=req.unit_price,
            total_price=total,
            reference=req.reference,
            performed_by=performer,
            stock_remaining=updated.get("quantity", 0)
        )
        notifier.alert_stock_out(
            product=updated,
            quantity=req.quantity,
            unit_price=req.unit_price,
            total_price=total,
            remaining_stock=updated.get("quantity", 0),
            performed_by=f"🌐 {performer} (Web)",
            reference=req.reference
        )

    return {"success": True, "message": msg, "product": updated}


@app.post("/api/stock-adjust")
async def stock_adjust_endpoint(req: StockAdjustRequest, user: Dict[str, Any] = Depends(require_auth)):
    success, msg, updated = db.adjust_product_quantity(
        product_id=req.product_id,
        new_quantity=req.new_quantity,
        reason=req.reason,
        user_id=user["user_id"]
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)

    if updated and updated.get("quantity", 0) <= updated.get("min_quantity", 5):
        notifier.alert_low_stock(
            product=updated,
            current_qty=updated.get("quantity", 0),
            min_qty=updated.get("min_quantity", 5)
        )

    return {"success": True, "message": msg, "product": updated}


@app.get("/api/transactions")
async def list_transactions(limit: int = 50, user: Dict[str, Any] = Depends(require_auth)):
    """ប្រវត្តិប្រតិបត្តិការចុងក្រោយ"""
    txs = db.get_recent_transactions(limit=limit)
    if user.get("role") != "admin":
        # Mask financial amounts if staff
        for t in txs:
            if t['type'] == 'IN':
                t['unit_price'] = 0.0
                t['total_price'] = 0.0
    return txs


# ==========================================
# Export & Report Endpoints (CSV & PDF)
# ==========================================

@app.get("/api/export/products/csv")
async def export_products_csv(user: Dict[str, Any] = Depends(require_auth)):
    """ទាញយកបញ្ជីទំនិញជា CSV (គាំទ្រ Microsoft Excel ខ្មែរ ១០០%)"""
    products = db.list_all_products(limit=5000)
    is_admin = (user.get("role") == "admin")
    csv_text = export_service.generate_products_csv(products, is_admin=is_admin)

    filename = f"SM_Products_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_text.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@app.get("/api/export/transactions/csv")
async def export_transactions_csv(user: Dict[str, Any] = Depends(require_auth)):
    """ទាញយកប្រវត្តិប្រតិបត្តិការជា CSV (គាំទ្រ Microsoft Excel ខ្មែរ ១០០%)"""
    txs = db.get_recent_transactions(limit=5000)
    is_admin = (user.get("role") == "admin")
    csv_text = export_service.generate_transactions_csv(txs, is_admin=is_admin)

    filename = f"SM_Transactions_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_text.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@app.get("/report/print", response_class=HTMLResponse)
async def print_report(request: Request, user: Dict[str, Any] = Depends(require_auth)):
    """ផ្ទាំងបោះពុម្ព ឬរក្សាទុកជា PDF នៃរបាយការណ៍ស្តុកផ្លូវការ"""
    products = db.list_all_products(limit=2000)
    low_stocks = db.get_low_stock_products()
    total_units = sum(p.get('quantity', 0) for p in products)
    total_asset_cost = sum((p.get('quantity') or 0) * (p.get('cost_price') or 0.0) for p in products)
    total_potential_revenue = sum((p.get('quantity') or 0) * (p.get('sell_price') or 0.0) for p in products)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    stats = {
        "total_products": len(products),
        "low_stock_count": len(low_stocks),
        "total_asset_cost": total_asset_cost,
        "total_potential_revenue": total_potential_revenue
    }

    template = jinja_env.get_template("print_report.html")
    html_content = template.render(
        user=user,
        products=products,
        stats=stats,
        total_units=total_units,
        report_date=now_str
    )
    return HTMLResponse(content=html_content)


class GoogleSheetUrlRequest(BaseModel):
    webhook_url: str


@app.get("/api/settings/google-sheets")
async def get_google_sheets_url(admin: Dict[str, Any] = Depends(require_admin)):
    """ពិនិត្យមើល Webhook URL របស់ Google Sheet"""
    url = google_sheets_sync.get_webhook_url()
    return {
        "webhook_url": url,
        "is_configured": bool(url)
    }


@app.post("/api/settings/google-sheets")
async def set_google_sheets_url(req: GoogleSheetUrlRequest, admin: Dict[str, Any] = Depends(require_admin)):
    """កំណត់ Google Sheets Webhook URL ថ្មី"""
    url = req.webhook_url.strip()
    google_sheets_sync.set_webhook_url(url)
    return {"success": True, "message": "បានកំណត់ Google Sheet Webhook URL រួចរាល់!"}


@app.post("/api/settings/telegram-alerts/test")
async def test_telegram_alert(admin: Dict[str, Any] = Depends(require_admin)):
    """ធ្វើតេស្តផ្ញើសារ Alert ទៅកាន់ Telegram"""
    admin_name = admin.get("full_name") or admin.get("username") or "Admin"
    notifier.send_system_alert(
        title="ការធ្វើតេស្តប្រព័ន្ធជូនដំណឹង (Telegram Alert Test)",
        message=f"👋 សួស្តី {admin_name}!\n\nប្រព័ន្ធជូនដំណឹង Real-time តាម Telegram ដំណើរការជោគជ័យ ១០០%! 🎉\nរាល់ពេលមានការនាំចេញ/លក់ ឬទំនិញជិតអស់ពីស្តុក ប្រព័ន្ធនឹងផ្ញើដំណឹងមកកាន់ទីនេះភ្លាមៗ។"
    )
    return {"success": True, "message": "បានផ្ញើសារតេស្តទៅកាន់ Telegram រួចរាល់!"}



if __name__ == "__main__":
    import uvicorn
    db.init_db()
    print("🚀 កំពុងដំណើរការ Web Dashboard លើ http://127.0.0.1:8000 ...")
    uvicorn.run("web_app:app", host="0.0.0.0", port=8000, reload=True)
