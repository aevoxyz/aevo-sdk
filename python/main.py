from email import message
import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()
from client import Client

async def main():
    client = Client(os.environ["SIGNING_KEY"], os.environ["ACCOUNT_ADDRESS"], os.environ["API_KEY"])

    await client.open_connection()
    await client.ping_all()
    instruments = client.get_markets()

    await client.subscribe_orders()
    await asyncio.gather(*[client.subscribe_orderbook(instrument["instrument_name"]) for instrument in instruments])
    await asyncio.gather(*[client.subscribe_ticker(instrument["instrument_name"]) for instrument in instruments])
    await asyncio.gather(*[client.subscribe_trades(instrument["instrument_name"]) for instrument in instruments])
    await client.subscribe_index(asset="ETH")

    try:
        async for msg in client.read_messages():
            print(msg)
    finally:
        await client.close_connection()


asyncio.run(main())
