# Setup Instructions

## Installation Steps

1. **Create and activate virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run migrations:**
```bash
python manage.py makemigrations
python manage.py migrate
```

4. **Create superuser (optional):**
```bash
python manage.py createsuperuser
```

5. **Run the server:**
```bash
python manage.py runserver
```

## Important Notes

### USDC Functionality
The USDC send functionality uses a simplified implementation. For production use, you may need to:
- Install and configure a proper SPL token library
- Ensure associated token accounts are created before transfers
- Handle token account initialization

### Network Configuration
By default, the project uses Solana Devnet. To switch to Mainnet:
1. Update `SOLANA_RPC_URL` in `settings.py` to `https://api.mainnet-beta.solana.com`
2. Update `USDC_MINT_ADDRESS` to mainnet USDC mint: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`

### Security
- Seed phrases are stored in plain text for this demo
- In production, implement proper encryption
- Change `SECRET_KEY` in `settings.py`
- Use environment variables for sensitive data

## Testing

You can test the API using curl:

```bash
# Signup/Login
curl -X POST http://localhost:8000/api/auth/login-signup/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}' \
  -c cookies.txt

# Get Balance
curl -X GET http://localhost:8000/api/wallet/balance/ \
  -b cookies.txt

# Send SOL
curl -X POST http://localhost:8000/api/wallet/send/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "to_address": "recipient_wallet_address",
    "amount": "0.1",
    "token_type": "SOL"
  }'
```

