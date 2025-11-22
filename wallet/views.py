from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import login
from django.utils import timezone
from datetime import datetime
from .models import User, Transaction
from .serializers import (
    UserSerializer, LoginSignupSerializer, SendTransactionSerializer,
    TransactionSerializer, BalanceSerializer
)
from .utils import (
    generate_keypair_from_seed, get_balance_sol, get_balance_usdc,
    send_sol, send_usdc, get_transaction_details
)
from django.conf import settings
import pytz


@api_view(['POST'])
@permission_classes([AllowAny])
def login_signup(request):
    """
    Combined login/signup endpoint.
    If user exists and password is correct, login.
    If user doesn't exist, create account and wallet.
    """
    serializer = LoginSignupSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        is_new_user = serializer.validated_data['is_new_user']
        
        # Login user
        login(request, user)
        
        user_serializer = UserSerializer(user, context={'request': request})
        
        return Response({
            'message': 'Account created successfully. Wallet generated!' if is_new_user else 'Login successful!',
            'user': user_serializer.data,
            'is_new_user': is_new_user
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_balance(request):
    """
    Get SOL and USDC balance for authenticated user's wallet
    """
    user = request.user
    
    if not user.wallet_address:
        return Response(
            {'error': 'Wallet not found for this user.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        sol_balance = get_balance_sol(user.wallet_address)
        usdc_balance = get_balance_usdc(user.wallet_address)
        
        serializer = BalanceSerializer({
            'sol_balance': sol_balance,
            'usdc_balance': usdc_balance,
            'wallet_address': user.wallet_address
        })
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': f'Error fetching balance: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_transaction(request):
    """
    Send SOL or USDC to another wallet
    """
    user = request.user
    
    if not user.wallet_address or not user.seed_phrase:
        return Response(
            {'error': 'Wallet not found for this user.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = SendTransactionSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    to_address = serializer.validated_data['to_address']
    amount = float(serializer.validated_data['amount'])
    token_type = serializer.validated_data['token_type']
    
    try:
        # Generate keypair from seed phrase
        keypair = generate_keypair_from_seed(user.seed_phrase)
        
        # Send transaction based on token type
        if token_type == 'SOL':
            tx_signature = send_sol(keypair, to_address, amount)
        elif token_type == 'USDC':
            tx_signature = send_usdc(keypair, to_address, amount)
        else:
            return Response(
                {'error': 'Invalid token type.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get transaction details
        tx_details = get_transaction_details(tx_signature)
        block_time = None
        if tx_details and hasattr(tx_details, 'block_time') and tx_details.block_time:
            block_time = tx_details.block_time
        
        # Save transaction to database
        transaction = Transaction.objects.create(
            user=user,
            transaction_signature=tx_signature,
            token_type=token_type,
            transaction_type='send',
            amount=amount,
            from_address=user.wallet_address,
            to_address=to_address,
            timestamp=timezone.now(),
            block_time=block_time,
            status='confirmed' if tx_details else 'pending'
        )
        
        # Also create a receive transaction for the recipient if they exist in our system
        try:
            recipient = User.objects.get(wallet_address=to_address)
            Transaction.objects.create(
                user=recipient,
                transaction_signature=tx_signature,
                token_type=token_type,
                transaction_type='receive',
                amount=amount,
                from_address=user.wallet_address,
                to_address=to_address,
                timestamp=timezone.now(),
                block_time=block_time,
                status='confirmed' if tx_details else 'pending'
            )
        except User.DoesNotExist:
            pass  # Recipient not in our system, that's okay
        
        tx_serializer = TransactionSerializer(transaction)
        
        return Response({
            'message': f'{token_type} sent successfully!',
            'transaction': tx_serializer.data,
            'transaction_signature': tx_signature
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': f'Transaction failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transactions(request):
    """
    Get all transactions for authenticated user
    """
    user = request.user
    transactions = Transaction.objects.filter(user=user)
    
    serializer = TransactionSerializer(transactions, many=True)
    
    return Response({
        'count': transactions.count(),
        'transactions': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    """
    Get user profile with wallet information
    """
    user = request.user
    serializer = UserSerializer(user, context={'request': request})
    
    return Response(serializer.data, status=status.HTTP_200_OK)

