# pagamentos/views.py
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET
from decouple import config

from .services import criar_pix_qr
from .models import Payment
from corrida.models import Corrida
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def abacatepay_webhook(request):
    """
    Stub de webhook simples: responde 200 para qualquer requisição.
    Substitua por lógica real de validação/atualização quando for ativar webhooks.
    """
    return HttpResponse(status=200)

def iniciar_pagamento(request, corrida_id):
    corrida = get_object_or_404(Corrida, pk=corrida_id)
    valor = float(corrida.valor or 0)
    valor_cents = int(round(valor * 100))

    pagamento = Payment.objects.create(
        corrida=corrida,
        user=request.user if request.user.is_authenticated else None,
        amount_cents=valor_cents,
        status="PENDING"
    )

    description = f"Pagamento corrida #{corrida_id}"
    external_id = f"corrida-{corrida_id}-payment-{pagamento.id}"

    customer = None
    if request.user.is_authenticated:
        customer = {"name": getattr(request.user, "nome", ""), "email": getattr(request.user, "email", "")}

    result = criar_pix_qr(valor_cents, description, external_id, customer=customer)

    if result["status_code"] != 200:
        pagamento.payload = result["body"]
        pagamento.status = "FAILED"
        pagamento.save(update_fields=["payload", "status"])
        return render(request, "pagamento_resultado.html", {"erro": result["body"]})

    data = result["body"].get("data", {})
    pagamento.abacate_id = data.get("id")
    pagamento.brCode = data.get("brCode")
    pagamento.brCodeBase64 = data.get("brCodeBase64")
    pagamento.payload = result["body"]
    pagamento.status = "CREATED"
    pagamento.save()

    return render(request, "pagamento_resultado.html", {"data": data, "payment_id": pagamento.id})

@require_GET
def payment_status(request, payment_id):
    p = get_object_or_404(Payment, pk=payment_id)
    return JsonResponse({
        "id": p.id,
        "status": p.status,
        "abacate_id": p.abacate_id,
        "payload": p.payload
    })
