import os
import time
import requests
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solders.signature import Signature
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Confirmed

load_dotenv()

# ------------------ CONFIG ------------------
SERVER_URL = "http://127.0.0.1:8000/premium-data"
RPC_URL = "https://api.devnet.solana.com"
client = Client(RPC_URL)

# Load client keypair
secret_b58 = os.getenv("CLIENT_WALLET_PRIVATE_KEY_BASE58")
if not secret_b58:
    raise SystemExit("Set CLIENT_WALLET_PRIVATE_KEY_BASE58 in .env")

kp = Keypair.from_base58_string(secret_b58)
print(f"Client pubkey : {kp.pubkey()}")

bal = client.get_balance(kp.pubkey()).value / 1_000_000_000
print(f"Balance       : {bal:.9f} SOL")

# ------------------ BULLETPROOF HELPERS ------------------
def wait_for_confirmation(sig: str, timeout: int = 120) -> bool:
    """Wait for tx confirmation using string sig directly"""
    print(f"Waiting for {sig} (up to {timeout}s)...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        # 1. Try get_signature_statuses WITH FULL HISTORY
        statuses = client.get_signature_statuses(
            [sig], 
            search_transaction_history=True
        )
        status = statuses.value[0]
        
        if status and status.confirmation_status == Confirmed:
            print("CONFIRMED!")
            return True
        
        # 2. BACKUP: Direct get_transaction fetch
        try:
            tx_resp = client.get_transaction(
                sig,  # string, not Signature object
                encoding="base64",
                max_supported_transaction_version=0
            )
            if tx_resp.value:
                print("FETCHED DIRECTLY!")
                return True
        except:
            pass

        time.sleep(2)

    print("TIMEOUT - Check explorer:")
    print(f"   https://explorer.solana.com/tx/{sig}?cluster=devnet")
    return False

def ensure_receiver_exists(receiver: str):
    pubkey = Pubkey.from_string(receiver)
    resp = client.get_balance(pubkey)
    if resp.value > 0:
        print(f"Receiver funded: {resp.value / 1e9:.6f} SOL")
        return

    print("Bootstrapping receiver with 0.002 SOL...")
    bootstrap_lamports = 2_039_280
    bh = client.get_latest_blockhash().value.blockhash
    ix = transfer(
        TransferParams(
            from_pubkey=kp.pubkey(),
            to_pubkey=pubkey,
            lamports=bootstrap_lamports
        )
    )
    msg = MessageV0.try_compile(
        payer=kp.pubkey(),
        instructions=[ix],
        address_lookup_table_accounts=[],
        recent_blockhash=bh
    )
    tx = VersionedTransaction(msg, [kp])
    
    opts = TxOpts(skip_preflight=True)
    sig = client.send_raw_transaction(bytes(tx), opts=opts).value
    print(f"Bootstrap sent: {sig}")
    
    wait_for_confirmation(sig)

def send_payment(to_addr: str, lamports: int, ref: str) -> str:
    bh = client.get_latest_blockhash().value.blockhash
    ix = transfer(
        TransferParams(
            from_pubkey=kp.pubkey(),
            to_pubkey=Pubkey.from_string(to_addr),
            lamports=lamports
        )
    )
    msg = MessageV0.try_compile(
        payer=kp.pubkey(),
        instructions=[ix],
        address_lookup_table_accounts=[],
        recent_blockhash=bh
    )
    tx = VersionedTransaction(msg, [kp])
    
    opts = TxOpts(skip_preflight=True)
    sig = client.send_raw_transaction(bytes(tx), opts=opts).value
    print(f"Micropayment sent: {sig}")
    
    if not wait_for_confirmation(sig):
        raise SystemExit("Micropayment failed - check link above")
    
    return str(sig)

def main():
    s = requests.Session()

    # 1. 402
    r1 = s.get(SERVER_URL)
    if r1.status_code != 402:
        print(f"Unexpected: {r1.status_code} {r1.text}")
        return

    details = r1.json()
    print("402 Details:")
    for k, v in details.items():
        print(f"  {k}: {v}")

    # 2. Bootstrap
    ensure_receiver_exists(details["receiver"])

    # 3. Pay
    sig = send_payment(details["receiver"], details["amount_lamports"], details["reference"])

    # 4. Retry
    s.headers.update({
        "X-Payment-Signature": sig,
        "X-Payment-Reference": details["reference"]
    })
    print("\nRetrying with proof...")
    r2 = s.get(SERVER_URL)
    print(f"\nFinal: {r2.status_code}")
    print(r2.json())

if __name__ == "__main__":
    main()