import json
import random
import requests
from web3 import Web3
import asyncio
import websockets
from eip712_structs import EIP712Struct, Address, Uint, Boolean, make_domain
from eth_account import Account


w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545")) # This URL doesn't actually do anything, we just need a web3 instance

class Order(EIP712Struct):
    maker = Address()
    isBuy = Boolean()
    limitPrice = Uint(256)
    amount = Uint(256)
    salt = Uint(256)
    instrument = Uint(256)

class Client:
    def __init__(self, private_key, wallet_address, api_key):
        self.private_key = private_key
        self.wallet_address = wallet_address
        self.api_key = api_key
        self.connection = None
    
    @property
    def address(self):
        return w3.eth.account.from_key(self.private_key).address
    
    @property
    def connections(self):
        # return (self.public_connection, self.private_connection)
        return (self.public_connection,)
    
    async def open_connection(self):
        self.public_connection = await websockets.connect('wss://ws.aevo.xyz')
        # self.private_connection = await websockets.connect('ws://ws-auth.aevo.xyz')
    
    async def close_connection(self):
        await self.public_connection.close()
        # await self.private_connection.close()
    
    async def recv(self):
        return json.loads(await self.public_connection.recv())
    
    async def ping(self):
        for connection in self.connections:
            await connection.send(json.dumps({
                'op': 'ping',
            }))
            msg = json.loads(await connection.recv())
            if msg['status'] != 'ok':
                raise Exception('Ping failed')
    
    def format_message(self, op, channel, data):
        return json.dumps({
            'op': op,
            'channel': channel,
            'data': data
        })
    
    def get_markets(self, asset='ETH'):
        req = requests.get(f'https://api.aevo.xyz/markets?asset={asset}')
        data = req.json()
        if type(data) is dict and data.get('error'):
            raise Exception('Failed to get markets')
        return data
    
    async def subscribe_ticker(self, instrument_name):
        await self.public_connection.send(self.format_message('subscribe', 'ticker', {'instrument': instrument_name}))
    
    async def subscribe_orderbook(self, instrument_name):
        await self.public_connection.send(self.format_message('subscribe', 'orderbook', {'instrument': instrument_name}))

    async def subscribe_trades(self, instrument_name):
        await self.public_connection.send(self.format_message('subscribe', 'trade', {'instrument': instrument_name}))
    
    async def subscribe_index(self, asset):
        await self.public_connection.send(self.format_message('subscribe', 'index', {'asset': asset}))
    
    def sign_order(self, instrument_id, is_buy, limit_price, quantity):
        salt = random.randint(0, 10**10) # we just need a large enough number
        decimals = 10**6

        order_struct = Order(
            maker=self.wallet_address, # The wallet's main address
            isBuy=is_buy,
            limitPrice=int(limit_price * decimals),
            amount=int(quantity * decimals),
            salt=salt,
            instrument=instrument_id)

        domain = make_domain(name='Ribbon Exchange', version='1', chainId=1)
        signable_bytes = Web3.keccak(order_struct.signable_bytes(domain=domain))
        return Account._sign_hash(signable_bytes, self.private_key).signature.hex()


async def main():
    client = Client('INSERT_PRIVATE_KEY_HERE', 'INSERT_WALLET_ADDRESS_HERE', 'INSERT_API_KEY_HERE')

    await client.open_connection()
    await client.ping()
    instruments = client.get_markets()

    await asyncio.gather(*[client.subscribe_orderbook(instrument['instrument_name']) for instrument in instruments])
    await asyncio.gather(*[client.subscribe_ticker(instrument['instrument_name']) for instrument in instruments])
    await asyncio.gather(*[client.subscribe_trades(instrument['instrument_name']) for instrument in instruments])
    await client.subscribe_index(asset='ETH')

    try:
        while True:
            print(await client.recv())
    finally:
        await client.close_connection()


asyncio.run(main())
