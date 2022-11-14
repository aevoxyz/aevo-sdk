import json
import random
import requests
from web3 import Web3
import asyncio
import websockets
from eip712_structs import EIP712Struct, Address, Uint, Boolean, make_domain
from eth_account import Account


w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545")) # This URL doesn"t actually do anything, we just need a web3 instance

REST_MAINNET = "https://api.aevo.xyz"
REST_TESTNET = "https://api-testnet.aevo.xyz"

WS_PUBLIC_MAINNET = "wss://ws.aevo.xyz"
WS_PUBLIC_TESTNET = "wss://ws-testnet.aevo.xyz"

WS_AUTH_MAINNET = "wss://ws-auth.aevo.xyz"
WS_AUTH_TESTNET = "wss://ws-auth-testnet.aevo.xyz"

class Order(EIP712Struct):
    maker = Address()
    isBuy = Boolean()
    limitPrice = Uint(256)
    amount = Uint(256)
    salt = Uint(256)
    instrument = Uint(256)

class AevoClient:
    def __init__(self, private_key, wallet_address, api_key, env="testnet"):
        self.private_key = private_key
        self.wallet_address = wallet_address
        self.api_key = api_key
        self.private_connection = None
        self.public_connection = None

        if (env != "testnet") and (env != "mainnet"):
            raise ValueError("env must either be 'testnet' or 'mainnet'")
        self.env = env
    
    @property
    def address(self):
        return w3.eth.account.from_key(self.private_key).address
    
    @property
    def connections(self):
        return (self.public_connection, self.private_connection)

    @property
    def ws_public_uri(self):
        if self.env == "testnet":
            return WS_PUBLIC_TESTNET
        else:
            return WS_PUBLIC_MAINNET

    @property
    def ws_auth_uri(self):
        if self.env == "testnet":
            return WS_AUTH_TESTNET
        else:
            return WS_AUTH_MAINNET
    
    @property
    def rest_uri(self):
        if self.env == "testnet":
            return REST_TESTNET
        else:
            return REST_MAINNET
    
    @property
    def signing_domain(self):
        if self.env == "testnet":
            return {
                "name": "Aevo Testnet",
                "version": "1",
                "chainId": "9461"
            }
        else:
            return {
                "name": "Aevo Mainnet",
                "version": "2",
                "chainId": "1"
            }

    async def open_connection(self):
        self.public_connection = await websockets.connect(self.ws_public_uri)
        self.private_connection = await websockets.connect(self.ws_auth_uri)
    
    async def close_connection(self):
        await self.public_connection.close()
        await self.private_connection.close()
    
    async def recv_on_both_connections(self):
        pub_wait = asyncio.wait_for(self.public_connection.recv(), timeout=0.1)
        priv_wait = asyncio.wait_for(self.private_connection.recv(), timeout=0.1)
        results = await asyncio.gather(pub_wait, priv_wait, return_exceptions=True)
        results = filter(lambda r: not isinstance(r, asyncio.TimeoutError), results)
        return results
    
    async def read_messages(self):
        while True:
            messages = await self.recv_on_both_connections()
            for message in messages:
                if isinstance(message, Exception):
                    raise message
                yield message
    
    async def ping_all(self):
        for connection in self.connections:
            payload = {
                "op": "ping",
            }
            if connection is self.private_connection:
                payload.update(self.auth_payload())
            await connection.send(json.dumps(payload))
            msg = json.loads(await connection.recv())
            if msg["status"] != "ok":
                raise Exception(f"Ping failed: {msg['error']}")
    
    def format_message(self, op, data, channel=None, private=False):
        payload = {
            "op": op,
            "data": data
        }
        if private:
            payload.update(self.auth_payload())
        if channel:
            payload.update({"channel": channel})
        return json.dumps(payload)
    
    def auth_payload(self):
        return {
            "auth": {
                "acc": self.wallet_address,
                "key": self.api_key,
            }
        }
    
    def get_markets(self, asset="ETH"):
        req = requests.get(f"{self.rest_uri}/markets?asset={asset}", verify=False)
        data = req.json()
        if type(data) is dict and data.get("error"):
            raise Exception("Failed to get markets")
        return data
    
    async def subscribe_ticker(self, instrument_name):
        await self.public_connection.send(json.dumps({
            "op": "subscribe",
            "channel": "ticker",
            "data": {"instrument": instrument_name}
        }))
    
    async def subscribe_orderbook(self, instrument_name):
        await self.public_connection.send(json.dumps({
            "op": "subscribe",
            "channel": "orderbook",
            "data": {"instrument": instrument_name}
        }))

    async def subscribe_trades(self, instrument_name):
        await self.public_connection.send(json.dumps({
            "op": "subscribe",
            "channel": "trade",
            "data": {"instrument": instrument_name}
        }))
    
    async def subscribe_index(self, asset):
        await self.public_connection.send(json.dumps({
            "op": "subscribe",
            "channel": "index",
            "data": {"asset": asset}
        }))
    
    async def subscribe_orders(self):
        payload = {
            "op": "subscribe",
            "channel": "orders",
        }
        payload.update(self.auth_payload())
        await self.private_connection.send(json.dumps(payload))

    async def create_order(self, instrument_id, is_buy, limit_price, quantity):
        data = self.create_order_json(instrument_id, is_buy, limit_price, quantity)
        payload = {
            "op": "create_order",
            "data": data
        }
        payload.update(self.auth_payload())
        await self.private_connection.send(json.dumps(payload))
    
    def create_order_json(self, instrument_id, is_buy, limit_price, quantity):
        salt, signature = self.sign_order(instrument_id, is_buy, limit_price, quantity)
        return {
            "instrument_id": instrument_id,
            "maker": self.wallet_address,
            "is_buy": is_buy,
            "amount": str(int(quantity*10**6)),
            "limit_price": str(int(limit_price*10**6)),
            "salt": str(salt),
            "signature": signature
        }
    
    async def edit_order(self, order_id, instrument_id, is_buy, limit_price, quantity):
        salt, signature = self.sign_order(instrument_id, is_buy, limit_price, quantity)
        payload = {
            "op": "edit_order",
            "data": {
                "existing_order_id": order_id,
                "instrument_id": str(instrument_id),
                "maker": self.wallet_address,
                "is_buy": is_buy,
                "amount": str(int(quantity*10**6)),
                "limit_price": str(int(limit_price*10**6)),
                "salt": str(salt),
                "signature": signature
            }
        }
        payload.update(self.auth_payload())
        await self.private_connection.send(json.dumps(payload))
    
    async def cancel_order(self, order_id):
        payload = {
            "op": "cancel_order",
            "data": {
                "order_id": order_id
            }
        }
        payload.update(self.auth_payload())
        await self.private_connection.send(json.dumps(payload))
    
    def sign_order(self, instrument_id, is_buy, limit_price, quantity):
        salt = random.randint(0, 10**10) # we just need a large enough number
        decimals = 10**6

        order_struct = Order(
            maker=self.wallet_address, # The wallet"s main address
            isBuy=is_buy,
            limitPrice=int(limit_price * decimals),
            amount=int(quantity * decimals),
            salt=salt,
            instrument=instrument_id)

        domain = make_domain(**self.signing_domain)
        signable_bytes = Web3.keccak(order_struct.signable_bytes(domain=domain))
        return salt, Account._sign_hash(signable_bytes, self.private_key).signature.hex()
