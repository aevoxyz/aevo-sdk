# Aevo SDK

This repo hosts Aevo's Python SDK, which simplifies the common operations around signing and creating orders.

Please see the documentation for more details:

[REST API docs](https://docs.aevo.xyz/reference/urls)

[Websocket API docs](https://docs.aevo.xyz/reference/endpoints)

Signing and API Keys can be generated through the Aevo UI:

Signing Keys: https://app.aevo.xyz/settings or https://testnet.aevo.xyz/settings

API Keys: https://app.aevo.xyz/settings/api-keys or https://testnet.aevo.xyz/settings/api-keys

NOTE: For security purposes, signing keys automatically expire 1 week after generation

## Getting Started

It is recommended that you use a virtual environment to install the dependencies. The code has specifically been tested on Python 3.11.4.

```
virtualenv -p python3 .venv
source .venv/bin/activate
```

Then, install the dependencies for the Python SDK.

```
pip install -r requirements.txt
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

## Subscribing to realtime Websocket channels

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
await aevo.open_connection()
await aevo.subscribe_index(asset="ETH")
```

**(Authenticated) Subscribing to private trades**

```python
await aevo.open_connection()
await aevo.subscribe_fills()
```

## Websocket Order Flow

See `order_ws_example.py` for an example flow of how to create, edit and cancel an order via websocket. Due to the use of `websockets` library it is recommended that you implement your code using `asyncio` as well.

It can be tested by running `python order_ws_example.py`.

## REST API Order Flow

See `order_rest_example.py` for an example flow of how to create and cancel an order via REST API.

It can be tested by running `python order_rest_example.py`.

## Generating infinite expiry signing key

Normally signing keys generated via the UI expire after 1 week. However, you can generate a signing key that never expires by using the `generate_infinite_expiry_signing_key.py` script.

You will need to extract your private key from your wallet and paste it into the code in the section indicated before running it.

#### NOTE: Be very careful with this as anyone with your private key will have complete access to your funds. Remember to delete the key from the code straight after generating the signing key.
