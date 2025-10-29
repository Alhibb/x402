from solders.keypair import Keypair
import base58
import os

def create_solana_wallet():
    # Generate a new keypair (Ed25519)
    kp = Keypair()

    # Get public key as string
    public_key = str(kp.pubkey())

    # Secret key bytes (64 bytes)
    secret_key_bytes = bytes(kp)

    # Encode secret key to Base58
    private_key_base58 = base58.b58encode(secret_key_bytes).decode()

    return {
        "public_key": public_key,
        "private_key_base58": private_key_base58,
        "secret_key_bytes": secret_key_bytes
    }

if __name__ == "__main__":
    wallet = create_solana_wallet()
    print("=== New Solana Wallet ===")
    print("Public Key:", wallet["public_key"])
    print("Private Key (base58):", wallet["private_key_base58"])

    # Save to file securely
    filename = "solana_wallet.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"public_key: {wallet['public_key']}\n")
        f.write(f"private_key_base58: {wallet['private_key_base58']}\n")
    try:
        os.chmod(filename, 0o600)
    except Exception:
        pass

    print(f"\nSaved keys to {filename} (secure permissions applied if supported).")
