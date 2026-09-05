import os
import uuid
import razorpay
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
SPEND_CAP = int(os.getenv("SPEND_CAP", "600"))

# Initialize Razorpay Client (only if keys are provided)
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    client = None


def _generate_order_id() -> str:
    """Generate a unique local order identifier when Razorpay is unavailable."""
    return f"ord_{uuid.uuid4().hex[:12]}"


def process_checkout(products: list):
    """
    Takes a list of product dictionaries, enforces the spend cap on the total, and creates a Razorpay test order.
    Returns a result dict.
    """
    total_price = sum(p.get("price", 0) for p in products)
    product_names = ", ".join(p.get("name", "") for p in products)
    
    # 1. Enforce strict spend cap check
    if total_price > SPEND_CAP:
        return {
            "status": "declined",
            "reason": f"Budget ₹{SPEND_CAP} exceeded. Total cost is ₹{total_price} for {product_names}."
        }
    
    # 2. Try creating a Razorpay test order
    if not client:
        # Fallback if no keys provided, simulate success so the hackathon project still runs locally
        order_id = _generate_order_id()
        return {
            "status": "success",
            "order_id": order_id,
            "amount": total_price
        }
        
    try:
        data = {
            "amount": total_price * 100,  # Razorpay accepts amount in paise
            "currency": "INR",
            "receipt": f"receipt_{uuid.uuid4().hex[:8]}",
            "notes": {
                "products": product_names[:255] # Razorpay notes limit
            }
        }
        order = client.order.create(data=data)
        return {
            "status": "success",
            "order_id": order.get("id"),
            "amount": total_price
        }
    except Exception as e:
        return {
            "status": "error",
            "reason": str(e)
        }