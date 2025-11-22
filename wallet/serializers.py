from rest_framework import serializers
from .models import User, Transaction


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
    """Serializer for login/signup endpoint - only validation"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value

    def validate_password(self, value):
        if not value:
            raise serializers.ValidationError("Password is required.")
        if len(value) < 6:
            raise serializers.ValidationError(
                "Password must be at least 6 characters long."
            )
        return value


class SendTransactionSerializer(serializers.Serializer):
    """Serializer for sending transactions - only validation"""
    to_address = serializers.CharField(max_length=44)
    amount = serializers.DecimalField(max_digits=20, decimal_places=9)
    token_type = serializers.ChoiceField(choices=['SOL', 'USDC'])

    def validate_to_address(self, value):
        # Basic validation for Solana address
        if not value:
            raise serializers.ValidationError("Recipient address is required.")
        if len(value) < 32 or len(value) > 44:
            raise serializers.ValidationError('Invalid Solana address format.')
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than 0.')
        return value

    def validate_token_type(self, value):
        if value not in ["SOL", "USDC"]:
            raise serializers.ValidationError("Token type must be SOL or USDC.")
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
