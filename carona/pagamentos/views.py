# pagamentos/views.py
import re
import json
import hmac
import hashlib
import logging
import time
import uuid

import base64

from decimal import Decimal, InvalidOperation
from django.contrib import messages

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

from decimal import Decimal
from .services import create_payment_for_corrida
from .models import Payment, Carteira, WebhookEventProcessed
from corrida.models import Corrida
from pagamentos.services import criar_pix_carteira
import os

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.db import transaction

from usuarios.models import Usuario
from corrida.models import SolicitacaoCarona

logger = logging.getLogger(__name__)
User = get_user_model()


def _get_webhook_secret():
    return getattr(settings, "ABACATEPAY_WEBHOOK_SECRET", None)


def _find_in_payload(obj, keys):
    """
    Busca recursiva em dict/list por chaves em `keys` (lista de strings).
    Retorna tuple (value, path_list) com o primeiro match encontrado, ou (None, None).
    Normaliza comparações ignorando case e '_' (external_id == externalId).
    """
    normalized_keys = set(k.lower().replace("_", "") for k in keys)

    def norm(k):
        return str(k).lower().replace("_", "")

    visited = set()

    def _walk(o, path):
        oid = id(o)
        if oid in visited:
            return None, None
        visited.add(oid)

        if isinstance(o, dict):
            # check direct keys first
            for k, v in o.items():
                if norm(k) in normalized_keys:
                    return v, path + [k]
            # then recurse
            for k, v in o.items():
                val, p = _walk(v, path + [k])
                if val is not None:
                    return val, p
        elif isinstance(o, (list, tuple)):
            for idx, item in enumerate(o):
                val, p = _walk(item, path + [f"[{idx}]"])
                if val is not None:
                    return val, p
        return None, None

    return _walk(obj, [])


