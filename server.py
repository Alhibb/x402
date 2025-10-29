import os
import uuid
import time
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from solders.pubkey import Pubkey
from solders.signature import Signature
from solana.rpc.api import Client
from decimal import Decimal

load_dotenv()

SERVER_WALLET_ADDRESS = os.getenv("SERVER_WALLET_ADDRESS")
if not SERVER_WALLET_ADDRESS:
    raise ValueError("Set SERVER_WALLET_ADDRESS in .env")

SOLANA_RPC_URL = "https://api.devnet.solana.com"
PREMIUM_PRICE_USD = Decimal("0.01")
USD_TO_SOL_RATE = Decimal("0.00007") # Example rate
LAMPORTS_PER_SOL = 1_000_000_000

PREMIUM_PRICE_SOL = (PREMIUM_PRICE_USD * USD_TO_SOL_RATE).quantize(Decimal("1e-9"))
PREMIUM_PRICE_LAMPORTS = int(PREMIUM_PRICE_SOL * LAMPORTS_PER_SOL)

processed_references = set()
client = Client(SOLANA_RPC_URL)
app = FastAPI()

print(f"Server wallet : {SERVER_WALLET_ADDRESS}")
print(f"Price         : {PREMIUM_PRICE_LAMPORTS} lamports ({PREMIUM_PRICE_SOL} SOL)")

# ------------------ HELPER ------------------
def find_system_transfer(encoded_tx_with_meta):
    """Extract first system transfer from EncodedTransactionWithStatusMeta"""
    tx = encoded_tx_with_meta.transaction
    meta = encoded_tx_with_meta.meta
    if not meta:
        raise ValueError("Transaction metadata missing")

    msg = tx.message

    for ix in msg.instructions:
        # Check if it's a system program instruction
        program_id_index = ix.program_id_index
        if str(msg.account_keys[program_id_index]) != "11111111111111111111111111111111":
            continue
        
        # Check if it's a transfer instruction (2 is the instruction index for transfer)
        # Data format: instruction_index (u32) + lamports (u64)
        if ix.data[0] != 2:
            continue
            
        lamports = int.from_bytes(ix.data[4:12], "little")
        # In a transfer, the source is account 0 and destination is account 1
        dest_idx = ix.accounts[1]
        dest = msg.account_keys[dest_idx]
        return str(dest), lamports
        
    return None, 0

@app.get("/")
def root():
    return {"msg": "Free endpoint. Try /premium-data"}

@app.get("/premium-data")
async def premium_data(request: Request):
    sig_header = request.headers.get("X-Payment-Signature")
    ref_header = request.headers.get("X-Payment-Reference")

    # ----- 402: No payment -----
    if not sig_header or not ref_header:
        ref = str(uuid.uuid4())
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={
                "message": "Payment Required",
                "receiver": SERVER_WALLET_ADDRESS,
                "amount_lamports": PREMIUM_PRICE_LAMPORTS,
                "reference": ref,
                "network": "solana-devnet",
            },
        )

    # ----- Replay protection -----
    if ref_header in processed_references:
        return JSONResponse(status_code=400, content={"error": "Reference already used"})

    # ----- Verify transaction -----
    try:
        sig = Signature.from_string(sig_header.strip())
        tx_wrapper = None
        for attempt in range(1, 6):
            print(f"  [Attempt {attempt}/5] Fetching tx {sig}")
            resp = client.get_transaction(
                sig,
                encoding="base64",
                max_supported_transaction_version=0
            )
            tx_wrapper = resp.value
            if tx_wrapper:
                break
            if attempt < 5:
                time.sleep(2)
        if not tx_wrapper:
            raise ValueError("Transaction not found after 5 attempts")

        inner_tx = tx_wrapper.transaction

        if inner_tx.meta is None:
            raise ValueError("Transaction metadata is missing")
        if inner_tx.meta.err:
            raise ValueError(f"Transaction failed: {inner_tx.meta.err}")

        to_addr, lamports = find_system_transfer(inner_tx)
        
        if not to_addr:
            raise ValueError("No system transfer instruction found")

        if to_addr != SERVER_WALLET_ADDRESS:
            raise ValueError(f"Wrong receiver: {to_addr}")

        if lamports < PREMIUM_PRICE_LAMPORTS:
            raise ValueError(f"Insufficient amount: {lamports} < {PREMIUM_PRICE_LAMPORTS}")

        # ----- Success -----
        processed_references.add(ref_header)
        print(f"PAYMENT SUCCESS: {lamports} lamports → {sig}")
        return {
            "message": "Payment accepted! Here is your premium data.",
            "data": "This is the secret AI-powered insight you paid for.",
            "tx_signature": str(sig),
            "amount_received_lamports": lamports
        }

    except Exception as e:
        print(f"Verification failed: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": "Payment verification failed", "details": str(e)}
        )