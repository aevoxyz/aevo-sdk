"""Builder Codes tests.

The hash vectors below were produced by the Aevo backend's own EIP-712 code
(pkg/signing.HashApproveBuilderDomain and
pkg/signing.HashMessageDomain(orders.SignedOrderEIP712Type /
orders.BuilderSignedOrderEIP712Type, "Order", ...)) for the exact inputs used
here, so these tests pin the SDK to what the exchange verifies.
"""

from decimal import Decimal

import pytest
from eth_account import Account
from hexbytes import HexBytes

import aevo
from aevo import AevoClient, bps_to_rate, rate_to_raw, validate_builder_id

# Public, well-known test key (web3.py docs). Never holds funds.
TEST_KEY = "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"
TEST_ADDRESS = "0x2c7536E3605D9C16a7a3D7b1898e529396a65c23"

BUILDER_ID = "builder_0123456789abcdef"
SALT = 123456789
TIMESTAMP = 1700000000  # order timestamp, unix seconds
NONCE_MS = 1700000000000  # approval nonce, unix milliseconds

# Vectors from the Go backend (testnet domain unless noted).
GO_APPROVE_HASH = "0x47c0c6b9aa266d3eb96234ed0cd8ec81acce0dbded5bb39397b13785972c5ddc"
GO_ORDER_HASH = "0x9a7312065e781a4eb70483a84317bb2a37cf98591a875be80f21eaa7d90f9379"
GO_BUILDER_ORDER_HASH = (
    "0x5cfbfdf144d2b228428aa33efbbd4a1b23d8b1f2e66d47d8d2a8a3ed5d7fb966"
)
GO_BUILDER_ORDER_HASH_MAINNET = (
    "0x51a8c2407a1d08dddc30e1e2780adddf737e4e6867ea790e74dcc9670883bc8e"
)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, content=b""):
        self.status_code = status_code
        self._json = json_data
        self.content = content
        self.text = content.decode() if content else str(json_data)

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class FakeClient:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def _respond(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.get((method, url), FakeResponse(200, {"success": True}))

    def get(self, url, **kwargs):
        return self._respond("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._respond("POST", url, **kwargs)


@pytest.fixture
def client(monkeypatch):
    c = AevoClient(
        signing_key=TEST_KEY,
        wallet_address=TEST_ADDRESS,
        wallet_private_key=TEST_KEY,
        api_key="key",
        api_secret="secret",
        env="testnet",
    )
    c.client = FakeClient()
    monkeypatch.setattr(aevo.random, "randint", lambda a, b: SALT)
    monkeypatch.setattr(aevo.time, "time", lambda: TIMESTAMP)
    monkeypatch.setattr(aevo.time, "time_ns", lambda: NONCE_MS * 1_000_000)
    return c


def recovers_to(hash_hex, signature):
    return Account._recover_hash(HexBytes(hash_hex), signature=HexBytes(signature))


# Hash parity with the backend


def test_approve_builder_hash_matches_backend(client):
    signature, approval_hash = client.sign_approve_builder(BUILDER_ID, "0.0005", NONCE_MS)
    assert approval_hash == GO_APPROVE_HASH
    assert recovers_to(approval_hash, signature) == TEST_ADDRESS


def test_builder_order_hash_matches_backend(client):
    salt, signature, order_id = client.sign_order(
        instrument_id=2054,
        is_buy=True,
        limit_price=1700,
        quantity=0.01,
        timestamp=TIMESTAMP,
        builder_id=BUILDER_ID,
        builder_fee_rate="0.0003",
    )
    assert salt == SALT
    assert order_id == GO_BUILDER_ORDER_HASH
    assert recovers_to(order_id, signature) == TEST_ADDRESS


def test_builder_order_hash_matches_backend_mainnet(client):
    client.env = "mainnet"
    _, _, order_id = client.sign_order(
        instrument_id=2054,
        is_buy=True,
        limit_price=1700,
        quantity=0.01,
        timestamp=TIMESTAMP,
        builder_id=BUILDER_ID,
        builder_fee_rate="0.0003",
    )
    assert order_id == GO_BUILDER_ORDER_HASH_MAINNET


def test_non_builder_order_hash_unchanged(client):
    _, _, order_id = client.sign_order(
        instrument_id=2054,
        is_buy=True,
        limit_price=1700,
        quantity=0.01,
        timestamp=TIMESTAMP,
    )
    assert order_id == GO_ORDER_HASH
    assert order_id != GO_BUILDER_ORDER_HASH


# Order payloads


def test_rest_order_without_builder_is_unchanged(client):
    payload, order_id = client.create_order_rest_json(2054, True, 1700, 0.01)
    assert order_id == GO_ORDER_HASH
    assert payload == {
        "maker": TEST_ADDRESS,
        "is_buy": True,
        "instrument": 2054,
        "limit_price": "1700000000",
        "amount": "10000",
        "salt": str(SALT),
        "signature": payload["signature"],
        "post_only": True,
        "reduce_only": False,
        "close_position": False,
        "timestamp": TIMESTAMP,
    }
    assert client.client.calls == []


def test_ws_order_without_builder_is_unchanged(client):
    payload, order_id = client.create_order_ws_json(2054, True, 1700, 0.01)
    assert order_id == GO_ORDER_HASH
    assert "builder_id" not in payload and "builder_fee_rate" not in payload


@pytest.mark.parametrize("kwargs", [{"builder_fee_bps": 3}, {"builder_fee_rate": "0.0003"}])
def test_rest_order_with_builder(client, kwargs):
    payload, order_id = client.create_order_rest_json(
        2054, True, 1700, 0.01, post_only=False, builder=BUILDER_ID, **kwargs
    )
    assert order_id == GO_BUILDER_ORDER_HASH
    assert payload["builder_id"] == BUILDER_ID
    assert payload["builder_fee_rate"] == "0.0003"
    assert recovers_to(order_id, payload["signature"]) == TEST_ADDRESS


def test_ws_order_with_builder(client):
    payload, order_id = client.create_order_ws_json(
        2054, True, 1700, 0.01, builder=BUILDER_ID, builder_fee_bps=3
    )
    assert order_id == GO_BUILDER_ORDER_HASH
    assert payload["builder_id"] == BUILDER_ID
    assert payload["builder_fee_rate"] == "0.0003"
    assert client.client.calls == []


def test_order_builder_argument_validation(client):
    with pytest.raises(ValueError, match="require builder"):
        client.create_order_rest_json(2054, True, 1700, 0.01, builder_fee_bps=3)
    with pytest.raises(ValueError, match="is required"):
        client.create_order_rest_json(2054, True, 1700, 0.01, builder=BUILDER_ID)
    with pytest.raises(ValueError, match="not both"):
        client.create_order_rest_json(
            2054, True, 1700, 0.01, builder=BUILDER_ID, builder_fee_bps=3,
            builder_fee_rate="0.0003",
        )


# Units


@pytest.mark.parametrize(
    "bps,rate",
    [(5, "0.0005"), ("5", "0.0005"), (10, "0.001"), ("2.5", "0.00025"),
     (Decimal("0.01"), "0.000001"), (0, "0"), (10000, "1")],
)
def test_bps_to_rate(bps, rate):
    assert bps_to_rate(bps) == rate


@pytest.mark.parametrize(
    "rate,raw",
    [("0.0005", 500), ("0.0003", 300), ("0.000001", 1), ("0", 0), ("1", 1000000),
     ("0.00050", 500), (Decimal("0.001"), 1000)],
)
def test_rate_to_raw(rate, raw):
    assert rate_to_raw(rate) == raw


@pytest.mark.parametrize("bad", ["0.0000001", "-0.0005", "1e-4", "", " 0.1", "abc"])
def test_rate_to_raw_rejects_invalid(bad):
    with pytest.raises(ValueError):
        rate_to_raw(bad)


def test_bps_to_rate_rejects_more_than_six_decimals():
    with pytest.raises(ValueError):
        bps_to_rate("0.001")


@pytest.mark.parametrize("bad", [0.0005, True])
def test_floats_are_rejected(bad):
    with pytest.raises(TypeError):
        rate_to_raw(bad)
    with pytest.raises(TypeError):
        bps_to_rate(bad)


# Builder id validation


def test_validate_builder_id_accepts_well_formed_id():
    assert validate_builder_id(BUILDER_ID) == BUILDER_ID


def test_validate_builder_id_rejects_none():
    # On order methods builder=None means "no builder"; see
    # test_order_builder_argument_validation.
    with pytest.raises(ValueError, match="builder_id"):
        validate_builder_id(None)


@pytest.mark.parametrize(
    "bad",
    ["copilot", "", 123, "builder_0123456789ABCDEF", "builder_0123456789abcde",
     "builder_0123456789abcdef0", " builder_0123456789abcdef", "builder_0123456789abcdeg"],
)
def test_builder_arguments_reject_anything_but_a_builder_id(client, bad):
    with pytest.raises(ValueError, match="builder_id"):
        validate_builder_id(bad)
    with pytest.raises(ValueError, match="builder_id"):
        client.create_order_rest_json(2054, True, 1700, 0.01, builder=bad, builder_fee_bps=3)
    with pytest.raises(ValueError, match="builder_id"):
        client.create_order_ws_json(2054, True, 1700, 0.01, builder=bad, builder_fee_bps=3)
    with pytest.raises(ValueError, match="builder_id"):
        client.approve_builder(bad, max_fee_bps=5)
    with pytest.raises(ValueError, match="builder_id"):
        client.revoke_builder(bad)
    with pytest.raises(ValueError, match="builder_id"):
        client.get_builder(bad)
    assert client.client.calls == []


# Approval / revoke


def test_approve_builder(client):
    client.approve_builder(BUILDER_ID, max_fee_bps=5)
    assert len(client.client.calls) == 1
    method, url, kwargs = client.client.calls[-1]
    assert (method, url) == ("POST", "https://api-testnet.aevo.xyz/builder/approve")
    body = kwargs["json"]
    assert body["builder_id"] == BUILDER_ID
    assert body["max_fee_rate"] == "0.0005"
    assert body["nonce"] == str(NONCE_MS)
    assert recovers_to(GO_APPROVE_HASH, body["signature"]) == TEST_ADDRESS
    assert kwargs["headers"]["AEVO-KEY"] == "key"


def test_approve_builder_requires_wallet_key(client):
    client.wallet_private_key = ""
    with pytest.raises(ValueError, match="wallet_private_key"):
        client.approve_builder(BUILDER_ID, max_fee_rate="0.0005")


def test_approve_builder_rejects_key_for_other_wallet(client):
    client.wallet_address = "0x0000000000000000000000000000000000000001"
    with pytest.raises(ValueError, match="not wallet_address"):
        client.approve_builder(BUILDER_ID, max_fee_rate="0.0005")


def test_revoke_builder(client):
    client.revoke_builder(BUILDER_ID)
    method, url, kwargs = client.client.calls[-1]
    assert (method, url) == ("POST", "https://api-testnet.aevo.xyz/builder/revoke")
    assert kwargs["json"] == {"builder_id": BUILDER_ID}


# Endpoint mapping


def test_register_and_public_reads(client):
    client.register_builder("Copilot")
    client.get_builder(BUILDER_ID)
    client.get_builder_config()
    client.get_builder_approvals()
    calls = [(m, u) for m, u, _ in client.client.calls]
    assert calls == [
        ("POST", "https://api-testnet.aevo.xyz/builder/register"),
        ("GET", f"https://api-testnet.aevo.xyz/builders/{BUILDER_ID}"),
        ("GET", "https://api-testnet.aevo.xyz/builder-config"),
        ("GET", "https://api-testnet.aevo.xyz/account/builder-approvals"),
    ]
    assert client.client.calls[0][2]["json"] == {"name": "Copilot"}


def test_reporting_params(client):
    client.get_builder_stats(period="7d")
    client.get_builder_markets(start_time=1, end_time=2, limit=100, offset=200)
    client.get_builder_users(period="30d", limit=10, offset=20)
    client.get_builder_users(period="7d", limit=50, cursor="abc")
    client.get_builder_fills(instrument="ETH-PERP", limit=5, offset=15)
    got = [(u.rsplit("/", 1)[1], kw["params"]) for _, u, kw in client.client.calls]
    assert got == [
        ("stats", {"period": "7d"}),
        ("markets", {"start_time": 1, "end_time": 2, "limit": 100, "offset": 200}),
        ("users", {"period": "30d", "limit": 10, "offset": 20}),
        ("users", {"period": "7d", "limit": 50, "cursor": "abc"}),
        ("fills", {"instrument": "ETH-PERP", "limit": 5, "offset": 15}),
    ]


def test_reporting_omits_none_params(client):
    client.get_builder_markets(limit=None, offset=None)
    client.get_builder_users(period="7d", limit=None, cursor=None, offset=None)
    client.get_builder_fills(instrument="ETH-PERP", limit=None, cursor=None, offset=None)
    got = [(u.rsplit("/", 1)[1], kw["params"]) for _, u, kw in client.client.calls]
    assert got == [
        ("markets", {}),
        ("users", {"period": "7d"}),
        ("fills", {"instrument": "ETH-PERP"}),
    ]


@pytest.mark.parametrize(
    "method,kwargs",
    [
        ("get_builder_users", {"period": "7d", "cursor": "abc", "offset": 50}),
        ("get_builder_fills", {"cursor": "abc", "offset": 50}),
    ],
)
def test_reporting_rejects_cursor_with_offset(client, method, kwargs):
    with pytest.raises(ValueError, match="either cursor or offset"):
        getattr(client, method)(**kwargs)
    assert client.client.calls == []


def test_download_builder_fills_csv(client, tmp_path):
    url = "https://api-testnet.aevo.xyz/builder/fills"
    client.client.responses[("GET", url)] = FakeResponse(200, content=b"timestamp,trade_id\n")
    out = tmp_path / "fills.csv"
    assert client.download_builder_fills_csv(str(out), start_time=1, end_time=2) == str(out)
    assert out.read_bytes() == b"timestamp,trade_id\n"
    assert client.client.calls[-1][2]["params"] == {
        "start_time": 1, "end_time": 2, "format": "csv",
    }


def test_download_builder_fills_csv_error(client, tmp_path):
    url = "https://api-testnet.aevo.xyz/builder/fills"
    client.client.responses[("GET", url)] = FakeResponse(400, content=b'{"error":"CSV_RANGE_TOO_LARGE"}')
    out = tmp_path / "fills.csv"
    with pytest.raises(RuntimeError, match="CSV_RANGE_TOO_LARGE"):
        client.download_builder_fills_csv(str(out))
    assert not out.exists()