@csrf_exempt
def abacatepay_webhook(request):
    if request.method != "POST":
        return JsonResponse({"status": "method-not-allowed"}, status=405)

    raw_body = request.body

    webhook_secret = _get_webhook_secret()
    if not webhook_secret:
        logger.error("ABACATEPAY_WEBHOOK_SECRET não configurado")
        return JsonResponse({"status": "missing-webhook-secret"}, status=500)

    # validar webhookSecret (query string)
    qs_secret = request.GET.get("webhookSecret")
    if not qs_secret or qs_secret != webhook_secret:
        logger.warning("Webhook secret inválido (query string). recebido=%s esperado=%s", qs_secret, webhook_secret)
        return JsonResponse({"status": "invalid-webhook-secret"}, status=401)

    # assinatura
    signature_header = (
        request.headers.get("X-Webhook-Signature")
        or request.headers.get("X-Abacatepay-Signature")
        or request.headers.get("X-Abacate-Signature")
        or request.META.get("HTTP_X_WEBHOOK_SIGNATURE")
        or request.META.get("HTTP_X_ABACATEPAY_SIGNATURE")
        or request.META.get("HTTP_X_ABACATE_SIGNATURE")
    )
    if not signature_header:
        logger.warning("Header de assinatura ausente")
        return JsonResponse({"status": "missing-signature"}, status=401)

    pubkey = getattr(settings, "ABACATEPAY_PUBLIC_KEY", None)
    key_bytes = (pubkey or webhook_secret).encode("utf-8")

    try:
        expected_sig = base64.b64encode(hmac.new(key_bytes, raw_body, hashlib.sha256).digest()).decode()
    except Exception as exc:
        logger.exception("Erro ao calcular assinatura esperada: %s", exc)
        return JsonResponse({"status": "server-error"}, status=500)

    if not hmac.compare_digest(expected_sig, signature_header):
        logger.warning("Signature inválida. recebido=%s esperada=%s", signature_header, expected_sig)
        return JsonResponse({"status": "invalid-signature"}, status=401)

    try:
        data = json.loads(raw_body.decode("utf-8"))
    except Exception:
        logger.exception("JSON inválido no webhook")
        return JsonResponse({"status": "invalid-json"}, status=400)

    # suportar variações de nomes
    event_id = data.get("id") or data.get("event_id") or data.get("webhook_id")
    event_type = data.get("event") or data.get("type") or data.get("eventType")
    payload = data.get("data") or data.get("payload") or data

    if not event_id:
        logger.warning("Evento sem id (ignorado): %s", data)
        return JsonResponse({"status": "missing-event-id"}, status=400)

    # idempotência
    if WebhookEventProcessed.objects.filter(event_id=event_id).exists():
        logger.info("Evento %s já processado, ignorando", event_id)
        return JsonResponse({"status": "already_processed"}, status=200)

    try:
        with transaction.atomic():
            logger.debug("Processando evento webhook id=%s tipo=%s payload_keys=%s", event_id, event_type, list(payload.keys()) if isinstance(payload, dict) else None)

            # detectar billing.paid (aceita variações como 'paid' no tipo)
            if event_type == "billing.paid" or (isinstance(event_type, str) and "paid" in event_type.lower()):
                # procurar external_id e abacate_id/ids aninhados
                ext_value, ext_path = _find_in_payload(payload, ["external_id", "externalId", "externalid"])
                abacate_value, abacate_path = _find_in_payload(payload, ["id", "bill_id", "billing_id", "billingid", "payment_id", "paymentid"])

                logger.info("Webhook search results: external_id=%s (path=%s) abacate_id=%s (path=%s)",
                            ext_value, "->".join(ext_path) if ext_path else None,
                            abacate_value, "->".join(abacate_path) if abacate_path else None)

                # buscar amount (em centavos)
                amount_cents = None
                # tentar locais comuns
                for kloc in ("amount", "amount_cents", "value", "price"):
                    v = None
                    # checar payment/billing blocks se existirem
                    if isinstance(payload, dict):
                        if "payment" in payload and isinstance(payload["payment"], dict):
                            v = payload["payment"].get(kloc)
                        if v is None and "billing" in payload and isinstance(payload["billing"], dict):
                            v = payload["billing"].get(kloc)
                        if v is None:
                            v = payload.get(kloc)
                    if v is not None:
                        try:
                            amount_cents = int(v)
                            break
                        except (ValueError, TypeError):
                            continue
                if amount_cents is None:
                    try:
                        amount_cents = int(payload.get("amount") or payload.get("amount_cents") or 0)
                    except Exception:
                        amount_cents = 0

                # localizar Payment: primeiro por abacate_id, em seguida por external_id
                payment_qs = Payment.objects.none()
                if abacate_value:
                    # normalizar para string
                    payment_qs = Payment.objects.filter(abacate_id=str(abacate_value))
                if not payment_qs.exists() and ext_value:
                    payment_qs = Payment.objects.filter(external_id=str(ext_value))

                # fallback: se ainda não encontrou, tentar contains em external_id (caso payload traga prefix/sufix)
                if not payment_qs.exists() and ext_value:
                    payment_qs = Payment.objects.filter(external_id__icontains=str(ext_value))

                if not payment_qs.exists():
                    logger.warning(
                        "Nenhum Payment encontrado para external_id=%s abacate_id=%s (evento %s). payload keys: %s",
                        ext_value, abacate_value, event_id, list(payload.keys()) if isinstance(payload, dict) else None
                    )
                else:
                    for p in payment_qs:
                        if not p.abacate_id and abacate_value:
                            p.abacate_id = str(abacate_value)

                        # processar apenas se ainda não estiver pago
                        if p.status != Payment.STATUS_PAID:
                            # converter amount para Decimal reais
                            try:
                                valor_reais = (Decimal(amount_cents) / Decimal(100)).quantize(Decimal("0.01"))
                            except (InvalidOperation, TypeError):
                                valor_reais = Decimal("0.00")

                            if p.payment_type == Payment.PAYMENT_TYPE_DEPOSITO:
                                p.status = Payment.STATUS_PAID
                                if not p.paid_at:
                                    p.paid_at = timezone.now()

                                # se Payment.user ausente, tentar metadata.user_id no payload
                                if p.user:
                                    carteira, _ = Carteira.objects.get_or_create(user=p.user)
                                    carteira.depositar(valor_reais)
                                    logger.info("Carteira atualizada (DEPÓSITO) usuario=%s +R$ %s (payment=%s)",
                                                getattr(p.user, "nome", str(p.user)), valor_reais, p.id)
                                else:
                                    # procurar user_id dentro do payload
                                    candidate_user, cand_path = _find_in_payload(payload, ["user_id", "userid"])
                                    if candidate_user:
                                        try:
                                            user = User.objects.get(pk=int(candidate_user))
                                            p.user = user
                                            p.save(update_fields=["user"])
                                            carteira, _ = Carteira.objects.get_or_create(user=user)
                                            carteira.depositar(valor_reais)
                                            logger.info("Associado user.id=%s ao Payment %s e depositei R$ %s", user.id, p.id, valor_reais)
                                        except Exception:
                                            logger.exception("Falha ao associar user_id %s ao payment %s", candidate_user, p.id)
                                    else:
                                        logger.warning("Payment %s sem user e metadata.user_id ausente — não foi possível creditar.", p.id)
                            else:
                                # para corrida, marcar pago (implementação em Payment.mark_paid)
                                p.mark_paid(when=timezone.now())

                        # atualizar payload e campos
                        p.payload = payload
                        if isinstance(payload, dict):
                            billing_url = payload.get("billing_url") or payload.get("billingUrl")
                            if billing_url:
                                p.billing_url = billing_url
                        if ext_value:
                            p.external_id = p.external_id or str(ext_value)

                        update_fields = ["payload", "updated_at"]
                        if p.abacate_id:
                            update_fields.append("abacate_id")
                        if getattr(p, "billing_url", None):
                            update_fields.append("billing_url")
                        if p.external_id:
                            update_fields.append("external_id")
                        if p.status:
                            update_fields.append("status")
                        if p.paid_at:
                            update_fields.append("paid_at")

                        # remover duplicados mantendo ordem
                        seen = set()
                        final_update_fields = []
                        for f in update_fields:
                            if f not in seen:
                                final_update_fields.append(f)
                                seen.add(f)

                        p.save(update_fields=final_update_fields)

            elif event_type and ("withdraw" in str(event_type).lower()):
                # tratar withdraw.done / withdraw.failed (simplificado)
                txn = payload.get("transaction") or {}
                txn_external = txn.get("externalId") or txn.get("external_id")
                if txn_external:
                    payments = Payment.objects.filter(external_id=txn_external)
                    for p in payments:
                        p.payload = payload
                        p.save(update_fields=["payload"])
                if "failed" in str(event_type).lower():
                    for p in payments:
                        p.status = Payment.STATUS_FAILED
                        p.payload = payload
                        p.save(update_fields=["status", "payload"])

            else:
                logger.info("Evento não tratado: %s (payload keys: %s)", event_type, list(payload.keys()) if isinstance(payload, dict) else None)

            # registrar evento processado
            WebhookEventProcessed.objects.create(
                event_id=event_id,
                event_type=event_type or "",
                payload=payload
            )

        return JsonResponse({"status": "ok"}, status=200)

    except Exception as exc:
        logger.exception("Erro processando webhook: %s", exc)
        return JsonResponse({"status": "error"}, status=500)



