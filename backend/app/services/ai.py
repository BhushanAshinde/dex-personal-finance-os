import json
import re
from ..config import settings

SYSTEM = """You are Dex, a personal finance assistant. Convert user messages into safe structured intents. Supported intent: create_expense, list_spending, unknown. For create_expense return JSON with amount, category, merchant, note. Never invent an amount. If information is missing, ask a concise clarification question. Currency is INR unless user explicitly says otherwise."""

def parse_message(message: str):
    api_key = (settings.openai_api_key or "").strip()
    if not api_key or api_key.startswith("your_"):
        return parse_expense_fallback(message)
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    r = client.chat.completions.create(model="gpt-4o-mini", response_format={"type":"json_object"}, messages=[{"role":"system","content":SYSTEM},{"role":"user","content":message}])
    return json.loads(r.choices[0].message.content)


def parse_expense_fallback(message: str):
    """Handle common expense capture without making an external AI call."""
    normalized = message.lower().strip()
    amount_matches = list(re.finditer(r"(?:₹|rs\.?\s*)?([0-9][0-9,]*(?:\.\d{1,2})?)", normalized))
    if not amount_matches:
        return {"intent": "unknown", "reply": "Tell me an amount, for example: 'Spent 450 on petrol'."}

    stop_words = {"spent", "paid", "for", "on", "at", "using", "today", "yesterday", "rs", "inr"}
    items = []
    for match in amount_matches:
        amount = match.group(1).replace(",", "")
        remainder = normalized[match.end():]
        next_amount = re.search(r"(?:₹|rs\.?\s*)?[0-9]", remainder)
        description = remainder[:next_amount.start()] if next_amount else remainder
        words = [word for word in re.split(r"[^a-z0-9]+", description) if word and word not in stop_words]
        if not words:
            words = ["Other"]
        label = " ".join(words[:5]).strip().title()
        category = "Fuel" if any(word in words for word in ("petrol", "fuel", "diesel")) else "Food" if any(word in words for word in ("food", "dinner", "lunch", "breakfast", "coffee", "restaurant")) else "Groceries" if any(word in words for word in ("grocery", "groceries")) else "Other"
        items.append({"amount": amount, "category": category, "merchant": label})

    return {"intent": "create_expenses", "items": items}
