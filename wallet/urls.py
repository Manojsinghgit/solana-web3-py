from django.urls import path
from . import views

urlpatterns = [
    path("auth/login-signup/", views.LoginSignupView.as_view(), name="login-signup"),
    path("wallet/balance/", views.GetBalanceView.as_view(), name="get-balance"),
    path("wallet/send/", views.SendTransactionView.as_view(), name="send-transaction"),
    path(
        "wallet/transactions/",
        views.GetTransactionsView.as_view(),
        name="get-transactions",
    ),
    path("user/profile/", views.GetProfileView.as_view(), name="get-profile"),
]