@login_required
@transaction.atomic
def refresh_qr(request, payment_id):
    """Recria o QR ou cria um novo Payment se o anterior falhou/expirou."""
    old_payment = get_object_or_404(Payment, pk=payment_id)

    # Controle de acesso: apenas o dono do pagamento
    if old_payment.user and old_payment.user != request.user:
        return JsonResponse({"error": "Acesso negado"}, status=403)

    # Só permite refresh se status for FAILED ou EXPIRED
    if old_payment.status not in [Payment.STATUS_FAILED, Payment.STATUS_EXPIRED]:
        return JsonResponse({"error": "QR ainda válido", "status": old_payment.status}, status=400)

    # --- Cria novo pagamento via AbacatePay ---
    from .services import criar_pix_carteira

    customer_info = {
        "id": request.user.id,
        "name": request.user.nome,
        "email": request.user.email,
        "cellphone": "(00) 0000-0000",  # opcional, se precisar
        "taxId": "00000000000"           # opcional, se precisar
    }

    external_id = f"carteira-{request.user.id}-deposito-{old_payment.id}-{uuid.uuid4().hex[:6]}"
    result = criar_pix_carteira(
        amount_cents=old_payment.amount_cents,
        description=f"Depósito na carteira - {request.user.nome}",
        external_id=external_id,
        customer=customer_info,
        return_url=request.build_absolute_uri("/pagamentos/carteira/"),
        completion_url=request.build_absolute_uri("/pagamentos/carteira/")
    )

    # Atualiza campos críticos do payment antigo ou cria um novo se necessário
    old_payment.abacate_id = result.get("id")
    old_payment.billing_url = result.get("billing_url") or result.get("url") or result.get("payment_url")
    old_payment.external_id = external_id
    old_payment.status = Payment.STATUS_PENDING
    old_payment.save(update_fields=["abacate_id", "billing_url", "external_id", "status"])

    return JsonResponse({
        "ok": True,
        "billing_url": old_payment.billing_url,
        "status": old_payment.status,
        "payment_id": old_payment.id
    })



