"""
Utility functions for Solana wallet operations
"""
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import transfer, TransferParams
from solders.transaction import Transaction
from solders.commitment_config import CommitmentLevel
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
import mnemonic
import os
from django.conf import settings
from cryptography.fernet import Fernet
import base58
import struct
import hashlib


def generate_keypair_from_seed(seed_phrase):
    """Generate a Solana keypair from seed phrase"""
    mnemo = mnemonic.Mnemonic("english")
    if not mnemo.check(seed_phrase):
        raise ValueError("Invalid seed phrase")
    
    seed = mnemo.to_seed(seed_phrase)
    # Use first 32 bytes for keypair
    seed_bytes = seed[:32]
    keypair = Keypair.from_bytes(seed_bytes)
    return keypair


def generate_new_wallet():
    """Generate a new Solana wallet with seed phrase"""
    mnemo = mnemonic.Mnemonic("english")
    seed_phrase = mnemo.generate(strength=128)  # 12 words
    keypair = generate_keypair_from_seed(seed_phrase)
    public_key = str(keypair.pubkey())
    
    return {
        'seed_phrase': seed_phrase,
        'public_key': public_key,
        'keypair': keypair
    }


def get_associated_token_address(owner_pubkey, mint_pubkey):
    """Calculate associated token account address (ATA) using PDA derivation"""
    # Associated Token Program ID
    ASSOCIATED_TOKEN_PROGRAM_ID = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
    TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    
    # Convert Pubkeys to bytes (Pubkey objects have a __bytes__ method)
    try:
        owner_bytes = bytes(owner_pubkey)
        token_program_bytes = bytes(TOKEN_PROGRAM_ID)
        mint_bytes = bytes(mint_pubkey)
    except:
        # If direct bytes conversion doesn't work, try alternative
        owner_bytes = owner_pubkey.__bytes__() if hasattr(owner_pubkey, '__bytes__') else bytes(owner_pubkey)
        token_program_bytes = TOKEN_PROGRAM_ID.__bytes__() if hasattr(TOKEN_PROGRAM_ID, '__bytes__') else bytes(TOKEN_PROGRAM_ID)
        mint_bytes = mint_pubkey.__bytes__() if hasattr(mint_pubkey, '__bytes__') else bytes(mint_pubkey)
    
    # Create seeds for PDA (Program Derived Address)
    seeds = [
        owner_bytes,
        token_program_bytes,
        mint_bytes
    ]
    
    # Find PDA using solders
    try:
        from solders.pubkey import find_program_address
        pda, _ = find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM_ID)
        return pda
    except Exception as e:
        # Manual PDA calculation as fallback
        try:
            from solders.hash import hash
            from solders.pubkey import Pubkey
            
            # Combine seeds
            seed_data = b''.join(seeds)
            # Add program ID and discriminator
            seed_with_program = seed_data + bytes(ASSOCIATED_TOKEN_PROGRAM_ID) + b'ProgramDerivedAddress'
            # Hash
            hash_result = hash(seed_with_program)
            # Take first 32 bytes for pubkey
            pda_bytes = bytes(hash_result)[:32]
            return Pubkey.from_bytes(pda_bytes)
        except Exception as e2:
            raise Exception(f"Could not calculate ATA. Error: {str(e)}. Secondary error: {str(e2)}")


def get_solana_client():
    """Get Solana RPC client"""
    return Client(settings.SOLANA_RPC_URL)


def get_balance_sol(wallet_address):
    """Get SOL balance for a wallet"""
    client = get_solana_client()
    pubkey = Pubkey.from_string(wallet_address)
    response = client.get_balance(pubkey)
    if response.value is not None:
        # Convert lamports to SOL (1 SOL = 1,000,000,000 lamports)
        return response.value / 1_000_000_000
    return 0.0


