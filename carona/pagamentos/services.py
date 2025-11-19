import requests
from decouple import config
import json

ABACATEPAY_KEY = config("ABACATEPAY_KEY")
ABACATEPAY_BASE = "https://api.abacatepay.com/v1"  # confirme na doc se for diferente


def criar_pix_qr(amount_cents: int, description: str, external_id: str, customer: dict | None = None, expires_in: int = 86400):
    url = f"{ABACATEPAY_BASE}/pixQrCode/create"
    headers = {
        "Authorization": f"Bearer {ABACATEPAY_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "amount": amount_cents,
        "expiresIn": expires_in,
        "description": description,
        "metadata": {"externalId": external_id}
    }
    if customer:
        payload["customer"] = customer

    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    try:
        body = resp.json()
    except Exception:
        body = {"status_code": resp.status_code, "text": resp.text}
    return {"status_code": resp.status_code, "body": body}
