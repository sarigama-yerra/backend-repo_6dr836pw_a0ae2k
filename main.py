import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Service, Quote, QuoteItem

app = FastAPI(title="Plumbing Services & Estimator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utilities

def to_str_id(doc):
    if not doc:
        return doc
    doc["id"] = str(doc.get("_id"))
    doc.pop("_id", None)
    return doc

# Seed default services if collection empty
@app.on_event("startup")
async def seed_services():
    try:
        if db is None:
            return
        count = db["service"].count_documents({})
        if count == 0:
            defaults = [
                {"name": "Leak Repair", "description": "Fix minor to major leaks", "unit": "flat", "rate": 120, "category": "Repair"},
                {"name": "Pipe Installation", "description": "Install new copper/PVC pipes", "unit": "sqm", "rate": 35, "category": "Installation"},
                {"name": "Fixture Installation", "description": "Sinks, toilets, showers, faucets", "unit": "fixture", "rate": 85, "category": "Installation"},
                {"name": "Drain Cleaning", "description": "Clear clogged drains", "unit": "flat", "rate": 95, "category": "Maintenance"},
                {"name": "Water Heater Setup", "description": "Install standard water heater", "unit": "flat", "rate": 650, "category": "Installation"}
            ]
            for d in defaults:
                db["service"].insert_one({**d})
    except Exception:
        pass

# Models for requests
class QuoteRequest(BaseModel):
    project_name: str
    area_sqm: float = 0
    fixtures: int = 0
    service_ids: List[str] = []
    location_factor: float = 1.0
    overhead_pct: float = 0.1
    tax_pct: float = 0.08

# Routes
@app.get("/")
def root():
    return {"message": "Plumbing API running"}

@app.get("/services")
def list_services():
    try:
        docs = list(db["service"].find({})) if db else []
        return [to_str_id(doc) for doc in docs]
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/services")
def create_service(service: Service):
    try:
        sid = create_document("service", service)
        return {"id": sid}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/estimate")
def estimate(req: QuoteRequest):
    try:
        # fetch selected services
        sel = []
        if db and req.service_ids:
            ids = [ObjectId(s) for s in req.service_ids if ObjectId.is_valid(s)]
            if ids:
                sel = list(db["service"].find({"_id": {"$in": ids}}))
        # compute items
        items: List[QuoteItem] = []
        subtotal = 0.0
        for s in sel:
            unit = s.get("unit")
            rate = float(s.get("rate", 0))
            qty = 1.0
            if unit == "sqm":
                qty = max(0.0, req.area_sqm)
            elif unit == "fixture":
                qty = max(0.0, float(req.fixtures))
            cost = qty * rate * req.location_factor
            subtotal += cost
            items.append(QuoteItem(
                service_id=str(s.get("_id")),
                service_name=s.get("name", "Service"),
                unit=unit,
                quantity=qty,
                rate=rate,
                cost=round(cost, 2),
            ))
        overhead = subtotal * req.overhead_pct
        tax = (subtotal + overhead) * req.tax_pct
        total = subtotal + overhead + tax
        quote = Quote(
            project_name=req.project_name,
            area_sqm=req.area_sqm,
            fixtures=req.fixtures,
            selected_service_ids=req.service_ids,
            location_factor=req.location_factor,
            items=items,
            subtotal=round(subtotal, 2),
            overhead=round(overhead, 2),
            tax=round(tax, 2),
            total=round(total, 2)
        )
        qid = create_document("quote", quote)
        return {"id": qid, **quote.model_dump()}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/quotes")
def list_quotes(limit: Optional[int] = 20):
    try:
        docs = get_documents("quote", {}, limit)
        return [to_str_id(d) for d in docs]
    except Exception as e:
        raise HTTPException(500, str(e))

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
