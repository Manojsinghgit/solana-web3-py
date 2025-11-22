from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Transaction
from .utils import generate_new_wallet, generate_keypair_from_seed
from django.conf import settings


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    seed_phrase = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'wallet_address', 'seed_phrase', 'created_at']
        read_only_fields = ['id', 'wallet_address', 'seed_phrase', 'created_at']
    
    def get_seed_phrase(self, obj):
        # Only return seed phrase if user is viewing their own profile
        request = self.context.get('request')
        if request and request.user == obj:
            return obj.seed_phrase
        return None


class LoginSignupSerializer(serializers.Serializer):
    """Serializer for login/signup endpoint"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError('Email and password are required.')
        
        # Try to authenticate user
        user = authenticate(username=email, password=password)
        
        if user:
            # User exists and password is correct
            attrs['user'] = user
            attrs['is_new_user'] = False
        else:
            # Check if user exists with wrong password
            try:
                User.objects.get(email=email)
                raise serializers.ValidationError('Invalid password.')
            except User.DoesNotExist:
                # New user - create wallet
                wallet_data = generate_new_wallet()
                user = User.objects.create_user(
                    username=email.split('@')[0],
                    email=email,
                    password=password,
                    wallet_address=wallet_data['public_key'],
                    seed_phrase=wallet_data['seed_phrase']
                )
                attrs['user'] = user
                attrs['is_new_user'] = True
        
        return attrs


class SendTransactionSerializer(serializers.Serializer):
    """Serializer for sending transactions"""
    to_address = serializers.CharField(max_length=44)
    amount = serializers.DecimalField(max_digits=20, decimal_places=9)
    token_type = serializers.ChoiceField(choices=['SOL', 'USDC'])
    
    def validate_to_address(self, value):
        # Basic validation for Solana address
        if len(value) < 32 or len(value) > 44:
            raise serializers.ValidationError('Invalid Solana address format.')
        return value
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than 0.')
        return value


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""
    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_signature', 'token_type', 'transaction_type',
            'amount', 'from_address', 'to_address', 'timestamp', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class BalanceSerializer(serializers.Serializer):
    """Serializer for balance response"""
    sol_balance = serializers.DecimalField(max_digits=20, decimal_places=9)
    usdc_balance = serializers.DecimalField(max_digits=20, decimal_places=6)
    wallet_address = serializers.CharField()

