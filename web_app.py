import os
import sys
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Response, Depends, status, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

import database as db
import auth
import export_service
import import_service
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
    expiry_date: Optional[str] = None
    batch_no: Optional[str] = None


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
    expiry_date: Optional[str] = None
    batch_no: Optional[str] = None


class StockOutRequest(BaseModel):
    product_id: int
    quantity: int
    unit_price: float = 0.0
    reference: str = "លក់ចេញតាម Web"
    batch_id: Optional[int] = None


class BatchUpdateRequest(BaseModel):
    expiry_date: Optional[str] = None
    quantity: Optional[int] = None
    batch_no: Optional[str] = None


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

    expiry = db.get_expiry_summary(days=30)

    return {
        "total_products": len(products),
        "low_stock_count": len(low_stocks),
        "total_asset_cost": round(total_cost_val, 2),
        "total_potential_revenue": round(total_sell_val, 2),
        "daily_summary": daily_summary,
        "expiry": expiry,
        "expired_count": expiry["expired"]["batches"],
        "expiring_soon_count": expiry["expiring_soon"]["batches"],
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

    db.attach_expiry_info(products)

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
    db.attach_expiry_info([prod])
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
        quantity=0,  # ស្តុកដំបូងត្រូវកត់ត្រាតាម record_stock_in ខាងក្រោម (ដើម្បីកុំឱ្យរាប់ពីរដង)
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
        ok_in, msg_in, _ = db.record_stock_in(
            product_id=prod_id,
            quantity=req.quantity,
            unit_price=req.cost_price,
            reference="ស្តុកដំបូងពេលបង្កើតតាម Web",
            user_id=user["user_id"],
            expiry_date=req.expiry_date,
            batch_no=req.batch_no
        )
        if not ok_in:
            return {"success": True, "message": f"បង្កើតទំនិញរួច ប៉ុន្តែស្តុកដំបូងមិនបានកត់ត្រា៖ {msg_in}", "id": prod_id}

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
        user_id=user["user_id"],
        expiry_date=req.expiry_date,
        batch_no=req.batch_no
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
        user_id=user["user_id"],
        batch_id=req.batch_id
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


def _mask_tx_for_staff(txs: List[Dict[str, Any]], user: Dict[str, Any]) -> List[Dict[str, Any]]:
    if user.get("role") != "admin":
        # Mask financial amounts if staff
        for t in txs:
            if t['type'] == 'IN':
                t['unit_price'] = 0.0
                t['total_price'] = 0.0
    return txs


@app.get("/api/transactions")
async def list_transactions(
    limit: int = 50,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    product_id: Optional[int] = None,
    user: Dict[str, Any] = Depends(require_auth)
):
    """ប្រវត្តិប្រតិបត្តិការ ជាមួយតម្រងកាលបរិច្ឆេទ (date_from/date_to = YYYY-MM-DD), ប្រភេទ (IN/OUT), ស្វែងរក"""
    tx_type = (type or "").upper() or None
    txs = db.get_transactions(
        limit=min(limit, 5000), date_from=date_from, date_to=date_to,
        tx_type=tx_type, search=search, product_id=product_id
    )
    return _mask_tx_for_staff(txs, user)


@app.get("/api/transactions/summary")
async def transactions_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    user: Dict[str, Any] = Depends(require_auth)
):
    """សរុបនាំចូល/នាំចេញ តាមតម្រង"""
    tx_type = (type or "").upper() or None
    summary = db.get_transactions_summary(date_from=date_from, date_to=date_to, tx_type=tx_type, search=search)
    if user.get("role") != "admin":
        summary["IN"]["amount"] = 0.0
    return summary


@app.get("/api/transactions/calendar")
async def transactions_calendar(
    year: Optional[int] = None,
    month: Optional[int] = None,
    user: Dict[str, Any] = Depends(require_auth)
):
    """ទិន្នន័យប្រតិទិន៖ ចំនួននាំចូល/នាំចេញ និងឡូតិ៍ផុតកំណត់ ក្នុងថ្ងៃនីមួយៗនៃខែ"""
    today = datetime.date.today()
    y = year or today.year
    m = month or today.month
    if not (1 <= m <= 12):
        raise HTTPException(status_code=400, detail="ខែមិនត្រឹមត្រូវ")
    return {
        "year": y,
        "month": m,
        "days": db.get_transaction_calendar(y, m),
        "expiry": db.get_expiry_calendar(y, m)
    }


# ==========================================
# Expiry / Batch Endpoints
# ==========================================

@app.get("/api/expiry")
async def list_expiry(
    days: int = 30,
    status: str = "alert",
    search: Optional[str] = None,
    user: Dict[str, Any] = Depends(require_auth)
):
    """បញ្ជីឡូតិ៍ផុតកំណត់ / ជិតផុតកំណត់ (status = expired | soon | ok | alert | all)"""
    days = max(1, min(days, 3650))
    return {
        "summary": db.get_expiry_summary(days=days),
        "batches": db.list_expiry_batches(days=days, status=status, search=search)
    }


