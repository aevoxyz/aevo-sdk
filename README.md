# Aevo SDK

This repo hosts Aevo's Python SDK, which simplifies the common operations around signing and creating orders.

Please see the documentation for more details:

[REST API docs](https://api-docs.aevo.xyz/reference/urls)

[Websocket API docs](https://api-docs.aevo.xyz/reference/endpoints)

Signing and API Keys can be generated [through the Aevo UI](https://api-docs.aevo.xyz/reference/api-key-setup-via-ui):

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

## Builder Codes

Builder Codes let an app (a "builder") attach a builder fee to its users' perpetual and option orders once the user has approved that builder. The builder fee is separate from the Aevo fee. It is debited from the user in USDC and credited to the builder's fee account. See `builder_example.py` for a full flow. It is dry-run by default and only sends when `SEND=1` is set.

A builder is identified only by its `builder_id` (`builder_<16 hex>`). Aevo generates it when the builder registers, builders never choose it, and it is the value that gets signed. SDK methods that take `builder` expect a `builder_id` and raise `ValueError` for anything else.

### Fee units

Rates are decimal fractions with at most 6 decimals: `0.0005` is 5 bps. The API takes them as decimal strings (`"0.0005"`), and EIP-712 signs the raw 6-decimal integer (`500`). Every fee argument has a `*_bps` form and a `*_rate` form. Pass exactly one of them. Floats are rejected, so pass a `str`, `int` or `Decimal`.

```python
from aevo import bps_to_rate, rate_to_raw

bps_to_rate(5)         # "0.0005"
rate_to_raw("0.0005")  # 500
```

Read the protocol caps before choosing fees. An approval above `max_fee_rate_perps` is rejected. An order fee above `max_fee_rate_perps` (perpetuals) or `max_fee_rate_options` (options) is rejected. A `null` cap means builder fees are disabled for that instrument type:

```python
aevo.get_builder_config()
# {"max_fee_rate_perps": "0.0005", "min_create_balance": "100",
#  "max_fee_rate_options": "0.0003", "option_premium_cap": "0.05"}
```

### Registration (builder)

Any account can register one builder for itself, using its own API key. Registration needs a USDC balance of at least `min_create_balance`. If that value is `null`, self-service registration is disabled.

```python
aevo.register_builder(name="Copilot")
# {"success": true, "builder_id": "builder_0123456789abcdef"}
aevo.get_builder("builder_0123456789abcdef")  # public profile: builder_id, name, status
```

Share the returned `builder_id` with your users. It is what they approve and what your orders carry.

### Approval (user)

The user approves a builder once, up to a maximum fee rate. The approval is signed with the wallet key, so `wallet_private_key` must be set, and a signing key is not accepted. The nonce is the current time in unix milliseconds; the server accepts values at most 5 minutes old and at most 30 seconds in the future, so do not future-date it.

```python
aevo = AevoClient(
    signing_key=os.environ["AEVO_SIGNING_KEY"],
    wallet_address=os.environ["AEVO_WALLET_ADDRESS"],
    wallet_private_key=os.environ["AEVO_WALLET_PRIVATE_KEY"],
    api_key=os.environ["AEVO_API_KEY"],
    api_secret=os.environ["AEVO_API_SECRET"],
    env="testnet",
)
builder_id = "builder_0123456789abcdef"
aevo.approve_builder(builder_id, max_fee_bps=5)  # POST /builder/approve
aevo.get_builder_approvals()                     # GET /account/builder-approvals
aevo.revoke_builder(builder_id)                  # POST /builder/revoke
```

### Attribution on orders

Pass `builder` and one of `builder_fee_bps` or `builder_fee_rate` to `rest_create_order`, `rest_create_market_order` or the websocket `create_order`. You can also pass them to `create_order_rest_json` or `create_order_ws_json`. The order is then signed with the builder `Order` EIP-712 type, which adds `builderId` (string) and `builderFeeRate` (uint256, raw 6-decimal) after `timestamp`, and the payload includes `builder_id` and `builder_fee_rate`. Without `builder`, orders are signed and sent exactly as before.

```python
aevo.rest_create_order(
    instrument_id=2054,
    is_buy=True,
    limit_price=1200,
    quantity=0.01,
    post_only=False,
    builder="builder_0123456789abcdef",
    builder_fee_bps=3,
)
```

The order fee must be at or below both the user's approved max and the protocol cap. Builder attribution applies to signed perpetual and option orders; signing is identical for both.

**Options:** the builder fee on an option fill is `min(builder_fee_rate × index price × contracts, option_premium_cap × premium × contracts)`, the same shape as Aevo's own option fee. The rate must also be at or below the options cap. Read both limits from `get_builder_config()`, as `max_fee_rate_options` and `option_premium_cap`. Builder fees on options are disabled while either is `null`.

### Error codes

| Code | Meaning |
| --- | --- |
| `BUILDER_NOT_FOUND` | Unknown builder, or the report caller is not a builder fee account |
| `BUILDER_NOT_ACTIVE` | The builder is suspended or disabled |
| `BUILDER_NOT_APPROVED` | The user has not approved this builder |
| `BUILDER_FEE_EXCEEDS_USER_LIMIT` | The order fee is above the user's approved max |
| `BUILDER_FEE_EXCEEDS_AEVO_LIMIT` | The fee is above the protocol cap, or the cap is unset |
| `BUILDER_INVALID_FEE_RATE` | The rate is malformed |
| `BUILDER_INVALID_SIGNATURE`, `BUILDER_INVALID_NONCE` | The approval signature is invalid, or the nonce was replayed |
| `BUILDER_NOT_SUPPORTED` | Builder fields were sent on an unsupported path |
| `BUILDER_INVALID_ID` | The builder id is malformed |
| `BUILDER_INVALID_NAME` | The registration name was rejected |
| `BUILDER_ALREADY_EXISTS` | The account already owns a builder |
| `BUILDER_CURSOR_WITH_OFFSET` | Reporting pagination sent both `cursor` and `offset` |
| `BUILDER_SELF_SERVICE_DISABLED`, `BUILDER_INSUFFICIENT_BALANCE` | Registration is disabled, or the USDC balance is below `min_create_balance` |
| `INVALID_PERIOD`, `CSV_RANGE_TOO_LARGE` | The reporting window is invalid, or the window is too large for the CSV export (50,000 rows max) |

### Reporting (builder)

Reporting uses the builder fee account's own API key, and the builder is derived from that key. Pick a window with either `period` (`24h`, `7d`, `30d` or `90d`) or `start_time` and `end_time` in unix nanoseconds, and don't combine the two.

`/builder/users`, `/builder/fills` and `/builder/markets` accept numbered pagination with `limit` and `offset`, where `offset` is the number of rows to skip. `limit` defaults to 50 and is capped at 200. Paginated responses include `count` as a string total before pagination. `/builder/users` and `/builder/fills` also support cursor pagination with `next_cursor`; offset pages do not include `next_cursor`, and you should not send both `cursor` and `offset`. `/builder/markets` returns every market when `limit` and `offset` are both omitted.

```python
aevo.get_builder_stats(period="30d")
aevo.get_builder_markets(start_time=start_ns, end_time=end_ns, limit=200, offset=0)
aevo.get_builder_users(period="7d", limit=50, cursor=None)  # paginate with next_cursor
aevo.get_builder_users(period="7d", limit=50, offset=100)   # numbered page
aevo.get_builder_fills(start_time=start_ns, end_time=end_ns, instrument="ETH-PERP", limit=200, offset=0)
aevo.download_builder_fills_csv("fills.csv", start_time=start_ns, end_time=end_ns)
```

### Read-only API keys

All reporting endpoints (`/builder/stats`, `/builder/markets`, `/builder/users` and `/builder/fills`, including CSV) and `get_builder_approvals` are GET requests, so a read-only API key works for them. A dashboard or accounting job should use one. Registration, approve, revoke and orders need a key that can trade.

## Generating infinite expiry signing key

Normally signing keys generated via the UI expire after 1 week. However, you can generate a signing key that never expires by using the `generate_infinite_expiry_signing_key.py` script.

You will need to extract your private key from your wallet and paste it into the code in the section indicated before running it.

#### NOTE: Be very careful with this as anyone with your private key will have complete access to your funds. Remember to delete the key from the code straight after generating the signing key.
