import os
import uuid
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from solders.pubkey import Pubkey
from solders.hash import Hash
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from decimal import Decimal

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
SERVER_WALLET_ADDRESS = os.getenv("SERVER_WALLET_ADDRESS")
SOLANA_RPC_URL = "https://api.devnet.solana.com"
PREMIUM_DATA_PRICE_USD = Decimal("0.01")  # Price in USD
# For simplicity, we'll use a fixed SOL price. In a real app, you'd fetch this from an oracle.
USD_TO_SOL_RATE = Decimal("0.00007") # Example rate: 1 USD = 0.00007 SOL
PREMIUM_DATA_PRICE_SOL = (PREMIUM_DATA_PRICE_USD * USD_TO_SOL_RATE).quantize(Decimal('1e-9'))
LAMPORTS_PER_SOL = 1_000_000_000
PREMIUM_DATA_PRICE_LAMPORTS = int(PREMIUM_DATA_PRICE_SOL * LAMPORTS_PER_SOL)

# In-memory store for payment references to prevent replay attacks
# In a production app, use a database like Redis or PostgreSQL.
processed_references = set()

# Initialize FastAPI app
app = FastAPI()

# Initialize Solana RPC Client
solana_client = Client(SOLANA_RPC_URL)

print(f"✅ Server configured to receive payments at: {SERVER_WALLET_ADDRESS}")
print(f"💰 Price for /premium-data set to {PREMIUM_DATA_PRICE_SOL} SOL ({PREMIUM_DATA_PRICE_LAMPORTS} Lamports)")

@app.get("/premium-data")
async def get_premium_data(request: Request):
    """
    This endpoint is protected. It requires a valid Solana transaction signature
    in the 'X-Payment-Signature' header for access.
    """
    payment_signature = request.headers.get("X-Payment-Signature")
    payment_reference = request.headers.get("X-Payment-Reference")

    # --- Step 1: Check if payment proof is provided ---
    if not payment_signature or not payment_reference:
        # No payment proof, so demand payment with a 402 response.
        new_reference = str(uuid.uuid4()) # Generate a unique reference for this transaction attempt
        
        payment_details = {
            "message": "Payment Required",
            "receiver": SERVER_WALLET_ADDRESS,
            "amount_lamports": PREMIUM_DATA_PRICE_LAMPORTS,
            "reference": new_reference,
            "network": "solana-devnet"
        }
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content=payment_details
        )

    # --- Step 2: Verify the provided payment proof ---
    print(f"\n🔎 Received payment proof. Verifying signature: {payment_signature}")

    # Prevent replay attacks by checking if this reference has been used
    if payment_reference in processed_references:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Payment reference has already been used."}
        )

    try:
        # Fetch the transaction from the Solana devnet
        tx_hash = Hash.from_string(payment_signature)
        response = solana_client.get_transaction(tx_hash, max_supported_transaction_version=0)
        
        tx_info = response.value
        if not tx_info:
            raise ValueError("Transaction not found.")

        tx_details = tx_info.transaction
        meta = tx_info.meta

        # --- Verification Checks ---
        # 1. Check for transaction error
        if meta.err:
            raise ValueError("Transaction failed on-chain.")
            
        # 2. Find the correct transfer instruction
        transfer_instruction = None
        for instruction in tx_details.message.instructions:
             # This is a simplistic check. A real app would parse instruction data more robustly.
             # We are looking for a simple SystemProgram.transfer
            if len(instruction.accounts) >= 2 and instruction.data == b'':
                # This is likely the transfer we care about.
                 transfer_instruction = instruction
                 break
        
        if not transfer_instruction:
            raise ValueError("No valid transfer instruction found in transaction.")

        # 3. Verify amount, receiver, and reference (memo)
        receiver_account_index = 1 # In a simple transfer, the 2nd account is the destination
        receiver_pubkey = tx_details.message.account_keys[receiver_account_index]
        
        lamports_transferred = meta.post_balances[receiver_account_index] - meta.pre_balances[receiver_account_index]
        
        if str(receiver_pubkey) != SERVER_WALLET_ADDRESS:
            raise ValueError("Payment sent to the wrong address.")
        if lamports_transferred < PREMIUM_DATA_PRICE_LAMPORTS:
            raise ValueError("Incorrect payment amount.")
        # In a real app, you'd verify the memo instruction matches the reference

        print(f"✅ Verification successful!")
        
        # Mark reference as used and grant access
        processed_references.add(payment_reference)
        
        return {
            "message": "Access granted! Thank you for your payment.",
            "data": "This is the secret information you paid for.",
            "tx_signature": payment_signature
        }

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Payment verification failed.", "details": str(e)}
        )

@app.get("/")
def read_root():
    return {"message": "This is a free endpoint. Try accessing /premium-data"}