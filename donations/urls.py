from django.urls import path
from . import views

urlpatterns = [
    path('', views.DonationView.as_view(), name='donation'),
    path('success/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('cancel/', views.PaymentCancelView.as_view(), name='payment_cancel'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('api/stats/', views.DonationStatsAPIView.as_view(), name='donation_stats_api'),
]