@app.get("/api/products/{product_id}/batches")
async def product_batches(product_id: int, include_empty: bool = False, user: Dict[str, Any] = Depends(require_auth)):
    """បញ្ជីថ្ងៃផុតកំណត់ (ឡូតិ៍) ទាំងអស់របស់ទំនិញមួយ"""
    prod = db.get_product_by_id(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="រកមិនឃើញទំនិញនេះទេ")
    batches = db.get_product_batches(product_id, include_empty=include_empty)
    tracked = sum(b['quantity'] for b in batches)
    return {
        "product": {"id": prod['id'], "code": prod['code'], "name": prod['name'],
                    "unit": prod['unit'], "quantity": prod['quantity']},
        "batches": batches,
        "tracked_qty": tracked,
        "untracked_qty": max(0, prod['quantity'] - tracked)
    }


@app.put("/api/batches/{batch_id}")
async def update_batch_endpoint(batch_id: int, req: BatchUpdateRequest, user: Dict[str, Any] = Depends(require_auth)):
    """កែថ្ងៃផុតកំណត់ ឬចំនួនរបស់ឡូតិ៍ (ការកែចំនួន សម្រាប់ Admin ប៉ុណ្ណោះ)"""
    if req.quantity is not None and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="មានតែ Admin ទើបអាចកែចំនួនឡូតិ៍បាន!")
    ok, msg = db.update_batch(batch_id, expiry_date=req.expiry_date, quantity=req.quantity,
                              user_id=user["user_id"], batch_no=req.batch_no)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@app.delete("/api/batches/{batch_id}")
async def delete_batch_endpoint(batch_id: int, reason: str = "បោះចោលទំនិញផុតកំណត់", admin: Dict[str, Any] = Depends(require_admin)):
    """លុប/បោះចោលឡូតិ៍ (កាត់ស្តុកសរុបតាមចំនួនឡូតិ៍)"""
    ok, msg = db.delete_batch(batch_id, user_id=admin["user_id"], reason=reason)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


# ==========================================
# Bulk Import Endpoints (CSV / Excel)
# ==========================================

@app.get("/api/import/sample")
async def import_sample(format: str = "csv", user: Dict[str, Any] = Depends(require_auth)):
    """ទាញយកឯកសារគំរូសម្រាប់បញ្ចូលទិន្នន័យ (CSV ឬ XLSX)"""
    rows = db.generate_import_sample_rows()
    if format.lower() == "xlsx":
        try:
            content = import_service.rows_to_xlsx(rows)
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="SM_Import_Sample.xlsx"'}
        )
    csv_text = import_service.rows_to_csv(rows)
    return Response(
        content=csv_text.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="SM_Import_Sample.csv"'}
    )


@app.post("/api/import/products")
async def import_products(
    file: UploadFile = File(...),
    update_existing: bool = Form(True),
    dry_run: bool = Form(False),
    user: Dict[str, Any] = Depends(require_auth)
):
    """នាំចូលទិន្នន័យទំនិញពី CSV/XLSX (ទំនិញ ១ អាចមានច្រើនជួរ = ថ្ងៃផុតកំណត់ច្រើន)"""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="ឯកសារទទេ!")
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="ឯកសារធំពេក (អតិបរមា 10MB)")
    try:
        headers, data_rows = import_service.parse_upload(file.filename or "", raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    mapping = db.map_import_headers(headers)
    if 'code' not in mapping.values():
        raise HTTPException(
            status_code=400,
            detail=f"រកមិនឃើញ column 'code' ក្នុងឯកសារ! Header ដែលបានអាន៖ {', '.join(str(h) for h in headers)}"
        )
    rows = [{mapping[i]: v for i, v in enumerate(r) if i in mapping} for r in data_rows]
    rows = [r for r in rows if any(str(v).strip() for v in r.values() if v is not None)]
    ordered_cols = [f for f, _ in db.IMPORT_COLUMNS if f in mapping.values()]

    if dry_run:
        preview = import_service.preview_rows(rows)
        return {"success": True, "dry_run": True, "columns": ordered_cols,
                "total": len(rows), "preview": preview}

    performer = user.get("full_name") or user.get("username") or "Web User"
    summary = db.import_products_rows(rows, user_id=user["user_id"],
                                      update_existing=update_existing,
                                      reference=f"Import ដោយ {performer}")
    summary["columns"] = ordered_cols
    return {"success": True, "dry_run": False, **summary}


# ==========================================
# Export & Report Endpoints (CSV & PDF)
# ==========================================

@app.get("/api/export/products/csv")
async def export_products_csv(user: Dict[str, Any] = Depends(require_auth)):
    """ទាញយកបញ្ជីទំនិញជា CSV (គាំទ្រ Microsoft Excel ខ្មែរ ១០០%)"""
    products = db.attach_expiry_info(db.list_all_products(limit=5000))
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
async def export_transactions_csv(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    user: Dict[str, Any] = Depends(require_auth)
):
    """ទាញយកប្រវត្តិប្រតិបត្តិការជា CSV តាមតម្រង (គាំទ្រ Microsoft Excel ខ្មែរ ១០០%)"""
    tx_type = (type or "").upper() or None
    txs = db.get_transactions(limit=50000, date_from=date_from, date_to=date_to, tx_type=tx_type, search=search)
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
    products = db.attach_expiry_info(db.list_all_products(limit=2000))
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
