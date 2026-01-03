import requests
import json
import hmac
import hashlib

# URL do webhook (ngrok)
WEBHOOK_URL = "https://thresa-retroflex-ambilaterally.ngrok-free.dev/pagamentos/webhook/abacatepay/"

# Secret configurado no Django
WEBHOOK_SECRET = b"9fda75c9fd810e6dc50f81a398efc0a645b093e5881f528976ddabef38792312"

# Evento realista de pagamento aprovado
evento = {
    "event": "payment.paid",
    "data": {
        "id": "bill_3FQPzyN0yak30Chh0jQAHZkx",  # Use o abacate_id real do Payment que você criou
        "external_id": "carteira-2-45-fe1674",
        "amount": 5000,
        "billing_url": "https://abacatepay.com/pay/bill_3FQPzyN0yak30Chh0jQAHZkx"
    }
}

payload = json.dumps(evento).encode()  # transforma em bytes
signature = hmac.new(WEBHOOK_SECRET, payload, hashlib.sha256).hexdigest()

headers = {
    "Content-Type": "application/json",
    "X-AbacatePay-Signature": signature
}

response = requests.post(WEBHOOK_URL, headers=headers, data=payload)

print(f"Evento enviado: {evento['event']}")
print(f"Status HTTP: {response.status_code}")
print(f"Resposta: {response.text}")
