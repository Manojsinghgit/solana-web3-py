from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import json


class User(AbstractUser):
    """Custom User model with wallet integration"""
    email = models.EmailField(unique=True)
    wallet_address = models.CharField(max_length=44, unique=True, null=True, blank=True)
    seed_phrase = models.TextField(null=True, blank=True)  # Seed phrase (consider encryption in production)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Remove username from required fields

    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        # Auto-generate username from email if not provided
        if not self.username:
            self.username = self.email.split('@')[0]
        super().save(*args, **kwargs)


class Transaction(models.Model):
    """Model to store all wallet transactions"""
    TOKEN_CHOICES = [
        ('SOL', 'Solana'),
        ('USDC', 'USD Coin'),
    ]
    
    TRANSACTION_TYPE_CHOICES = [
        ('send', 'Send'),
        ('receive', 'Receive'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_signature = models.CharField(max_length=88, unique=True)
    token_type = models.CharField(max_length=10, choices=TOKEN_CHOICES)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=20, decimal_places=9)
    from_address = models.CharField(max_length=44)
    to_address = models.CharField(max_length=44)
    timestamp = models.DateTimeField()
    block_time = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')  # pending, confirmed, failed
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['transaction_signature']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.token_type} - {self.amount}"

