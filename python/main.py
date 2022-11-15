import time
from email import message
import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()
from client import AevoClient


async def main():
    client = AevoClient(os.environ["SIGNING_KEY"], os.environ["ACCOUNT_ADDRESS"], os.environ["API_KEY"])

    await client.open_connection()
    instruments = client.get_markets()

    await client.subscribe_orders()

    await client.create_order(instruments[0]['instrument_id'], True, 10, 100)

    print(await client.rest_create_order(instruments[0]['instrument_id'], True, 10, 100))

    # Create an order and cancel instantly
    async for msg in client.read_messages():
        print(msg)

asyncio.run(main())
