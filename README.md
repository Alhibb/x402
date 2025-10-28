# X402 Payment Protocol with Python, FastAPI, and Solana Devnet

This project provides a complete, working example of the X402 payment protocol implemented with a Python backend and the Solana devnet. It has been configured to use a user-friendly **Base58 private key** for the client wallet.

It contains:
1.  **A Server (`server.py`)**: A FastAPI application that serves a premium API endpoint. Access is denied with a `402 Payment Required` error unless a valid Solana transaction is provided as proof of payment.
2.  **A Client (`client.py`)**: A Python script that attempts to access the premium endpoint, handles the `402` error, creates, signs, and sends a real transaction on the Solana devnet, and then retries the request with the transaction signature to gain access.

## How It Works

1.  The client requests data from the `/premium-data` endpoint on the server.
2.  The server sees that the request lacks a payment proof and responds with a `402 Payment Required` status. The response body contains the `price`, the `receiver`'s Solana address, and a unique `memo` (reference) for the transaction.
3.  The client receives the `402` response, parses the payment details, and uses the Solana Python SDK to create a transaction.
4.  The client signs the transaction with its **Base58 private key** and sends it to the Solana devnet.
5.  Upon successful transaction confirmation, the client retries the original API request, this time adding the transaction signature to the `X-Payment-Signature` header.
6.  The server receives the new request, extracts the signature, and verifies it on the Solana devnet to ensure it's a valid payment for the correct amount and memo.
7.  If verification is successful, the server grants access and returns the premium data with a `200 OK` status.

## Prerequisites

*   Python 3.8+
*   The [Solana CLI Tool Suite](https://docs.solana.com/cli/install-solana-cli-tools) installed on your machine. This is needed to easily create a devnet wallet and fund it.

## Step-by-Step Setup and Execution

### 1. Create a Project Directory

Create a folder for your project and navigate into it.

```bash
mkdir x402-solana-py
cd x402-solana-py
```

### 2. Create the Project Files

Create the files listed in the sections below (`README.md`, `requirements.txt`, `server.py`, `client.py`, `.env.example`) inside this directory.

### 3. Set Up a Python Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

```bash
# Create a virtual environment
python -m venv venv

# Activate it (on macOS/Linux)
source venv/bin/activate

# Or on Windows
.\venv\Scripts\activate
```

### 4. Install Dependencies

Install all the required Python packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 5. Generate and Fund Your Solana Devnet Wallets

You need two wallets: one for the **server** (to receive funds) and one for the **client** (to send funds).

**A. Generate the Wallets:**

Open your terminal and run the following commands to create two keypair files.

```bash
# Create a wallet for the server
solana-keygen new --outfile ./server-wallet.json

# Create a wallet for the client
solana-keygen new --outfile ./client-wallet.json
```
These commands will create `server-wallet.json` and `client-wallet.json` files.

**B. Fund the Client Wallet with Devnet SOL:**

You need "test" SOL to make payments. Get the client's public key (address) first:

```bash
solana-keygen pubkey ./client-wallet.json
```

Copy the output address. Now, airdrop 2 devnet SOL to it.

```bash
# Replace YOUR_CLIENT_PUBLIC_KEY with the address you just copied
solana airdrop 2 YOUR_CLIENT_PUBLIC_KEY --url https://api.devnet.solana.com
```
You should see a success message with the transaction signature.

### 6. Configure Environment Variables

This project uses a `.env` file to securely manage your secret keys.

**A. Create the `.env` file:**

Copy the example file to a new `.env` file.

```bash
cp .env.example .env
```

**B. Edit the `.env` file:**

Now, open the `.env` file and fill in the required values.

*   `SERVER_WALLET_ADDRESS`: Get this by running `solana-keygen pubkey ./server-wallet.json`.
*   `CLIENT_WALLET_PRIVATE_KEY_BASE58`: **This is the important change.** Get your client's secret key in Base58 format by running:
    ```bash
    solana-keygen display ./client-wallet.json
    ```
    This command will output your Public Key and your **Private Key (in Base58 format)**. Copy the private key string.

Your `.env` file should look like this:

```
SERVER_WALLET_ADDRESS="7q...server...pubkey...here"
CLIENT_WALLET_PRIVATE_KEY_BASE58="2z...your...long...base58...private...key...string...here"
```

### 7. Run the Application

Now you are ready to run the server and client.

**A. Start the Server:**

Open a terminal window, activate the virtual environment, and run:

```bash
uvicorn server:app --reload```
The server is now running and listening for requests on `http://127.0.0.1:8000`.

**B. Run the Client:**

Open a **second terminal window**, activate the virtual environment, and run:

```bash
python client.py
```

You will see the client's output as it performs the entire X402 payment flow, resulting in successful access to the premium data.

## Conclusion
