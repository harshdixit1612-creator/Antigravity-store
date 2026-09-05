# 🚀 AntiGravity Store
### AI-Powered Voice Commerce Agent — Razorpay Buildathon 2026, Track 01

> *AI agents can talk. Now they can transact.*

AntiGravity Store is a fully transactable merchant built for AI buyers. A user speaks or types a request in Hindi, English, or Hinglish — the AI understands intent, selects the best product, enforces a spend cap, and creates a real Razorpay order. Every action is explainable, bounded, and logged.

---

## 🎯 What Problem Does It Solve?

Today's AI agents cannot shop autonomously. They can recommend products but cannot complete a transaction end-to-end. AntiGravity Store fixes this by building a merchant that any AI buyer can:

- **Discover** — via a structured, agent-readable product catalog
- **Understand** — AI reads intent in any language and selects the best match
- **Transact** — real Razorpay test orders created autonomously
- **Trust** — every decision explained, every rupee bounded, everything audited

---

## ✨ Features

### Customer Side
- 🎙️ **Voice Input** — speak in Hindi, English, or Hinglish
- ⌨️ **Text Input** — type if you prefer
- 🤖 **AI Buyer Agent** — Gemini reads catalog and picks the best product with a reason
- 💳 **Razorpay Checkout** — real test orders created automatically
- 🚫 **Graceful Decline** — budget exceeded? Clear explanation, no crash
- 🎁 **Upsell Suggestions** — AI recommends add-ons to increase basket value
- 🔊 **Voice Output** — AI speaks the result back to you

### Merchant Side
- 📊 **Real-Time Dashboard** — live sales metrics, updates every 3 seconds
- 📦 **Product Performance Table** — times selected, revenue generated, stock alerts
- 🧠 **AI Merchant Advisor** — one click gets restock alerts, campaign ideas, bundle suggestions
- 🖥️ **Live Audit Terminal** — every AI action visible with timestamp and reason

---

## 🏗️ Architecture

```
User speaks/types intent
        ↓
   FastAPI Backend
        ↓
   Gemini AI Agent  ←→  Product Catalog (catalog.json)
        ↓
  Spend Cap Check (razorpay_utils.py)
        ↓                    ↓
  Razorpay Order         Graceful Decline
        ↓
   Audit Logger (audit.py)
        ↓
  Merchant Dashboard (merchant.html)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI + Uvicorn |
| AI Brain | Google Gemini 1.5 Flash |
| Payments | Razorpay Test Mode API |
| Voice Input | Web Speech API (browser, free) |
| Voice Output | Web Speech Synthesis API (browser, free) |
| Frontend | Vanilla HTML + CSS + JS (zero build steps) |
| Config | python-dotenv |

---

## 📁 Project Structure

```
antigravity-store/
├── main.py              # FastAPI app — all routes
├── agent.py             # Gemini AI buyer agent + fallback engine
├── razorpay_utils.py    # Razorpay order creation + spend cap enforcement
├── audit.py             # In-memory audit trail logger
├── catalog.json         # 10 agent-readable products
├── index.html           # Customer voice/text shopping UI
├── merchant.html        # Merchant intelligence dashboard
├── requirements.txt     # Python dependencies
└── .env                 # API keys (never commit this)
```

---

## ⚡ Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/antigravity-store.git
cd antigravity-store
```

### 2. Create virtual environment
```bash
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1

# Mac/Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key
RAZORPAY_KEY_ID=your_razorpay_test_key_id
RAZORPAY_KEY_SECRET=your_razorpay_test_key_secret
SPEND_CAP=600
```

### 5. Run the server
```bash
uvicorn main:app --reload
```

### 6. Open the app
| Page | URL |
|---|---|
| Customer Store | http://localhost:8000 |
| Merchant Dashboard | http://localhost:8000/merchant |
| API Docs | http://localhost:8000/docs |
| Audit Trail | http://localhost:8000/audit |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Customer shopping UI |
| GET | `/catalog` | Agent-readable product catalog |
| POST | `/agent/buy` | AI processes intent → selects product → checkout |
| GET | `/audit` | Full audit trail (newest first) |
| GET | `/merchant` | Merchant intelligence dashboard |
| POST | `/merchant/advice` | AI generates 3 business recommendations |

### Example — POST /agent/buy
```json
// Request
{
  "intent": "mujhe birthday gift chahiye 500 mein",
  "budget": 600
}

// Response
{
  "action": "proceed_to_checkout",
  "reason": "Selected Wireless Headphones ₹499 — fits birthday gift intent and within budget",
  "chosen_product_ids": ["p001"],
  "checkout": {
    "status": "success",
    "order_id": "order_Jxk92mNabcd",
    "amount": 499
  },
  "upsell_suggestions": [...],
  "bundle_suggestion": {...},
  "revenue_uplift": 99
}
```

---

## 🧪 Demo Scenarios

**Success flow:**
```
Input:  "wireless headphones under 600"
Output: Headphones selected, Razorpay order created, upsell suggested
```

**Graceful decline:**
```
Input:  "buy the mechanical keyboard"
Output: "Budget ₹600 exceeded. Keyboard costs ₹899." — no crash
```

**Hinglish support:**
```
Input:  "mujhe kuch relaxing chahiye 400 mein"
Output: Best match selected within budget
```

**Work setup:**
```
Input:  "work desk setup under 600"
Output: Bundle selected, productivity upsell suggested
```

---

## 🔒 Key Design Decisions

**Why spend cap server-side?**
The AI cannot override financial limits. Enforcement happens in `razorpay_utils.py` — before Razorpay is ever called. This is the foundation of trustworthy agentic commerce.

**Why explainable decisions?**
Every AI selection includes a `reason` field. Judges, merchants, and users can always see *why* a product was chosen. No black box.

**Why a fallback engine?**
If Gemini quota is hit, `_fallback_product_selection` activates automatically with deterministic scoring. The demo never breaks.

**Why in-memory audit logs?**
Hackathon scope. Production version would use SQLite or PostgreSQL for persistent storage across sessions.

---

## 📊 Test Results

| Test | Status |
|---|---|
| Basic text order | ✅ PASS |
| Hindi/Hinglish input | ✅ PASS |
| Voice input | ✅ PASS |
| Budget exceed decline | ✅ PASS |
| Upsell suggestions | ✅ PASS |
| Merchant real-time metrics | ✅ PASS |
| Product performance table | ✅ PASS |
| AI advice generation | ✅ PASS |
| Audit terminal | ✅ PASS |
| Zero state (no orders) | ✅ PASS |

---

## 🚀 Roadmap

- [ ] Persistent database (SQLite → PostgreSQL)
- [ ] Multi-merchant onboarding
- [ ] Merchant catalog management UI
- [ ] Production Razorpay integration
- [ ] Deploy to Railway / Render
- [ ] Historical analytics and weekly reports

---

## 🙏 Built For

**Razorpay AI Buildathon 2026 — Track 01: AI Growth & Agentic Commerce**

> *"Grow the merchant's revenue, and make them sellable to AI buyers."*

Every requirement from the track is addressed:
- ✅ Conversational in-app checkout
- ✅ Agent-readable catalog
- ✅ Upsell & cross-sell agent
- ✅ Every money action explainable, bounded and gated
- ✅ Audit trail visible
- ✅ One failure handled gracefully

---

## 👨‍💻 Author

**Harsh** — Built in 48 hours for Razorpay Buildathon 2026
