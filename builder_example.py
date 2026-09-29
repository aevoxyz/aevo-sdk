"""Builder Codes example: approve a builder, then place a tiny IOC order with
builder attribution.

DRY-RUN by default: it signs everything and prints the payloads, but sends
nothing except public reads (instrument, orderbook). Set
SEND=1 to actually approve and place the order.

Environment (defaults in brackets):
    AEVO_ENV                [testnet]  testnet or mainnet
    AEVO_WALLET_PRIVATE_KEY            wallet private key (signs the approval)
    AEVO_WALLET_ADDRESS                [derived from the wallet key]
    AEVO_SIGNING_KEY                   [wallet key] key used to sign orders
    AEVO_API_KEY / AEVO_API_SECRET     required when SEND=1
    BUILDER_ID                         e.g. builder_0123456789abcdef
    MAX_FEE_BPS             [5]        max fee the user approves, in bps
    BUILDER_FEE_BPS         [3]        fee charged on this order, in bps
    INSTRUMENT              [ETH-PERP]
    SIDE                    [buy]      buy or sell
    AMOUNT                  [0.01]
    SLIPPAGE                [0.01]     fraction crossed past the top of book
    SEND                    [0]        1 to send the approval and the order
"""

import json
import os
from decimal import Decimal

from eth_account import Account

from aevo import AevoClient, validate_builder_id


def env(name, default=None):
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise SystemExit(f"{name} is required")
    return value


def main():
    send = os.environ.get("SEND") == "1"
    wallet_key = env("AEVO_WALLET_PRIVATE_KEY")
    wallet_address = os.environ.get("AEVO_WALLET_ADDRESS") or Account.from_key(
        wallet_key
    ).address
    aevo = AevoClient(
        signing_key=os.environ.get("AEVO_SIGNING_KEY") or wallet_key,
        wallet_address=wallet_address,
        wallet_private_key=wallet_key,
        api_key=env("AEVO_API_KEY") if send else os.environ.get("AEVO_API_KEY", ""),
        api_secret=env("AEVO_API_SECRET")
        if send
        else os.environ.get("AEVO_API_SECRET", ""),
        env=os.environ.get("AEVO_ENV", "testnet"),
    )

    builder_id = validate_builder_id(env("BUILDER_ID"))
    max_fee_bps = os.environ.get("MAX_FEE_BPS", "5")
    builder_fee_bps = os.environ.get("BUILDER_FEE_BPS", "3")
    instrument = os.environ.get("INSTRUMENT", "ETH-PERP")
    is_buy = os.environ.get("SIDE", "buy").lower() == "buy"
    amount = Decimal(os.environ.get("AMOUNT", "0.01"))
    slippage = Decimal(os.environ.get("SLIPPAGE", "0.01"))

    print(f"env={aevo.env} wallet={wallet_address} builder={builder_id} send={send}")

    # 1. Approval, signed by the WALLET key.
    approval, approval_hash = aevo.create_approve_builder_json(
        builder_id, max_fee_bps=max_fee_bps
    )
    print("approve payload:", json.dumps(approval, indent=2))
    if send:
        print(
            "approve response:",
            aevo.client.post(
                f"{aevo.rest_url}/builder/approve",
                json=approval,
                headers=aevo.rest_headers,
            ).json(),
        )

    # 2. Tiny IOC order that crosses the top of book, with builder attribution.
    inst = aevo.client.get(f"{aevo.rest_url}/instrument/{instrument}").json()
    book = aevo.client.get(
        f"{aevo.rest_url}/orderbook", params={"instrument_name": instrument}
    ).json()
    levels = book["asks"] if is_buy else book["bids"]
    if not levels:
        raise SystemExit(f"no resting liquidity on {instrument} to fill against")
    top = Decimal(levels[0][0])
    price = (top * (1 + slippage if is_buy else 1 - slippage)).quantize(
        Decimal("0.01")
    )

    order, order_id = aevo.create_order_rest_json(
        int(inst["instrument_id"]),
        is_buy,
        float(price),
        float(amount),
        post_only=False,
        builder=builder_id,
        builder_fee_bps=builder_fee_bps,
    )
    order["time_in_force"] = "IOC"  # not part of the signature
    print(f"expected order_id: {order_id}")
    print("order payload:", json.dumps(order, indent=2))
    if not send:
        print("DRY-RUN: nothing sent. Set SEND=1 to approve and place the order.")
        return

    print(
        "order response:",
        aevo.client.post(
            f"{aevo.rest_url}/orders", json=order, headers=aevo.rest_headers
        ).json(),
    )


if __name__ == "__main__":
    main()
