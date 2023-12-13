import secrets
from typing import TypedDict

import requests
from eth_account import Account
from eth_hash.auto import keccak as keccak_256

from eip712_structs import Address, EIP712Struct, Uint, make_domain


class Register(EIP712Struct):
    key = Address()
    expiry = Uint(256)


class SignKey(EIP712Struct):
    account = Address()


class AevoRegister(TypedDict):
    account: str
    signing_key: str
    expiry: str
    account_signature: str
    signing_key_signature: str


CONFIG = {
    "testnet": {
        "rest_url": "https://api-testnet.aevo.xyz",
        "ws_url": "wss://ws-testnet.aevo.xyz",
        "signing_domain": {
            "name": "Aevo Testnet",
            "version": "1",
            "chainId": "11155111",
        },
    },
    "mainnet": {
        "rest_url": "https://api.aevo.xyz",
        "ws_url": "wss://ws.aevo.xyz",
        "signing_domain": {
            "name": "Aevo Mainnet",
            "version": "1",
            "chainId": "1",
        },
    },
}

# NOTE: Change this to "mainnet" if you want to generate a mainnet signing key
environment = "testnet"
# NOTE: Paste your account private key here
# NOTE: BE CAREFUL WITH YOUR PRIVATE KEY, DO NOT SHARE IT WITH ANYONE
account_key = ""

domain = make_domain(**CONFIG[environment]["signing_domain"])

account = Account.from_key(account_key)
print("Account:", account.address)

signing_key = secrets.token_hex(32)
signing_key_account = Account.from_key(signing_key)

expiry = 2**256 - 1

sign_key = SignKey(account=account.address)
register = Register(key=signing_key_account.address, expiry=expiry)

sign_key_hash = keccak_256(sign_key.signable_bytes(domain=domain))
signing_key_signature = Account._sign_hash(sign_key_hash, signing_key).signature.hex()

register_hash = keccak_256(register.signable_bytes(domain=domain))
account_signature = Account._sign_hash(register_hash, account_key).signature.hex()

aevo_register: AevoRegister = {
    "account": account.address,
    "signing_key": signing_key_account.address,
    "expiry": str(expiry),
    "account_signature": account_signature,
    "signing_key_signature": signing_key_signature,
}

print(aevo_register)

r = requests.post(f"{CONFIG[environment]['rest_url']}/register", json=aevo_register)
print(r)
j = r.json()

print(j)

if "error" in j:
    print("\n\nError:", j["error"])
else:
    print(f"\n\nInfinite expiry signing key generated for: {account.address}")
    print(f"Signing Key (Use this): {signing_key}")
