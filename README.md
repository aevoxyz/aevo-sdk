Aevo SDK
===

This repo hosts Aevo's Python SDK, which simplifies the common operations around signing and creating orders.

Please see the documentation for more details:

[REST API docs](https://docs.aevo.xyz/reference/urls)

[Websocket API docs](https://docs.aevo.xyz/reference/endpoints)

Signing and API Keys can be generated through the Aevo UI:

Signing Keys: https://app.aevo.xyz/settings or https://testnet.aevo.xyz/settings

API Keys: https://app.aevo.xyz/settings/api-keys or https://testnet.aevo.xyz/settings/api-keys

NOTE: For security purposes, signing keys automatically expire 1 week after generation 

Getting Started
---

To get started, install the dependencies for the Python SDK.

```
cd python
pip install requirements.txt
```

Next, create an AevoClient instance with your credentials.

```python
from client import AevoClient

client = AevoClient(
    signing_key="",
    wallet_address="",
    api_key="",
    api_secret="",
    env="testnet",
)
markets = aevo.get_markets("ETH")
print(markets) # This should work if your client is setup right
```

The variables that you have to pass into AevoClient are:

`signing_key` - The private key of the signing key, used to sign orders.

`wallet_address` - Ethereum address of the account.

`api_key` - API key for the account. Used for private operations.

`api_secret` - API secret for the account.

`env` - Either `testnet` or `mainnet`.

Subscribing to realtime Websocket channels
---

**Subscribing to orderbook updates**

```python
async def main():
    aevo = AevoClient(
        signing_key="",
        wallet_address="",
        api_key="",
        api_secret="",
        env="testnet",
    )

    await aevo.open_connection() # need to do this first to open wss connections
    await aevo.subscribe_ticker("ticker:ETH:PERPETUAL")

    async for msg in aevo.read_messages():
        print(msg)

if __name__ == "__main__":
    asyncio.run(main())
```

**Subscribing to index price**

```python
async def main():
    aevo = AevoClient(
        signing_key="",
        wallet_address="",
        api_key="",
        api_secret="",
        env="testnet",
    )

    await aevo.open_connection() # need to do this first to open wss connections
    await aevo.subscribe_index(asset="ETH")

    async for msg in aevo.read_messages():
        print(msg)

if __name__ == "__main__":
    asyncio.run(main())
```

Creating new orders
---

```python
async def main():
    aevo = AevoClient(
        signing_key="",
        wallet_address="",
        api_key="",
        api_secret="",
        env="testnet",
    )

    await aevo.open_connection()

    # We pass in the instrument ID as the first parameter
    # ONLY RUN THIS LINE IN TESTNET
    await aevo.create_order(1, True, 10, 100)

asyncio.run(main())
```

Cancelling an order
---

```python
async def main():
    aevo = AevoClient(
        signing_key="",
        wallet_address="",
        api_key="",
        api_secret="",
        env="testnet",
    )
    await aevo.open_connection()

    await client.create_order(1, True, 10, 100)

    # Create an order and cancel instantly
    async for msg in client.read_messages():
        await client.cancel_order(
            json.loads(msg)["data"]["orders"][0]["order_id"])
        break

asyncio.run(main())
```

