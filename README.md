Aevo SDK
===

This repo hosts Aevo's Python SDK, which simplifies the common operations around signing and creating orders.

Please see the documentation for more details:

[REST API docs](https://aevo.readme.io/docs/reference/overview)

[Websocket API docs](https://aevo.readme.io/docs/websocket-overview)

Getting Started
---

To get started, create an AevoClient instance with your credentials.

```python
from client import AevoClient

client = AevoClient(os.environ["SIGNING_KEY"], os.environ["ACCOUNT_ADDRESS"], os.environ["API_KEY"])
instruments = client.get_markets()
print(instruments) # This should work if your client is setup right
```

`SIGNING_KEY` - The private key of the signing key, used to sign orders.

`ACCOUNT_ADDRESS` - Etheruem address of the account.

`API_KEY` - API key for the account. Used for private operations.

Subscribing to realtime Websocket channels
---

**Subscribing to orderbook updates**

```python
async def main():
    client = AevoClient(os.environ["SIGNING_KEY"], os.environ["ACCOUNT_ADDRESS"], os.environ["API_KEY"])
    await client.open_connection()
    await client.subscribe_orderbook(instrument_name="ETH-30DEC22-1500-P")

    async for msg in client.read_messages():
        print(msg)

asyncio.run(main())
```

**Subscribing to index price**

```python
async def main():
    client = AevoClient(os.environ["SIGNING_KEY"], os.environ["ACCOUNT_ADDRESS"], os.environ["API_KEY"])
    await client.open_connection()
    await client.subscribe_index(asset="ETH")

    async for msg in client.read_messages():
        print(msg)

asyncio.run(main())
```

Creating new orders
---

```python
async def main():
    client = AevoClient(os.environ["SIGNING_KEY"], os.environ["ACCOUNT_ADDRESS"], os.environ["API_KEY"])

    await client.open_connection()
    instruments = client.get_markets()

    # We pass in the instrument ID as the first parameter
    await client.create_order(instruments[0]['instrument_id'], True, 10, 100)

asyncio.run(main())
```

Cancelling an order
---

```python
async def main():
    client = AevoClient(os.environ["SIGNING_KEY"], os.environ["ACCOUNT_ADDRESS"], os.environ["API_KEY"])

    await client.open_connection()
    instruments = client.get_markets()

    await client.create_order(instruments[0]['instrument_id'], True, 10, 100)

    # Create an order and cancel instantly
    async for msg in client.read_messages():
        await client.cancel_order(msg['order_id'])
        break

asyncio.run(main())
```

