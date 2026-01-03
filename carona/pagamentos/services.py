# pagamentos/services.py
"""
Funções utilitárias para criar/consultar cobranças PIX / hosted payments via AbacatePay.

Objetivos:
- Payload compatível com /v1/billing/create e /v1/pix/qr-code.
- Extração padronizada de billing_url (data.url / data.billing_url / data.payment_url / data.checkout_url).
- Suporte a brCode / brCodeBase64 para QR PIX.
- Retries com backoff exponencial em falhas temporárias.
- Retorno padronizado: {"ok", "status_code", "body", "data", "error"}.
"""
from __future__ import annotations
import requests
import logging
import time
import json
from typing import Optional, Dict, Any
from datetime import datetime
from django.conf import settings
from pagamentos.models import Payment, Carteira

import os
import uuid



BASE_URL = os.environ.get("ABACATEPAY_BASE_URL", "https://api.abacatepay.com/v1")
API_KEY = os.environ.get("ABACATEPAY_API_KEY")
TIMEOUT = int(os.environ.get("ABACATEPAY_TIMEOUT", 30))


from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Defaults (podem ser sobrescritos nas settings)
DEFAULT_TIMEOUT = getattr(settings, "ABACATEPAY_TIMEOUT", 30)
DEFAULT_RETRIES = getattr(settings, "ABACATEPAY_RETRIES", 2)
DEFAULT_RETURN_URL = getattr(settings, "ABACATEPAY_RETURN_URL", None)
DEFAULT_COMPLETION_URL = getattr(settings, "ABACATEPAY_COMPLETION_URL", None)
PRICE_AS_DECIMAL = getattr(settings, "ABACATEPAY_PRICE_AS_DECIMAL", False)


def _build_headers() -> Dict[str, str]:
    api_key = getattr(settings, "ABACATEPAY_API_KEY", None)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _full_url(path: str) -> str:
    base = getattr(settings, "ABACATEPAY_BASE_URL", "").rstrip("/")
    path_norm = path.lstrip("/")
    if base.endswith("/v1") and path_norm.startswith("v1/"):
        path_norm = path_norm[len("v1/"):]
    return f"{base}/{path_norm}" if base else path_norm


def _post_with_retries(
    url: str, payload: Dict[str, Any], headers: Dict[str, str], retries: int = DEFAULT_RETRIES
) -> Dict[str, Any]:
    attempt = 0
    last_exc = None
    while attempt <= retries:
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT)
            status = resp.status_code
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text}
            return {"status": status, "body": body}
        except requests.RequestException as exc:
            last_exc = exc
            backoff = min(2 ** attempt * 0.2, 5.0)
            logger.warning(
                "RequestException para %s (attempt %s/%s): %s — sleeping %.2fs",
                url, attempt, retries, str(exc), backoff,
            )
            time.sleep(backoff)
            attempt += 1
    err_msg = str(last_exc) if last_exc else "unknown error"
    logger.error("Todas tentativas falharam para %s: %s", url, err_msg)
    return {"status": 0, "body": {"error": err_msg}}