def get_balance_usdc(wallet_address):
    """Get USDC balance for a wallet"""
    client = get_solana_client()
    pubkey = Pubkey.from_string(wallet_address)
    mint_pubkey = Pubkey.from_string(settings.USDC_MINT_ADDRESS)
    
    try:
        # Get associated token account
        token_account = get_associated_token_address(pubkey, mint_pubkey)
        
        # Get token account info
        response = client.get_token_account_balance(token_account)
        if response.value and hasattr(response.value, 'amount'):
            # USDC has 6 decimals
            return float(response.value.amount) / 1_000_000
        elif response.value and hasattr(response.value, 'ui_amount'):
            return float(response.value.ui_amount) if response.value.ui_amount else 0.0
        return 0.0
    except Exception as e:
        print(f"Error getting USDC balance: {e}")
        # Try alternative method - get account data
        try:
            token_account = get_associated_token_address(pubkey, mint_pubkey)
            account_info = client.get_account_info(token_account)
            if account_info.value and account_info.value.data:
                # Parse token account data (simplified - in production use proper parsing)
                data = account_info.value.data
                if len(data) >= 64:
                    # Amount is at offset 64, 8 bytes (uint64)
                    amount_bytes = data[64:72]
                    amount = struct.unpack('<Q', amount_bytes)[0]
                    return amount / 1_000_000
        except:
            pass
        return 0.0


def send_sol(from_keypair, to_address, amount):
    """Send SOL from one wallet to another"""
    client = get_solana_client()
    to_pubkey = Pubkey.from_string(to_address)
    
    # Convert SOL to lamports
    lamports = int(amount * 1_000_000_000)
    
    # Create transfer instruction
    transfer_ix = transfer(
        TransferParams(
            from_pubkey=from_keypair.pubkey(),
            to_pubkey=to_pubkey,
            lamports=lamports
        )
    )
    
    # Create and send transaction
    transaction = Transaction()
    transaction.add(transfer_ix)
    
    opts = TxOpts(skip_preflight=False, preflight_commitment=CommitmentLevel("confirmed"))
    response = client.send_transaction(transaction, from_keypair, opts=opts)
    
    if response.value:
        return str(response.value)
    raise Exception(f"Transaction failed: {response}")


def send_usdc(from_keypair, to_address, amount):
    """Send USDC from one wallet to another"""
    # Note: This implementation requires proper SPL token library setup
    # For now, this is a basic implementation that may need adjustments
    client = get_solana_client()
    mint_pubkey = Pubkey.from_string(settings.USDC_MINT_ADDRESS)
    to_pubkey = Pubkey.from_string(to_address)
    
    try:
        # Try to get associated token accounts
        from_token_account = get_associated_token_address(from_keypair.pubkey(), mint_pubkey)
        to_token_account = get_associated_token_address(to_pubkey, mint_pubkey)
    except Exception as e:
        raise Exception(f"Could not calculate associated token accounts. Please ensure spl-token library is properly installed. Error: {str(e)}")
    
    # Convert USDC amount (6 decimals)
    amount_ui = int(amount * 1_000_000)
    
    # Token Program ID
    TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    
    # Create transfer_checked instruction
    try:
        from solders.instruction import Instruction, AccountMeta
        
        # Build instruction data for transfer_checked
        # Instruction index: 12 (transfer_checked)
        # Amount: 8 bytes (uint64, little-endian)
        # Decimals: 1 byte (uint8)
        instruction_data = bytes([12]) + struct.pack('<Q', amount_ui) + struct.pack('B', 6)
        
        # Create accounts list for transfer_checked
        # Order: source, mint, destination, owner
        accounts = [
            AccountMeta(pubkey=from_token_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=mint_pubkey, is_signer=False, is_writable=False),
            AccountMeta(pubkey=to_token_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=from_keypair.pubkey(), is_signer=True, is_writable=False),
        ]
        
        # Create instruction
        transfer_ix = Instruction(
            program_id=TOKEN_PROGRAM_ID,
            data=instruction_data,
            accounts=accounts
        )
        
        # Create and send transaction
        transaction = Transaction()
        transaction.add(transfer_ix)
        
        opts = TxOpts(skip_preflight=False, preflight_commitment=CommitmentLevel("confirmed"))
        response = client.send_transaction(transaction, from_keypair, opts=opts)
        
        if response.value:
            return str(response.value)
        raise Exception(f"Transaction failed: {response}")
    except Exception as e:
        raise Exception(f"USDC transfer failed. Error: {str(e)}. Make sure token accounts exist and have sufficient balance.")


def get_transaction_details(tx_signature):
    """Get transaction details from blockchain"""
    client = get_solana_client()
    try:
        if isinstance(tx_signature, str):
            from solders.signature import Signature
            sig = Signature.from_string(tx_signature)
        else:
            sig = tx_signature
            
        response = client.get_transaction(
            sig,
            commitment=CommitmentLevel("confirmed"),
            max_supported_transaction_version=0
        )
        return response.value
    except Exception as e:
        print(f"Error getting transaction: {e}")
        return None
