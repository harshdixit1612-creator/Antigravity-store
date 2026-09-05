import os
import json
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Setup Gemini API key
gemini_api_key = os.getenv("GEMINI_API_KEY", "")
client = None
if gemini_api_key:
    client = genai.Client(api_key=gemini_api_key)


def _safe_parse_json(raw_response) -> dict:
    """Parse Gemini JSON robustly across SDK response shapes."""
    if raw_response is None:
        return {"action": "decline", "reason": "AI returned no content.", "chosen_product_ids": []}

    text = None
    if hasattr(raw_response, "text") and raw_response.text:
        text = raw_response.text
    elif hasattr(raw_response, "output_text") and raw_response.output_text:
        text = raw_response.output_text
    elif isinstance(raw_response, str):
        text = raw_response

    if isinstance(text, str):
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```json\s*|^```\s*|\s*```$", "", text, flags=re.MULTILINE)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            return {
                "action": "decline",
                "reason": "AI returned malformed JSON. Please retry.",
                "chosen_product_ids": []
            }

    return {
        "action": "decline",
        "reason": "AI returned an unexpected response format.",
        "chosen_product_ids": []
    }


def _get_recommendations(intent: str, budget: int, chosen_product_ids: list, catalog: list) -> dict:
    """Build safe, budget-aware add-ons and bundles for merchant growth."""
    if not chosen_product_ids:
        return {
            "upsells": [],
            "bundle": None,
            "revenue_uplift": 0,
            "remaining_budget": budget
        }

    chosen_products = [p for p in catalog if p["id"] in chosen_product_ids]
    current_total = sum(p.get("price", 0) for p in chosen_products)
    remaining_budget = max(budget - current_total, 0)
    intent_lower = (intent or "").lower()

    suggestions = []

    # Strong merchant-growth rules: prefer cheap add-ons that fit the intent
    if any(keyword in intent_lower for keyword in ["gift", "birthday", "anniversary", "special"]):
        for product in catalog:
            product_id = product.get("id")
            if product_id in chosen_product_ids:
                continue
            product_price = product.get("price", 0)
            tags = " ".join(product.get("tags", [])).lower()
            name = product.get("name", "").lower()
            if product_price <= remaining_budget and (
                "gift" in tags or "birthday" in tags or "anniversary" in tags or "gift" in name or "card" in name
            ):
                suggestions.append({
                    "id": product_id,
                    "name": product.get("name"),
                    "price": product_price,
                    "reason": "Perfect gift add-on to increase basket value"
                })
                break

    if not suggestions and any(keyword in intent_lower for keyword in ["work", "office", "productivity", "desk", "keyboard", "mouse"]):
        for product in catalog:
            product_id = product.get("id")
            if product_id in chosen_product_ids:
                continue
            product_price = product.get("price", 0)
            category = product.get("category", "").lower()
            tags = " ".join(product.get("tags", [])).lower()
            if product_price <= remaining_budget and (category in ["work", "electronics"] or "desk" in tags or "work" in tags):
                suggestions.append({
                    "id": product_id,
                    "name": product.get("name"),
                    "price": product_price,
                    "reason": "Useful desk-side productivity upgrade"
                })
                break

    if not suggestions and any(keyword in intent_lower for keyword in ["fitness", "health", "wellness", "hydration", "water"]):
        for product in catalog:
            product_id = product.get("id")
            if product_id in chosen_product_ids:
                continue
            product_price = product.get("price", 0)
            tags = " ".join(product.get("tags", [])).lower()
            if product_price <= remaining_budget and ("health" in tags or "wellness" in tags or "hydration" in tags or "water" in product.get("name", "").lower()):
                suggestions.append({
                    "id": product_id,
                    "name": product.get("name"),
                    "price": product_price,
                    "reason": "Fits the wellness intent and boosts basket value"
                })
                break

    if not suggestions and any(keyword in intent_lower for keyword in ["audio", "music", "headphone", "earphone"]):
        for product in catalog:
            product_id = product.get("id")
            if product_id in chosen_product_ids:
                continue
            product_price = product.get("price", 0)
            tags = " ".join(product.get("tags", [])).lower()
            if product_price <= remaining_budget and ("travel" in tags or "tech" in tags or "gift" in tags):
                suggestions.append({
                    "id": product_id,
                    "name": product.get("name"),
                    "price": product_price,
                    "reason": "Compatible companion add-on for audio shoppers"
                })
                break

    # Fallback to useful low-cost add-ons if remaining budget allows it
    if not suggestions:
        for product in catalog:
            product_id = product.get("id")
            if product_id in chosen_product_ids:
                continue
            product_price = product.get("price", 0)
            if product_price <= remaining_budget and product_price > 0:
                suggestions.append({
                    "id": product_id,
                    "name": product.get("name"),
                    "price": product_price,
                    "reason": "Low-cost add-on to improve merchant conversion"
                })
                break

    bundle = None
    if len(suggestions) >= 1:
        bundle_total = sum(item["price"] for item in suggestions[:2])
        if bundle_total <= remaining_budget:
            bundle = {
                "name": "Campaign Bundle",
                "items": [item["id"] for item in suggestions[:2]],
                "total": bundle_total,
                "reason": "Promoted bundle to increase cart value while staying inside budget"
            }

    return {
        "upsells": suggestions[:2],
        "bundle": bundle,
        "revenue_uplift": sum(item["price"] for item in suggestions[:2]),
        "remaining_budget": remaining_budget
    }


def generate_merchant_advice(audit_logs: list, catalog: list) -> dict:
    """
    Generate exactly 3 pieces of merchant advice.
    Returns: {"advice": [ {type, product, message}, ... ] }
    Uses Gemini when available, otherwise falls back to a deterministic analyzer.
    """
    def fallback():
        counts = {p['id']: 0 for p in catalog}
        for entry in (audit_logs or []):
            act = (entry.get('action') or '').lower()
            det = (entry.get('detail') or '').lower()
            if 'ai decision' in act:
                for p in catalog:
                    if p['name'].lower() in det:
                        counts[p['id']] = counts.get(p['id'], 0) + 1

        top_seller = None
        if catalog:
            top_seller = max(catalog, key=lambda x: counts.get(x['id'], 0))

        slow = [p for p in catalog if counts.get(p['id'], 0) == 0]
        slow_product = slow[0] if slow else (catalog[-1] if catalog else None)

        work_prods = [p for p in catalog if p.get('category', '').lower() in ('work', 'electronics')]
        if len(work_prods) >= 2:
            bundle_name = f"{work_prods[0]['name']} + {work_prods[1]['name']}"
            bundle_msg = f"Bundle {work_prods[0]['name']} and {work_prods[1]['name']} at a promotional price to increase AOV."
        elif len(catalog) >= 2:
            bundle_name = f"{catalog[0]['name']} + {catalog[1]['name']}"
            bundle_msg = f"Bundle {catalog[0]['name']} and {catalog[1]['name']} to increase average order value."
        else:
            bundle_name = "Suggested Bundle"
            bundle_msg = "Create a bundle offer to improve cart size."

        advice = []
        if top_seller:
            advice.append({
                "type": "restock",
                "product": top_seller['name'],
                "message": f"Your top seller. Stock: {top_seller.get('stock',0)}. Consider restocking if below threshold."
            })
        else:
            advice.append({"type":"restock","product":"Top Seller","message":"No sales yet — monitor inventory."})

        if slow_product:
            advice.append({
                "type":"campaign",
                "product": slow_product['name'],
                "message": f"{slow_product['name']} has zero selections today. Consider a promotional discount or highlight in newsletter."
            })
        else:
            advice.append({"type":"campaign","product":"Slow-mover","message":"No slow movers identified."})

        advice.append({
            "type":"bundle",
            "product": bundle_name,
            "message": bundle_msg
        })
        return {"advice": advice}

    # If no client, return fallback
    if client is None:
        return fallback()

    # Build prompt and call Gemini
    try:
        recent = (audit_logs or [])[:40]
        audit_summary = "\n".join([f"[{e.get('timestamp')}] {e.get('action')}: {e.get('detail')} ({e.get('result')})" for e in recent])
        catalog_summary = ", ".join([f"{p['name']} (₹{p.get('price')}, stock:{p.get('stock')})" for p in catalog])
        system_instruction = (
            "You are a merchant intelligence assistant. Given recent audit logs and catalog, produce exactly 3 pieces of advice for the merchant: restock, campaign, and bundle. "
            "Return JSON with key 'advice' containing exactly three objects with fields 'type' ('restock'|'campaign'|'bundle'), 'product' and 'message'."
        )
        prompt = f"Audit logs:\n{audit_summary}\n\nCatalog:\n{catalog_summary}\n\nInstructions: Provide 3 concise actionable advice items (restock, campaign, bundle). Respond as JSON only."

        schema = {
            "type":"object",
            "properties":{
                "advice":{
                    "type":"array",
                    "items":{
                        "type":"object",
                        "properties":{
                            "type":{"type":"string"},
                            "product":{"type":"string"},
                            "message":{"type":"string"}
                        },
                        "required":["type","product","message"]
                    },
                    "minItems":3,
                    "maxItems":3
                }
            },
            "required":["advice"]
        }

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=schema
            )
        )
        parsed = _safe_parse_json(response)
        adv = parsed.get('advice')
        if isinstance(adv, list) and len(adv) == 3:
            return {"advice": adv}
        return fallback()
    except Exception:
        return fallback()


def _fallback_product_selection(intent: str, budget: int, catalog: list) -> dict:
    """A deterministic fallback for quota or API failures."""
    intent_lower = (intent or "").lower()
    scored = []

    for product in catalog:
        price = int(product.get("price", 0))
        if price <= 0 or price > budget:
            continue

        name = product.get("name", "").lower()
        tags = " ".join(product.get("tags", [])).lower()
        category = product.get("category", "").lower()
        score = 0

        if "gift" in intent_lower and ("gift" in tags or "birthday" in tags or "anniversary" in tags):
            score += 6
        if "work" in intent_lower and ("work" in tags or "desk" in tags or "productivity" in tags or category in ["work", "electronics"]):
            score += 6
        if "fitness" in intent_lower and ("fitness" in category or "health" in tags or "wellness" in tags or "hydration" in tags):
            score += 6
        if "headphone" in intent_lower or "audio" in intent_lower or "music" in intent_lower:
            if "audio" in category or "headphone" in name or "wireless" in name:
                score += 6
        if "keyboard" in intent_lower and "keyboard" in name:
            score += 7
        if "mouse" in intent_lower and "mouse" in name:
            score += 7
        if "water" in intent_lower and "water" in name:
            score += 7

        if "gift" in name or "gift" in tags:
            score += 2
        if category in ["work", "electronics", "audio", "fitness"]:
            score += 1

        scored.append((score, -price, product))

    if not scored:
        return {
            "action": "decline",
            "reason": "No product in the catalog matches your request within the current budget.",
            "chosen_product_ids": [],
            "used_fallback": True,
            "upsell_suggestions": [],
            "bundle_suggestion": None,
            "revenue_uplift": 0,
            "remaining_budget": budget
        }

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, _, best_product = scored[0]
    if best_score <= 0:
        return {
            "action": "decline",
            "reason": "No suitable product in the catalog matches your request within the budget.",
            "chosen_product_ids": [],
            "used_fallback": True,
            "upsell_suggestions": [],
            "bundle_suggestion": None,
            "revenue_uplift": 0,
            "remaining_budget": budget
        }

    decision = {
        "action": "proceed_to_checkout",
        "reason": f"Using the local recommendation engine, I selected {best_product['name']} for ₹{best_product['price']} because it best matches your intent and stays within budget.",
        "chosen_product_ids": [best_product["id"]],
        "used_fallback": True,
        "upsell_suggestions": [],
        "bundle_suggestion": None,
        "revenue_uplift": 0,
        "remaining_budget": budget - int(best_product['price'])
    }

    recs = _get_recommendations(intent, budget, decision["chosen_product_ids"], catalog)
    decision["upsell_suggestions"] = recs.get("upsells", [])
    decision["bundle_suggestion"] = recs.get("bundle")
    decision["revenue_uplift"] = recs.get("revenue_uplift", 0)
    decision["remaining_budget"] = recs.get("remaining_budget", decision["remaining_budget"])
    return decision


def process_intent_with_gemini(intent: str, budget: int, catalog: list) -> dict:
    """
    Sends the user's intent, budget, and the catalog to Gemini.
    Returns the structured decision as a dictionary.
    """
    if not intent or not str(intent).strip():
        return {
            "action": "decline",
            "reason": "No product request was provided in the query. Please specify what item you would like to buy.",
            "chosen_product_ids": []
        }

    if client is None:
        return _fallback_product_selection(intent, budget, catalog)

    system_instruction = (
        "You are an AI shopping agent. The user will provide a spoken command (which may be in Hindi, English, or Hinglish) "
        "indicating what they want to buy. You also receive a JSON catalog of products and a total budget constraint.\n"
        "Your task is to select the BEST matching product(s) from the catalog that fits the user's intent. "
        "If the user asks for multiple items, include all relevant product IDs in the list. "
        "The TOTAL sum of all chosen products MUST be strictly <= the budget.\n"
        "If NO product matches the intent OR the required items exceed the budget, explain why and set action to 'decline' and leave chosen_product_ids empty.\n"
        "You must return the reasoning in simple language so the user can hear it spoken back."
    )

    prompt = f"User Intent: {intent}\nBudget: {budget}\nCatalog: {json.dumps(catalog)}\n"

    schema = {
        "type": "object",
        "properties": {
            "chosen_product_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "A list of product IDs selected from the catalog to fulfill the user's intent. Empty list if none selected."
            },
            "reason": {
                "type": "string",
                "description": "Detailed explanation of why these products were chosen or why no product was chosen."
            },
            "action": {
                "type": "string",
                "description": "Either 'proceed_to_checkout' or 'decline'"
            }
        },
        "required": ["reason", "action", "chosen_product_ids"]
    }

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=schema
            )
        )
        decision = _safe_parse_json(response)

        decision.setdefault("chosen_product_ids", [])
        decision.setdefault("reason", "No reason provided by the AI.")
        decision.setdefault("action", "decline")

        if decision.get("action") not in ("proceed_to_checkout", "decline"):
            decision["action"] = "decline"

        if not isinstance(decision.get("chosen_product_ids", []), list):
            decision["chosen_product_ids"] = []

        # Get merchant growth recommendations
        recommendations = _get_recommendations(intent, budget, decision.get("chosen_product_ids", []), catalog)
        decision["upsell_suggestions"] = recommendations.get("upsells", [])
        decision["bundle_suggestion"] = recommendations.get("bundle", None)
        decision["revenue_uplift"] = recommendations.get("revenue_uplift", 0)
        decision["remaining_budget"] = recommendations.get("remaining_budget", budget)

        return decision
    except Exception as e:
        # Fallback to local product selection if AI processing fails
        return _fallback_product_selection(intent, budget, catalog)
