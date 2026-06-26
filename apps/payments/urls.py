from django.urls import path

from .views import (
    checkout,
    download_receipt,
    mpesa_callback,
    payment_history,
    payment_pending,
    payment_status,
    purchase_initiate,
    receipt_view,
)

app_name = "payments"

urlpatterns = [
    path("checkout/<int:level_id>/", checkout, name="checkout"),
    path("initiate/<int:level_id>/", purchase_initiate, name="initiate"),
    path("pending/<int:payment_id>/", payment_pending, name="pending"),
    path("status/<int:payment_id>/", payment_status, name="status"),
    path("history/", payment_history, name="history"),
    path("receipt/<int:payment_id>/", receipt_view, name="receipt"),
    path("receipt/<int:payment_id>/download/", download_receipt, name="download_receipt"),
    path("mpesa/callback/", mpesa_callback, name="mpesa_callback"),
]