def _parse_expires_at(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(int(value))
        except Exception:
            return None
    if isinstance(value, str):
        iso = value.strip()
        if iso.endswith("Z"):
            iso = iso[:-1]
        try:
            return datetime.fromisoformat(iso)
        except Exception:
            try:
                return datetime.strptime(iso.split(".")[0], "%Y-%m-%dT%H:%M:%S")
            except Exception:
                return None
    return None


def _normalize_body(resp_body: Any) -> Dict[str, Any]:
    if isinstance(resp_body, dict):
        body = resp_body
    else:
        try:
            body = json.loads(resp_body)
        except Exception:
            body = {"raw": str(resp_body)}
    data = body.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    return {"body": body, "data": data}


def criar_pix_qr(
    amount_cents: int,
    description: str,
    external_id: str,
    customer: Optional[Dict[str, Any]] = None,
    return_url: Optional[str] = None,
    completion_url: Optional[str] = None,
    allow_coupons: bool = False,
    coupons: Optional[list] = None,
    dev_mode: bool = True  # ativa modo teste
) -> Dict[str, Any]:
    """
    Cria uma cobrança PIX na AbacatePay usando o endpoint v1/billing/create.
    Retorna dicionário com dados da cobrança, incluindo `billing_url`.
    """
    base_url = getattr(settings, "ABACATEPAY_BASE_URL", "").rstrip("/")
    url = f"{base_url}/billing/create"

    api_token = getattr(settings, "ABACATEPAY_API_KEY", "")
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "frequency": "ONE_TIME",
        "methods": ["PIX"],
        "products": [
            {
                "externalId": external_id,
                "name": description[:128],
                "description": description[:255],
                "quantity": 1,
                "price": amount_cents
            }
        ],
        "externalId": external_id,
        "returnUrl": return_url or getattr(settings, "ABACATEPAY_RETURN_URL", ""),
        "completionUrl": completion_url or getattr(settings, "ABACATEPAY_COMPLETION_URL", ""),
        "customer": customer or {},
        "allowCoupons": allow_coupons,
        "coupons": coupons or [],
        "metadata": {"externalId": external_id},
        "devMode": dev_mode  # ativa página de teste
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", {})

        billing_url = data.get("url") or data.get("billing_url") or data.get("payment_url")

        return {
            "ok": True,
            "status_code": resp.status_code,
            "data": data,
            "billing_url": billing_url,
            "error": None
        }

    except requests.RequestException as e:
        return {
            "ok": False,
            "status_code": getattr(e.response, "status_code", 0),
            "data": {},
            "billing_url": None,
            "error": str(e)
        }


def create_payment_for_corrida(corrida):
    """
    Cria um Payment para a corrida, gera QR PIX via AbacatePay
    e atualiza os campos billing_url, brCode e brCodeBase64.
    """
    if not corrida:
        return None

    amount_cents = int(corrida.valor_total * 100)
    description = f"Pagamento corrida #{corrida.id}"
    external_id = f"corrida-{corrida.id}"
    return_url = f"https://SEU-DOMINIO/pagamentos/retorno/{corrida.id}/"
    completion_url = f"https://SEU-DOMINIO/pagamentos/concluido/{corrida.id}/"

    payment = Payment.objects.create(
        corrida=corrida,
        amount=amount_cents,
        status="PENDING",
    )

    result_qr = criar_pix_qr(
        amount_cents=amount_cents,
        description=description,
        external_id=external_id,
        return_url=return_url,
        completion_url=completion_url,
    )

    data = result_qr.get("data") or {}
    payment.billing_url = data.get("billing_url") or data.get("url")
    payment.brCode = data.get("brCode")
    payment.brCodeBase64 = data.get("brCodeBase64")
    payment.status = "CREATED" if payment.billing_url else "FAILED"
    payment.save()

    return {"payment": payment, "data": data}


def obter_charge(abacate_id: str) -> Dict[str, Any]:
    """
    Consulta uma cobrança já existente na AbacatePay pelo id.
    """
    if not abacate_id:
        return {"ok": False, "status_code": 0, "body": None, "data": None, "error": "missing abacate_id"}

    headers = _build_headers()
    candidate_paths = [
        f"v1/pix/charges/{abacate_id}",
        f"v1/charges/{abacate_id}",
        f"v1/billing/{abacate_id}",
        f"pix/charges/{abacate_id}",
        f"charges/{abacate_id}",
        f"billing/{abacate_id}",
    ]

    last_error = None
    for path in candidate_paths:
        url = _full_url(path)
        try:
            resp = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
            status = resp.status_code
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text}
            norm = _normalize_body(body)
            data = norm["data"]
            if 200 <= status < 300:
                return {"ok": True, "status_code": status, "body": norm["body"], "data": data, "error": None}
            if status == 404:
                last_error = f"{url} 404"
                continue
            return {"ok": False, "status_code": status, "body": norm["body"], "data": None, "error": f"HTTP {status}"}
        except requests.RequestException as exc:
            last_error = str(exc)
            time.sleep(0.2)
            continue

    return {"ok": False, "status_code": 0, "body": None, "data": None, "error": last_error or "no route found"}

def criar_pix_carteira(
    amount_cents: int,
    description: str,
    external_id: str,
    customer: dict,
    return_url: str,
    completion_url: str
) -> dict:
    """
    Cria um Payment na AbacatePay para depósito na carteira.
    Retorna o dict com os dados do pagamento ou {} em caso de erro.
    """

    customer_data = {
        "name": customer.get("name") or "Cliente Teste",
        "email": customer.get("email") or "teste@teste.com",
        "cellphone": customer.get("cellphone") or "(11) 99999-9999",
        "taxId": customer.get("taxId") or "48975967859"
    }

    payload = {
        "frequency": "ONE_TIME",
        "methods": ["PIX"],
        "products": [
            {
                "externalId": f"prod-{uuid.uuid4().hex[:6]}",
                "name": description,
                "description": description,
                "quantity": 1,
                "price": amount_cents
            }
        ],
        "returnUrl": return_url,
        "completionUrl": completion_url,
        "customer": customer_data,
        "allowCoupons": False,
        "coupons": [],
        "externalId": external_id,
        "metadata": {
            "user_id": customer.get("id"),
            "external_id": external_id
        }
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    print("=== PAYLOAD ===")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("=== HEADERS ===")
    print(headers)

    try:
        response = requests.post(
            "https://api.abacatepay.com/v1/billing/create",
            json=payload,
            headers=headers,
            timeout=TIMEOUT
        )

        print("=== STATUS HTTP ===", response.status_code)
        print("=== RESPOSTA RAW ===", response.text)

        result = response.json()
        if response.status_code != 200 or result.get("error"):
            print("Erro na API AbacatePay:", result)
            return {}

        return result.get("data") or {}

    except requests.Timeout:
        print("Erro: Timeout ao conectar na AbacatePay")
        return {}
    except requests.RequestException as e:
        print("Erro de requisição na AbacatePay:", e)
        return {}
    except Exception as e:
        print("Erro inesperado ao criar PIX na AbacatePay:", e)
        return {}