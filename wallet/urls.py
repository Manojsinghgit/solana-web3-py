from django.urls import path
from . import views

urlpatterns = [
    path('auth/login-signup/', views.login_signup, name='login-signup'),
    path('wallet/balance/', views.get_balance, name='get-balance'),
    path('wallet/send/', views.send_transaction, name='send-transaction'),
    path('wallet/transactions/', views.get_transactions, name='get-transactions'),
    path('user/profile/', views.get_profile, name='get-profile'),
]

