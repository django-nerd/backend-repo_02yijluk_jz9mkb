import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from random import randint, random

from database import db, create_document, get_documents
from schemas import User, Product, Order, OrderItem, Payment, Log, Withdrawal, Setting

app = FastAPI(title="Digital Services Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "DSP API running"}

@app.get("/schema")
def read_schema():
    return {
        "collections": [
            "user", "product", "order", "payment", "withdrawal", "log", "setting"
        ]
    }

# ---------- Auth (lightweight demo) ----------
class AuthPayload(BaseModel):
    email: str
    password: str

ROLE_PREFIX = {
    'owner': 'owner',
    'high': 'high_admin',
    'admin': 'admin',
    'investor': 'investor',
    'engineer': 'engineer',
    'reseller': 'reseller',
}

@app.post("/api/register")
def register(payload: AuthPayload):
    try:
        new_user = User(name=payload.email.split("@")[0], email=payload.email, password=payload.password, role='buyer')
        user_id = create_document('user', new_user)
        return {"ok": True, "id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/login")
def login(payload: AuthPayload):
    role = 'buyer'
    email = payload.email.lower()
    for key, r in ROLE_PREFIX.items():
        if email.startswith(key):
            role = r
            break
    return {"ok": True, "role": role, "token": "demo-token"}

@app.get("/api/me")
def me(email: Optional[str] = Query(None)):
    # Demo role resolution from email prefix
    role = 'buyer'
    if email:
        em = email.lower()
        for key, r in ROLE_PREFIX.items():
            if em.startswith(key):
                role = r
                break
    return {"ok": True, "role": role}

# ---------- Settings (Auto Payment) ----------

def get_setting(key: str, default: str = "false") -> str:
    try:
        docs = get_documents('setting', {"key": key}, limit=1)
        if docs:
            return docs[0].get('value', default)
    except Exception:
        pass
    return default

def set_setting(key: str, value: str) -> None:
    if db is None:
        return
    existing = list(db['setting'].find({"key": key}).limit(1))
    payload = {"key": key, "value": value, "updated_at": datetime.utcnow()}
    if existing:
        db['setting'].update_one({"_id": existing[0]['_id']}, {"$set": payload})
    else:
        db['setting'].insert_one({**payload, "created_at": datetime.utcnow()})

@app.get("/api/settings/auto-payment")
def get_auto_payment():
    value = get_setting('auto_payment_enabled', 'true')
    return {"ok": True, "enabled": value.lower() == 'true'}

class TogglePayload(BaseModel):
    enabled: bool

@app.post("/api/settings/auto-payment")
def toggle_auto_payment(body: TogglePayload):
    set_setting('auto_payment_enabled', 'true' if body.enabled else 'false')
    return {"ok": True, "enabled": body.enabled}

# ---------- Products ----------

def seed_products_if_empty():
    try:
        existing = get_documents('product', {}, limit=1)
        if existing:
            return
    except Exception:
        return
    presets = [
        Product(sku="VPS-1", title="VPS Nano", description="1 vCPU • 1GB RAM • 20GB SSD", price=3.99, category='vps', stock=200),
        Product(sku="VPS-2", title="VPS Micro", description="2 vCPU • 2GB RAM • 40GB SSD", price=6.99, category='vps', stock=150),
        Product(sku="DM-1", title=".com Domain", description="1 year registration", price=9.49, category='domain', stock=999),
        Product(sku="PNL-1", title="Game Panel", description="Pterodactyl slot", price=2.49, category='panel', stock=500),
    ]
    for p in presets:
        try:
            create_document('product', p)
        except Exception:
            pass

@app.get("/api/products")
def list_products():
    seed_products_if_empty()
    try:
        docs = get_documents('product', {})
        for d in docs:
            if '_id' in d:
                d['_id'] = str(d['_id'])
        return {"ok": True, "items": docs}
    except Exception:
        return {"ok": True, "items": [
            {"sku":"VPS-1","title":"VPS Nano","description":"1 vCPU • 1GB RAM • 20GB SSD","price":3.99,"category":"vps","stock":200},
            {"sku":"VPS-2","title":"VPS Micro","description":"2 vCPU • 2GB RAM • 40GB SSD","price":6.99,"category":"vps","stock":150},
            {"sku":"DM-1","title":".com Domain","description":"1 year registration","price":9.49,"category":"domain","stock":999},
            {"sku":"PNL-1","title":"Game Panel","description":"Pterodactyl slot","price":2.49,"category":"panel","stock":500},
        ]}

# ---------- Dashboard data ----------
@app.get("/api/metrics")
def metrics():
    return {
        "ok": True,
        "cards": [
            {"label":"Total Penjualan","value": randint(1200, 4800), "trend": round((random()-0.5)*10,2)},
            {"label":"MRR / Revenue","value": round(random()*15000,2), "trend": round((random()-0.5)*10,2)},
            {"label":"Saldo Tersedia","value": round(random()*5000,2), "trend": round((random()-0.5)*10,2)},
            {"label":"Ticket Open","value": randint(2, 37), "trend": round((random()-0.5)*10,2)},
            {"label":"Auto Payment","value": "On" if get_setting('auto_payment_enabled','true')=='true' else "Off", "trend": 0},
            {"label":"Konversi","value": f"{round(random()*5+1,2)}%", "trend": round((random()-0.5)*10,2)},
        ]
    }

@app.get("/api/sales")
def sales():
    base = datetime.utcnow()
    series = []
    for i in range(30):
        day = base - timedelta(days=29-i)
        open_p = round(50 + random()*50, 2)
        close_p = round(open_p + (random()-0.5)*10, 2)
        high = max(open_p, close_p) + round(random()*5,2)
        low = min(open_p, close_p) - round(random()*5,2)
        series.append({
            "date": day.strftime('%Y-%m-%d'),
            "gross": round(random()*2000+500,2),
            "net": round(random()*1500+300,2),
            "units": randint(5, 80),
            "open": open_p,
            "close": close_p,
            "high": high,
            "low": low
        })
    return {"ok": True, "series": series}

# ---------- Orders / Checkout ----------
class CartPayload(BaseModel):
    items: List[OrderItem]
    discount: float = 0
    tax_rate: float = 0.1

@app.post("/api/orders/preview")
def order_preview(payload: CartPayload):
    subtotal = sum(i.qty * i.unit_price for i in payload.items)
    tax = (subtotal - payload.discount) * payload.tax_rate
    total = max(subtotal - payload.discount + tax, 0)
    return {"ok": True, "subtotal": round(subtotal,2), "discount": payload.discount, "tax": round(tax,2), "total": round(total,2)}

class CheckoutPayload(CartPayload):
    user_email: Optional[str] = None
    payment_method: Optional[str] = None

@app.post("/api/checkout")
def checkout(payload: CheckoutPayload):
    summary = order_preview(payload)
    try:
        order = Order(
            user_email=payload.user_email or "guest@example.com",
            items=payload.items,
            subtotal=summary["subtotal"],
            discount=summary["discount"],
            tax=summary["tax"],
            total=summary["total"],
            status='pending',
            payment_method=payload.payment_method or 'manual'
        )
        order_id = create_document('order', order)
        # log sale
        try:
            create_document('log', Log(
                timestamp=datetime.utcnow(),
                category='sale',
                actor=order.user_email,
                description=f"{order.user_email} membeli layanan total ${order.total}",
                related_id=str(order_id)
            ))
        except Exception:
            pass
        return {"ok": True, "order_id": order_id, "client_secret": f"demo_{order_id}"}
    except Exception:
        return {"ok": True, "order_id": "demo123", "client_secret": "demo_demo123"}

class PaymentPayload(BaseModel):
    order_id: str
    method: str

@app.post("/api/payment")
def pay(payload: PaymentPayload):
    # In real impl, verify and update DB
    try:
        create_document('log', Log(
            timestamp=datetime.utcnow(),
            category='payment',
            actor='system',
            description=f"Payment captured for order {payload.order_id} via {payload.method}",
            related_id=payload.order_id
        ))
    except Exception:
        pass
    return {"ok": True, "status": "success", "order_id": payload.order_id}

# ---------- Withdrawals ----------
class WithdrawRequest(BaseModel):
    actor_email: str
    amount: float
    role: str

@app.post('/api/withdrawals')
def create_withdrawal(req: WithdrawRequest):
    role = req.role
    now = datetime.utcnow()
    status = 'requested'
    note = None
    scheduled_date = None

    if role == 'reseller':
        # T+5 days schedule
        scheduled_date = now + timedelta(days=5)
        status = 'scheduled'
        note = 'Reseller T+5 payout scheduled'
    elif role == 'high_admin':
        status = 'paid'
        note = 'High admin instant payout'
    else:
        status = 'approved'
        note = 'Approved by policy'

    try:
        wid = create_document('withdrawal', Withdrawal(
            actor_email=req.actor_email,
            amount=req.amount,
            role=role,
            status=status,
            note=note,
            scheduled_date=scheduled_date
        ))
        # log entry
        try:
            desc = f"{req.actor_email} request withdraw ${req.amount:0.2f} -> {status}"
            create_document('log', Log(
                timestamp=now,
                category='withdrawal',
                actor=req.actor_email,
                description=desc,
                related_id=str(wid)
            ))
        except Exception:
            pass
        return {"ok": True, "id": wid, "status": status, "scheduled_date": scheduled_date}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------- Logs ----------
@app.get("/api/logs")
def logs():
    now = datetime.utcnow()
    sample_names = ["Muhammad Ilham", "Aulia", "Rizky", "Siti", "Budi", "Andi"]
    products = [
        ("VPS Nano", "1 vCPU • 1GB RAM • 20GB SSD", 3.99),
        ("VPS Micro", "2 vCPU • 2GB RAM • 40GB SSD", 6.99),
        ("Game Panel", "Pterodactyl slot", 2.49),
        ("Domain .com", "Registrasi 1 tahun", 9.49)
    ]
    rows = []
    for i in range(25):
        name, (pname, spec, price) = sample_names[i % len(sample_names)], products[i % len(products)]
        desc = f"{name} menjual {pname} ({spec}) seharga ${price:.2f}"
        rows.append({
            "timestamp": (now - timedelta(minutes=i*7)).isoformat() + 'Z',
            "category": ['sale','payment','auth','withdrawal','system'][i % 5],
            "actor": ["system","admin@site.com","reseller@site.com","user@site.com"][i % 4],
            "description": desc,
            "related_id": f"RID{i:04d}"
        })
    return {"ok": True, "items": rows}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
