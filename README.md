# X402 Solana Micropayments: A Blueprint for the Machine Economy

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Framework: FastAPI](https://img.shields.io/badge/framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)

This repository provides a production-ready reference implementation of the **X402 Payment Protocol**, demonstrating how to gate API access with on-chain Solana micropayments. It serves as a blueprint for developers looking to build truly decentralized, monetizable services for the next generation of the web.

The web's original specification included a `402 Payment Required` status code that went largely unused for decades. X402 revitalizes this concept, creating a standardized, machine-readable protocol for programmatic payments, perfectly suited for the emerging economy of AI agents, automated services, and decentralized applications.

---

## Table of Contents

- [The Vision: Why X402 Matters](#the-vision-why-x402-matters)
- [How It Works: The Protocol Flow](#how-it-works-the-protocol-flow)
- [Architecture Diagram](#architecture-diagram)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [1. Clone & Setup](#1-clone--setup)
  - [2. Install Dependencies](#2-install-dependencies)
  - [3. Generate Solana Wallets](#3-generate-solana-wallets)
  - [4. Fund Your Client Wallet](#4-fund-your-client-wallet)
  - [5. Configure Environment](#5-configure-environment)
- [Running the Application](#running-the-application)
- [Codebase Deep Dive](#codebase-deep-dive)
- [Future Possibilities & Extensions](#future-possibilities--extensions)

## The Vision: Why X402 Matters

Today's web monetization is built on friction. Subscriptions, user accounts, credit card forms, and platform fees create barriers for both users and developers. X402 flips this model on its head.

By embedding payment instructions directly into HTTP responses, we enable a world of **permissionless, trustless, and automated value exchange**.

**Key Use Cases Unlocked by X402:**

*   **Pay-per-Call APIs:** Charge fractions of a cent for a single API call without requiring user accounts or monthly subscriptions.
*   **AI Agent Economy:** Allow autonomous AI agents to programmatically pay for data, computation, or other services as they need them.
*   **Dynamic Content Unlocking:** Paywall an article, a video, or even a single paragraph, and allow users to pay instantly to unlock it.
*   **Automated M2M Services:** Enable IoT devices to pay each other for data streams or services in real-time.

This project uses **Solana** for its near-instant finality and extremely low transaction fees, making it the ideal ledger for the high-throughput, low-value transactions that define the micropayment economy.

## How It Works: The Protocol Flow

The protocol is an elegant, stateless dance between a client and a server, orchestrated via the HTTP protocol and verified on the blockchain.

1.  **Idempotent Challenge:** The client makes a standard `GET` request to a protected resource. The server, seeing no proof of payment, responds with a `402 Payment Required` status. This response is not an error; it is a **challenge** containing a JSON payload with the necessary payment details:
    *   `receiver`: The server's Solana wallet address.
    *   `amount_lamports`: The precise amount required.
    *   `reference`: A unique UUID to prevent replay attacks.

2.  **On-Chain Fulfillment:** The client parses the `402` response. It then constructs, signs, and broadcasts a transaction to the Solana network that perfectly matches the server's challenge.

3.  **Cryptographic Proof:** Upon network confirmation, the client receives a unique transaction signature. This signature is the **cryptographic proof of payment**.

4.  **Verification and Access:** The client retries the original `GET` request, this time including the proof in the headers:
    *   `X-Payment-Signature`: The Solana transaction signature.
    *   `X-Payment-Reference`: The unique reference from the challenge.

5.  The server extracts the signature, queries a Solana RPC node to fetch the transaction details, and rigorously verifies that the payment was sent to the correct address for the required amount. If valid, it returns a `200 OK` with the premium data.

## Architecture Diagram

```mermaid
sequenceDiagram
    participant Client as Client (e.g., Python Script, AI Agent)
    participant Server as Server (FastAPI API)
    participant Solana as Solana Blockchain (Devnet)

    Client->>+Server: 1. GET /premium-data
    Server-->>-Client: 2. HTTP 402 Payment Required <br> {receiver, amount, reference}

    Note over Client: Parses 402, constructs transaction

    Client->>+Solana: 3. sendTransaction(to: receiver, amount: lamports)
    Solana-->>-Client: 4. Transaction Confirmed (Returns Signature)

    Note over Client: Attaches signature as proof

    Client->>+Server: 5. GET /premium-data <br> Headers: {X-Payment-Signature, X-Payment-Reference}
    Server->>+Solana: 6. getTransaction(Signature)
    Solana-->>-Server: 7. Returns Confirmed Transaction Details

    Note over Server: Verifies amount & receiver against original challenge

    alt Payment Valid
        Server-->>-Client: 8. HTTP 200 OK <br> { "data": "secret insight..." }
    else Payment Invalid
        Server-->>-Client: 8. HTTP 400 Bad Request
    end
```

## Getting Started

### Prerequisites

-   Python 3.8+
-   Git

### 1. Clone & Setup

First, clone the repository and navigate into the project directory.

```bash
git clone https://github.com/Alhibb/x402.git
cd x402
```

Next, create and activate a Python virtual environment. This isolates project dependencies.

```bash
# Create the environment
python -m venv venv

# Activate it (macOS/Linux)
source venv/bin/activate

# Activate it (Windows PowerShell)
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

Install all required packages using pip.

```bash
pip install -r requirements.txt
```

### 3. Generate Solana Wallets

You need two wallets: one for the server to receive payments and one for the client to send them. The included script makes this easy.

Run the script **twice** to generate two separate keypairs.

```bash
# Generate the first wallet (for the SERVER)
python generate_solana_wallet.py

# Generate the second wallet (for the CLIENT)
python generate_solana_wallet.py
```
Each run will print a **Public Key** and a **Base58 Private Key**. Securely save these credentials for the configuration step.

### 4. Fund Your Client Wallet

Your client wallet needs Devnet SOL to make payments.

1.  Copy the **Public Key** of your **client wallet**.
2.  Go to a reliable Solana Devnet faucet, such as [**Solfaucet**](https://solfaucet.com/).
3.  Paste your client's public key and airdrop 1-2 DEV SOL.
4.  You can verify the balance on the [**Solana Explorer**](https://explorer.solana.com/?cluster=devnet) by searching for your client's public key.

### 5. Configure Environment

The project uses a `.env` file for secure key management.

First, copy the example file:

```bash
cp .env.example .env
```

Now, open the `.env` file and populate it with the credentials you generated:

```dotenv
# .env

# The public key of the wallet that will RECEIVE payments.
SERVER_WALLET_ADDRESS="<YOUR_SERVER_PUBLIC_KEY>"

# The private key (in Base58 format) of the wallet that will SEND payments.
CLIENT_WALLET_PRIVATE_KEY_BASE58="<YOUR_CLIENT_PRIVATE_KEY_BASE58>"
```

## Running the Application

The moment of truth! You'll need two separate terminal windows.

**Terminal 1: Start the Server**

Ensure your virtual environment is active and start the FastAPI server.

```bash
uvicorn server:app --reload
```
The server is now live and listening on `http://127.0.0.1:8000`.

**Terminal 2: Run the Client**

In your second terminal (with the venv activated), execute the client script.

```bash
python client.py
```

Watch the logs in both terminals. You will see the full X402 flow execute in real-time, ending with the client successfully printing the premium data.

## Codebase Deep Dive

-   `server.py`: The heart of the service. A FastAPI app with a single premium endpoint (`/premium-data`) that implements the `402` challenge and `200` verification logic.
-   `client.py`: A reference consumer that demonstrates the full client-side logic: handling the `402`, sending the payment, and retrying with proof.
-   `generate_solana_wallet.py`: A utility to create new Solana keypairs, simplifying the setup process.
-   `requirements.txt`: A list of all Python dependencies.
-   `.env`: A local, untracked file for storing your secret keys securely.

## Future Possibilities & Extensions

This reference implementation is a starting point. The X402 pattern can be extended in numerous ways:
-   **Dynamic Pricing:** The server could adjust the `amount_lamports` based on server load or data complexity.
-   **Multi-Chain Support:** The `402` response could include a list of supported blockchains, allowing the client to choose.
-   **Proxy Services:** Build a "meta-transaction" proxy where a service pays the gas fee on behalf of the user, who signs a different message.
-   **Browser Integration:** Develop a browser extension that automatically detects `402` responses and prompts the user for payment, creating a seamless web experience.