@transaction.atomic
@login_required
def iniciar_pagamento(request, corrida_id):
    """Cria Payment e retorna template de acompanhamento."""
    corrida = get_object_or_404(Corrida, pk=corrida_id)

    # controle de acesso opcional
    # if request.user != corrida.motorista: ...

    result = create_payment_for_corrida(corrida, user=request.user if request.user.is_authenticated else None)
    if not result:
        return render(request, "pagamentos/pagamento_resultado.html", {"erro": "Erro ao criar pagamento"})

    payment = result.get("payment")
    data = result.get("data") or {}

    # atualiza campos críticos se necessário
    updates = {
        "abacate_id": data.get("id"),
        "brCode": data.get("brCode"),
        "brCodeBase64": data.get("brCodeBase64"),
        "billing_url": data.get("billing_url") or data.get("url") or data.get("payment_url"),
        "external_id": data.get("external_id") or data.get("externalId") or f"corrida-{corrida.id}-payment-{payment.id}"
    }

    updated_fields = []
    for k, v in updates.items():
        if _safe_setattr(payment, k, v):
            updated_fields.append(k)
    if updated_fields:
        payment.save(update_fields=updated_fields)

    context = {
        "data": data,
        "payment_id": payment.id,
        "payment": {
            "id": payment.id,
            "status": payment.status,
            "amount_display": payment.amount_display(),
            "brCode": payment.brCode,
            "brCodeBase64": payment.brCodeBase64,
            "billing_url": getattr(payment, "billing_url", None),
            "expires_in": int(data.get("expires_in") or 3600),
        },
        "raw": payment.payload,
    }
    return render(request, "corrida/acompanhamento.html", context)


@login_required
def carteira_view(request):
    carteira, _ = Carteira.objects.get_or_create(user=request.user)
    pagamentos = Payment.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "pagamentos/carteira.html", {"carteira": carteira, "pagamentos": pagamentos})



