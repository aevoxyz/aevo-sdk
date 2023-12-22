# Example deposit using
from web3 import Web3
from web3.middleware import construct_sign_and_send_raw_middleware
from loguru import logger
import json
from aevo import ADDRESSES, CONFIG

DEFAULT_GAS_LIMIT = 650000

# This is a sample RPC
# It's recommended that you use your own RPC from RPC providers such as Alchemy or Infura
HTTP_URL = ""

if __name__ == "__main__":
    w3 = Web3(Web3.HTTPProvider(HTTP_URL))

    env = "testnet"  # Change ENV if needed
    private_key = ""  # Insert your private key
    amount = 1000000  # Amount in 6 decimals fixed math e.g. $1 -> 1000000

    # Load account
    acc = w3.eth.account.from_key(private_key)
    logger.info(f"Your hot wallet address is {acc.address}")

    # APPROVE USDC ---------
    # Set up the contract binding
    with open("./abis/erc20.json") as f:
        erc20_abi = json.load(f)
    usdc_contract = w3.eth.contract(address=ADDRESSES[env]["l1_usdc"], abi=erc20_abi)

    nonce = w3.eth.get_transaction_count(acc.address)

    # Form the approval calldata
    approval_data = usdc_contract.functions.approve(
        ADDRESSES[env]["l1_bridge"], amount
    ).build_transaction({"nonce": nonce})
    # Form the transaction byte data
    approval_txn = w3.eth.account.sign_transaction(
        approval_data, private_key=private_key
    )
    # Send and wait for the transaction
    approval_tx_hash = w3.eth.send_raw_transaction(approval_txn.rawTransaction)
    w3.eth.wait_for_transaction_receipt(approval_tx_hash.hex())
    logger.info(
        f"Approved L1StandardBridge for {amount/1e6} - TX_HASH: {approval_tx_hash.hex()}"
    )

    # DEPOSIT FROM BRIDGE ---------
    # Set up the contract binding
    with open("./abis/erc20StandardBridge.json") as f:
        bridge_abi = json.load(f)
    bridge_contract = w3.eth.contract(
        address=ADDRESSES[env]["l1_bridge"], abi=bridge_abi
    )

    nonce = w3.eth.get_transaction_count(acc.address)

    # Form the deposit calldata
    deposit_data = bridge_contract.functions.depositERC20(
        ADDRESSES[env]["l1_usdc"],
        ADDRESSES[env]["l2_usdc"],
        amount,
        DEFAULT_GAS_LIMIT,
        b"",
    ).build_transaction({"nonce": nonce, "gas": DEFAULT_GAS_LIMIT})
    # Form the transaction byte data
    deposit_txn = w3.eth.account.sign_transaction(deposit_data, private_key=private_key)
    # Send and wait for the transaction
    deposit_tx_hash = w3.eth.send_raw_transaction(deposit_txn.rawTransaction)
    w3.eth.wait_for_transaction_receipt(deposit_tx_hash.hex())
    logger.info(
        f"Deposit {amount/10e6} to L1StandardBridge - TX_HASH {deposit_tx_hash}"
    )
