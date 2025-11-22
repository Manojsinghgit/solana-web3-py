# Solana Wallet Django REST API

A Django REST Framework project with Solana Web3 integration for wallet management, transactions, and balance tracking.

## Features

- **User Authentication**: Combined login/signup endpoint
- **Automatic Wallet Creation**: Wallet is created automatically when user signs up
- **Seed Phrase Generation**: Secure seed phrase generation and storage
- **Send Transactions**: Send SOL and USDC on Solana chain
- **Balance Checking**: Check SOL and USDC balances
- **Transaction History**: Track all transactions in database
- **User-specific Transactions**: Users can only see their own transactions

## Installation

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. Create superuser (optional):
```bash
python manage.py createsuperuser
```

5. Run the server:
```bash
python manage.py runserver
```

## API Endpoints

### 1. Login/Signup
**POST** `/api/auth/login-signup/`

Request body:
```json
{
    "email": "user@example.com",
    "password": "yourpassword"
}
```

Response:
```json
{
    "message": "Account created successfully. Wallet generated!",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "username": "user",
        "wallet_address": "ABC123...",
        "seed_phrase": "word1 word2 word3 ...",
        "created_at": "2024-01-01T00:00:00Z"
    },
    "is_new_user": true
}
```

### 2. Get Balance
**GET** `/api/wallet/balance/`

Headers:
```
Authorization: Session authentication required
```

Response:
```json
{
    "sol_balance": "1.5",
    "usdc_balance": "100.0",
    "wallet_address": "ABC123..."
}
```

### 3. Send Transaction
**POST** `/api/wallet/send/`

Headers:
```
Authorization: Session authentication required
```

Request body:
```json
{
    "to_address": "recipient_wallet_address",
    "amount": "0.1",
    "token_type": "SOL"  // or "USDC"
}
```

Response:
```json
{
    "message": "SOL sent successfully!",
    "transaction": {
        "id": 1,
        "transaction_signature": "tx_signature...",
        "token_type": "SOL",
        "transaction_type": "send",
        "amount": "0.1",
        "from_address": "sender_address",
        "to_address": "recipient_address",
        "timestamp": "2024-01-01T00:00:00Z",
        "status": "confirmed"
    },
    "transaction_signature": "tx_signature..."
}
```

### 4. Get Transactions
**GET** `/api/wallet/transactions/`

Headers:
```
Authorization: Session authentication required
```

Response:
```json
{
    "count": 10,
    "transactions": [
        {
            "id": 1,
            "transaction_signature": "tx_signature...",
            "token_type": "SOL",
            "transaction_type": "send",
            "amount": "0.1",
            "from_address": "sender_address",
            "to_address": "recipient_address",
            "timestamp": "2024-01-01T00:00:00Z",
            "status": "confirmed"
        }
    ]
}
```

### 5. Get Profile
**GET** `/api/user/profile/`

Headers:
```
Authorization: Session authentication required
```

Response:
```json
{
    "id": 1,
    "email": "user@example.com",
    "username": "user",
    "wallet_address": "ABC123...",
    "seed_phrase": "word1 word2 word3 ...",
    "created_at": "2024-01-01T00:00:00Z"
}
```

## Configuration

The project uses Solana Devnet by default. To change to Mainnet, update `SOLANA_RPC_URL` in `settings.py`:

```python
SOLANA_RPC_URL = 'https://api.mainnet-beta.solana.com'
```

Also update the USDC mint address for mainnet:
```python
USDC_MINT_ADDRESS = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'  # Mainnet USDC
```

## Security Notes

- Seed phrases are stored in plain text in the database for this demo. In production, use proper encryption.
- Change the `SECRET_KEY` in `settings.py` for production.
- Use environment variables for sensitive configuration.
- Implement proper rate limiting and authentication mechanisms.

## Testing

You can test the API using curl, Postman, or any HTTP client:

```bash
# Signup/Login
curl -X POST http://localhost:8000/api/auth/login-signup/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'

# Get Balance (use session cookie from login)
curl -X GET http://localhost:8000/api/wallet/balance/ \
  -H "Cookie: sessionid=your_session_id"
```

## License

MIT

