from django.contrib import admin
from .models import User, Transaction


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'wallet_address', 'created_at']
    search_fields = ['email', 'username', 'wallet_address']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'token_type', 'amount', 'transaction_type', 'timestamp', 'status']
    list_filter = ['token_type', 'transaction_type', 'status', 'timestamp']
    search_fields = ['transaction_signature', 'user__email', 'from_address', 'to_address']
    readonly_fields = ['created_at']

