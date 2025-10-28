import os
import time
import requests
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from solders.hash import Hash
from solana.rpc.api import Client
from solana.rpc.types import TxOpts

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
SERVER_URL = "http://127.0.0.1:8000/premium-data"
SOLANA_RPC_URL = "https://api.devnet.solana.com"
LAMPORTS_PER_SOL = 1_000_000_000

# Load client wallet private key from environment variable
try:
    private_key_b58 = os.getenv("CLIENT_WALLET_PRIVATE_KEY_BASE58")
    if not private_key_b58:
        raise ValueError("CLIENT_WALLET_PRIVATE_KEY_BASE58 not found in .env file.")
    
    # Create a Keypair object from the Base58 private key string
    CLIENT_KEYPAIR = Keypair.from_base58_string(private_key_b58)

except Exception as e:
    print(f"❌ Error loading client wallet: {e}")
    print("Please ensure CLIENT_WALLET_PRIVATE_KEY_BASE58 is set correctly in your .env file.")
    exit()

# Initialize Solana RPC Client
solana_client = Client(SOLANA_RPC_URL)

def make_solana_payment(receiver_str: str, lamports: int, reference: str) -> str:
    """Creates, signs, and sends a Solana transaction."""
    print(f"\n💸 Initiating payment of {lamports} lamports to {receiver_str}...")

    # Get the latest blockhash
    blockhash_resp = solana_client.get_latest_blockhash()
    recent_blockhash = blockhash_resp.value.blockhash

    # Create transfer instruction
    receiver_pubkey = Pubkey.from_string(receiver_str)
    transfer_ix = transfer(
        TransferParams(
            from_pubkey=CLIENT_KEYPAIR.pubkey(),
            to_pubkey=receiver_pubkey,
            lamports=lamports,
        )
    )
    
    # Create transaction
    transaction = Transaction.new_signed_with_payer(
        [transfer_ix],
        CLIENT_KEYPAIR.pubkey(),
        [CLIENT_KEYPAIR],
        recent_blockhash,
    )

    # Send the transaction
    print("🚀 Sending transaction to Solana devnet...")
    tx_signature = solana_client.send_transaction(transaction, opts=TxOpts(skip_preflight=True)).value
    print(f"🖊️ Transaction signature: {tx_signature}")

    # Confirm the transaction
    print("⏳ Waiting for transaction confirmation...")
    solana_client.confirm_transaction(tx_signature, commitment="confirmed")
    print("✅ Transaction confirmed!")
    
    return str(tx_signature)

def access_premium_content():
    """Main function to handle the X402 payment flow."""
    session = requests.Session()
    headers = {}

    print("--- Step 1: Initial request to premium endpoint ---")
    try:
        response = session.get(SERVER_URL, headers=headers)

        if response.status_code == 200:
            print("✅ Access granted without payment (maybe you paid before?).")
            print("Server Response:", response.json())
            return
        
        if response.status_code != 402:
            print(f"❌ Received unexpected status code: {response.status_code}")
            print("Response Body:", response.text)
            return

        print("🚦 Received 402 Payment Required. Server demands payment.")
        payment_details = response.json()
        print("Payment Details:", payment_details)

        # --- Step 2: Make the payment ---
        receiver = payment_details["receiver"]
        amount_lamports = payment_details["amount_lamports"]
        reference = payment_details["reference"]
        
        signature = make_solana_payment(receiver, amount_lamports, reference)

        # --- Step 3: Retry the request with payment proof ---
        print("\n--- Step 3: Retrying request with payment proof ---")
        headers["X-Payment-Signature"] = signature
        headers["X-Payment-Reference"] = reference
        
        final_response = session.get(SERVER_URL, headers=headers)
        final_response.raise_for_status() # Raise an exception for bad status codes

        print("✅ Success! Access granted.")
        print("Final Server Response:", final_response.json())

    except requests.exceptions.RequestException as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    print(f"🔑 Client wallet address: {CLIENT_KEYPAIR.pubkey()}")
    balance_resp = solana_client.get_balance(CLIENT_KEYPAIR.pubkey())
    print(f"💰 Client wallet balance: {balance_resp.value / LAMPORTS_PER_SOL} SOL")
    access_premium_content()