@login_required
@transaction.atomic
def adicionar_saldo_view(request):
    """
    View para adicionar saldo à carteira.
    Cria um Payment local, chama a API AbacatePay e retorna JSON com URL do pagamento.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método inválido"}, status=405)

    valor_str = request.POST.get("valor")
    try:
        valor = Decimal(valor_str)
        if valor <= 0:
            raise ValueError()
    except:
        return JsonResponse({"error": "Valor inválido"}, status=400)

    # 1️⃣ Criar Payment localmente (external_id gerado agora para garantir sincronia)
    pagamento = Payment.objects.create(
        user=request.user,
        amount_cents=int(valor * 100),
        status=Payment.STATUS_PENDING,
        payment_type=Payment.PAYMENT_TYPE_DEPOSITO,
        external_id=f"carteira-{request.user.id}-deposito-{uuid.uuid4().hex[:8]}",  # id único já na criação
    )

    # 2️⃣ Chamar AbacatePay
    try:
        result = criar_pix_carteira(
            amount_cents=pagamento.amount_cents,
            description=f"Depósito {request.user.nome}",
            external_id=pagamento.external_id,  # garante que o externalId enviado coincide com o local
            customer={
                "id": request.user.id,
                "name": request.user.nome,
                "email": request.user.email,
            },
            return_url=request.build_absolute_uri("/pagamentos/carteira/"),
            completion_url=request.build_absolute_uri("/pagamentos/carteira/")
        )

        # Normalizar resposta: o service pode retornar data em result['data'] ou direto em result
        data = {}
        if isinstance(result, dict):
            # aceitar tanto { "data": {...} } quanto já o bloco { "id": ..., "url": ... }
            data = result.get("data") or result
        else:
            data = {}

        # extrair os campos de interesse (vários nomes possíveis)
        abacate_id = data.get("id") or data.get("bill_id") or data.get("payment_id")
        billing_url = data.get("url") or data.get("billing_url") or data.get("payment_url")
        returned_external = data.get("externalId") or data.get("external_id") or result.get("externalId") or result.get("external_id")

        # gravar nos campos do pagamento
        # garanti que sempre salvamos abacate_id quando retornado pelo provedor
        changed_fields = []
        if abacate_id and pagamento.abacate_id != abacate_id:
            pagamento.abacate_id = abacate_id
            changed_fields.append("abacate_id")
        if billing_url and getattr(pagamento, "billing_url", None) != billing_url:
            pagamento.billing_url = billing_url
            changed_fields.append("billing_url")
        # preferir externalId retornado, mas não sobrescrever quando vazio
        if returned_external and pagamento.external_id != returned_external:
            pagamento.external_id = returned_external
            changed_fields.append("external_id")

        # armazenar payload de referência
        pagamento.payload = data or result
        if "payload" not in changed_fields:
            changed_fields.append("payload")

        pagamento.save(update_fields=changed_fields)

        if data and (billing_url or abacate_id):
            # sucesso: retornar a URL de pagamento para o frontend
            return JsonResponse({"success": True, "url": billing_url or data.get("payment_url"), "abacate_id": abacate_id})
        else:
            logger.warning("Pagamento criado mas resposta AbacatePay não contém url/abacate_id. result=%s", result)
            return JsonResponse({"success": False, "message": "Erro ao gerar URL de pagamento", "result": result})

    except Exception as e:
        logger.exception("Erro ao processar pagamento AbacatePay")
        # opcional: marcar pagamento como FAILED ou deixar como CREATED/PENDING para tentativa posterior
        pagamento.status = Payment.STATUS_FAILED
        pagamento.save(update_fields=["status"])
        return JsonResponse({"success": False, "message": "Erro ao processar pagamento"})


@login_required
@transaction.atomic
def pagar_corrida_view(request, corrida_id):
    """
    Processa o pagamento de uma corrida usando a carteira do passageiro.
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método inválido"}, status=405)

    corrida = get_object_or_404(Corrida, pk=corrida_id)

    # verifica se o usuário logado é passageiro da corrida
    # aqui assumimos que passageiro é aquele que tem uma SolicitacaoCarona aceita
    passageiro_solicitacao = corrida.solicitacoes.filter(
        passageiro=request.user, status='ACEITA'
    ).first()
    if not passageiro_solicitacao:
        return JsonResponse({"ok": False, "error": "Acesso negado: não é passageiro desta corrida"}, status=403)

    # pega valor da corrida
    valor_corrida = corrida.valor
    if valor_corrida is None:
        return JsonResponse({"ok": False, "error": "Valor da corrida não definido"}, status=400)
    
    valor_corrida = Decimal(valor_corrida)

    # carteira do passageiro
    passageiro_carteira, _ = Carteira.objects.get_or_create(user=request.user)

    if passageiro_carteira.saldo < valor_corrida:
        return JsonResponse({"ok": False, "error": "Saldo insuficiente"}, status=400)

    # carteira do motorista
    motorista_carteira, _ = Carteira.objects.get_or_create(user=corrida.motorista)

    # porcentagem de retenção (flexível via settings)
    RETENCAO_PORCENTAGEM = Decimal(getattr(settings, "PORCENTAGEM_RETENCAO", 0.10))
    valor_retenido = (valor_corrida * RETENCAO_PORCENTAGEM).quantize(Decimal("0.01"))
    valor_liquido_motorista = (valor_corrida - valor_retenido).quantize(Decimal("0.01"))

    # debitar passageiro
    passageiro_carteira.saldo -= valor_corrida
    passageiro_carteira.save(update_fields=["saldo"])

    # creditar motorista
    motorista_carteira.saldo += valor_liquido_motorista
    motorista_carteira.save(update_fields=["saldo"])

    # registra pagamento no histórico (Payment)
    payment = Payment.objects.create(
        corrida=corrida,
        user=request.user,
        amount_cents=int(valor_corrida * 100),
        status=Payment.STATUS_PAID,
        payment_method="CARTEIRA",
        external_id=f"corrida-{corrida.id}-carteira",
        payload={
            "retencao_percent": float(RETENCAO_PORCENTAGEM),
            "valor_retenido": float(valor_retenido),
            "valor_liquido_motorista": float(valor_liquido_motorista),
        }
    )

    return JsonResponse({
        "ok": True,
        "payment_id": payment.id,
        "valor_corrida": float(valor_corrida),
        "retencao": float(valor_retenido),
        "valor_motorista": float(valor_liquido_motorista),
        "novo_saldo_passageiro": float(passageiro_carteira.saldo),
        "novo_saldo_motorista": float(motorista_carteira.saldo),
        "mensagem": "Pagamento realizado com sucesso!"
    })



@login_required
def payment_status(request, payment_id):
    """Retorna status de um payment (opcional)."""
    payment = Payment.objects.filter(id=payment_id).first()
    if not payment:
        return JsonResponse({"error": "Payment não encontrado"}, status=404)
    return JsonResponse({"status": payment.status})
