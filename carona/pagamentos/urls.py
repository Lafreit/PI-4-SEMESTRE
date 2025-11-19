from django.urls import path
from .views import iniciar_pagamento, payment_status, abacatepay_webhook

app_name = "pagamentos"

urlpatterns = [
    path("status/<int:payment_id>/", payment_status, name="payment_status"),
    path("status/<int:payment_id>/", payment_status, name="payment_status"),
    path("webhook/abacatepay/", abacatepay_webhook, name="abacatepay_webhook"),
]
