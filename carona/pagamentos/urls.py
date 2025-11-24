from django.urls import path
from .views import iniciar_pagamento, payment_status, abacatepay_webhook, refresh_qr, adicionar_saldo_view, carteira_view, pagar_corrida_view

app_name = "pagamentos"

urlpatterns = [
    path("pagar/<int:corrida_id>/", iniciar_pagamento, name="iniciar_pagamento"),
    path("status/<int:payment_id>/", payment_status, name="payment_status"),
    path("webhook/abacatepay/", abacatepay_webhook, name="abacatepay_webhook"),
    path('refresh/<int:payment_id>/', refresh_qr, name='refresh_qr'),
    path("carteira/", carteira_view, name="carteira"),
    path("carteira/adicionar-saldo/", adicionar_saldo_view, name="adicionar_saldo"),
    path('corrida/<int:corrida_id>/pagar/', pagar_corrida_view, name='pagar_corrida'),
]

