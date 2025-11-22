from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import login, authenticate
from django.utils import timezone
from .models import User, Transaction
from .serializers import (
    UserSerializer, LoginSignupSerializer, SendTransactionSerializer,
    TransactionSerializer, BalanceSerializer
)
from .utils import (
    generate_new_wallet,
    generate_keypair_from_seed,
    get_balance_sol,
    get_balance_usdc,
    send_sol,
    send_usdc,
    get_transaction_details,
)


class LoginSignupView(APIView):
    """
    Combined login/signup endpoint.
    If user exists and password is correct, login.
    If user doesn't exist, create account and wallet.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSignupSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data.get("email")
        password = serializer.validated_data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Try to authenticate user
        user = authenticate(username=email, password=password)
        is_new_user = False

        if user:
            # User exists and password is correct
            is_new_user = False
        else:
            # Check if user exists with wrong password
            try:
                existing_user = User.objects.get(email=email)
                return Response(
                    {"error": "Invalid password."}, status=status.HTTP_400_BAD_REQUEST
                )
            except User.DoesNotExist:
                # New user - create wallet
                wallet_data = generate_new_wallet()
                username = email.split("@")[0]
                # Make username unique if needed
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    wallet_address=wallet_data["public_key"],
                    seed_phrase=wallet_data["seed_phrase"],
                )
                is_new_user = True

        # Login user
        login(request, user)

        user_serializer = UserSerializer(user, context={'request': request})

        message = (
            "Account created successfully. Wallet generated!"
            if is_new_user
            else "Login successful!"
        )

        return Response(
            {
                "message": message,
                "user": user_serializer.data,
                "is_new_user": is_new_user,
            },
            status=status.HTTP_200_OK,
        )


class GetBalanceView(APIView):
    """
    Get SOL and USDC balance for authenticated user's wallet
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if not user.wallet_address:
            return Response(
                {"error": "Wallet not found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            sol_balance = get_balance_sol(user.wallet_address)
            usdc_balance = get_balance_usdc(user.wallet_address)

            return Response(
                {
                    "sol_balance": str(sol_balance),
                    "usdc_balance": str(usdc_balance),
                    "wallet_address": user.wallet_address,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"Error fetching balance: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SendTransactionView(APIView):
    """
    Send SOL or USDC to another wallet
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if not user.wallet_address or not user.seed_phrase:
            return Response(
                {"error": "Wallet not found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SendTransactionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        to_address = serializer.validated_data.get("to_address")
        amount = float(serializer.validated_data.get("amount"))
        token_type = serializer.validated_data.get("token_type")

        # Validate token type
        if token_type not in ["SOL", "USDC"]:
            return Response(
                {"error": "Invalid token type. Must be SOL or USDC."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate amount
        if amount <= 0:
            return Response(
                {"error": "Amount must be greater than 0."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate address format
        if len(to_address) < 32 or len(to_address) > 44:
            return Response(
                {"error": "Invalid Solana address format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Generate keypair from seed phrase
            keypair = generate_keypair_from_seed(user.seed_phrase)

            # Send transaction based on token type
            if token_type == "SOL":
                tx_signature = send_sol(keypair, to_address, amount)
            elif token_type == "USDC":
                tx_signature = send_usdc(keypair, to_address, amount)
            else:
                return Response(
                    {"error": "Invalid token type."}, status=status.HTTP_400_BAD_REQUEST
                )

            # Get transaction details
            tx_details = get_transaction_details(tx_signature)
            block_time = None
            if (
                tx_details
                and hasattr(tx_details, "block_time")
                and tx_details.block_time
            ):
                block_time = tx_details.block_time

            # Save transaction to database
            transaction = Transaction.objects.create(
                user=user,
                transaction_signature=tx_signature,
                token_type=token_type,
                transaction_type="send",
                amount=amount,
                from_address=user.wallet_address,
                to_address=to_address,
                timestamp=timezone.now(),
                block_time=block_time,
                status="confirmed" if tx_details else "pending",
            )

            # Also create a receive transaction for the recipient if they exist in our system
            try:
                recipient = User.objects.get(wallet_address=to_address)
                Transaction.objects.create(
                    user=recipient,
                    transaction_signature=tx_signature,
                    token_type=token_type,
                    transaction_type="receive",
                    amount=amount,
                    from_address=user.wallet_address,
                    to_address=to_address,
                    timestamp=timezone.now(),
                    block_time=block_time,
                    status="confirmed" if tx_details else "pending",
                )
            except User.DoesNotExist:
                pass  # Recipient not in our system, that's okay

            tx_serializer = TransactionSerializer(transaction)

            return Response(
                {
                    "message": f"{token_type} sent successfully!",
                    "transaction": tx_serializer.data,
                    "transaction_signature": tx_signature,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"Transaction failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GetTransactionsView(APIView):
    """
    Get all transactions for authenticated user
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        transactions = Transaction.objects.filter(user=user).order_by("-timestamp")

        serializer = TransactionSerializer(transactions, many=True)

        return Response(
            {"count": transactions.count(), "transactions": serializer.data},
            status=status.HTTP_200_OK,
        )


class GetProfileView(APIView):
    """
    Get user profile with wallet information
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user, context={"request": request})

        return Response(serializer.data, status=status.HTTP_200_OK)
