import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from agent import process_intent_with_gemini, _get_recommendations, generate_merchant_advice
from razorpay_utils import process_checkout
from razorpay_utils import process_checkout
from audit import log_action, get_audit_trail

app = FastAPI(title="AntiGravity Store API")

def get_current_catalog():
    try:
        with open("catalog.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Pydantic input models
class BuyRequest(BaseModel):
    intent: str
    budget: int = 600

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serves the single-page HTML frontend"""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>index.html not found!</h1>"

@app.get("/catalog")
def get_catalog():
    """Returns the structured product catalog"""
    return get_current_catalog()


@app.get("/merchant", response_class=HTMLResponse)
def serve_merchant():
    """Serves the merchant dashboard page"""
    try:
        with open("merchant.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>merchant.html not found!</h1>"


@app.post("/merchant/advice")
def merchant_advice():
    """Generate 3 AI merchant advices based on audit logs + catalog.
    Falls back to deterministic advice if Gemini is unavailable or fails.
    """
    catalog_data = get_current_catalog()
    logs = get_audit_trail()
    try:
        advice = generate_merchant_advice(logs, catalog_data)
        return advice
    except Exception:
        # safe fallback
        return {
            "advice": [
                {"type":"restock","product":"Top Seller","message":"Consider restocking high-demand items."},
                {"type":"campaign","product":"Slow-Mover","message":"Run a short discount for slow movers."},
                {"type":"bundle","product":"Work Bundle","message":"Bundle related products to increase AOV."}
            ]
        }

@app.post("/agent/buy")
def agent_buy(req: BuyRequest):
    """
    1. Sends user intent + catalog to Gemini
    2. Gemini picks a product
    3. Triggers checkout logic
    4. Logs everything to audit trail
    """
    if not req.intent or not req.intent.strip():
        log_action("User Input", "Empty request received", "declined")
        return {"action": "decline", "reason": "Please provide a shopping request first.", "chosen_product_ids": []}

    # Step 1: Log user intent
    log_action("User Input", f"User said: '{req.intent}' with budget ₹{req.budget}", "received")
    
    # Step 2: Call Gemini
    catalog_data = get_current_catalog()
    decision = process_intent_with_gemini(req.intent, req.budget, catalog_data)
    
    if decision.get("action") == "decline":
        reason = decision.get("reason", "Declined")
        log_action("AI Decision", reason, "declined")
        return decision
    
    chosen_product_ids = decision.get("chosen_product_ids", [])
    if not chosen_product_ids:
        log_action("AI Decision", "Failed to select any valid products", "error")
        return {"action": "decline", "reason": "Could not find valid products matching your request.", "chosen_product_ids": []}
        
    # Map IDs to actual product dicts
    chosen_products = [p for p in catalog_data if p["id"] in chosen_product_ids]
    
    if not chosen_products:
        log_action("AI Decision", "Selected products were invalid", "error")
        return {"action": "decline", "reason": "Selected products were not found in catalog.", "chosen_product_ids": []}
        
    product_names = ", ".join(p["name"] for p in chosen_products)
    log_action("AI Decision", decision.get("reason", f"Selected {product_names}"), "success")
    
    recommendations = _get_recommendations(req.intent, req.budget, chosen_product_ids, catalog_data)
    decision["recommendations"] = recommendations
    decision["revenue_uplift"] = recommendations.get("revenue_uplift", 0)
    decision["remaining_budget"] = recommendations.get("remaining_budget", req.budget)

    if recommendations.get("upsells"):
        log_action(
            "Upsell Strategy",
            f"Suggested {', '.join(item['name'] for item in recommendations['upsells'])} to increase basket size while staying under budget.",
            "success"
        )

    # Step 3: Checkout (enforces spend cap and creates Razorpay test order)
    checkout_result = process_checkout(chosen_products)
    
    if checkout_result.get("status") == "success":
        order_id = checkout_result.get("order_id")
        log_action(
            "Checkout", 
            f"Created order {order_id} for ₹{checkout_result.get('amount')}", 
            "success",
            order_id=order_id
        )
        decision["checkout"] = checkout_result
        decision["chosen_products"] = chosen_products
        decision["final_message"] = f"Great choice! I have placed an order for {product_names} at {checkout_result['amount']} rupees total."
        return decision
    else:
        # Checkout failed (e.g. strict spend cap)
        reason = checkout_result.get("reason", "Checkout failed")
        log_action("Checkout", reason, "declined")
        decision["action"] = "decline"
        decision["chosen_products"] = chosen_products
        decision["final_message"] = f"I'm sorry, I couldn't complete the purchase. {reason}"
        return decision

@app.get("/audit")
def fetch_audit_trail():
    """Returns the live audit trail"""
    return get_audit_trail()
