import asyncio

from loguru import logger

from aevo import AevoClient


async def main():
    # The following values which are used for authentication on private endpoints, can be retrieved from the Aevo UI
    aevo = AevoClient(
        wallet_private_key="",  # SET VALUE
        wallet_address="",  # SET VALUE
        api_key="",  # SET VALUE
        api_secret="",  # SET VALUE
        env="testnet",
    )

    if not aevo.wallet_private_key:
        raise Exception(
            "Wallet private key is not set. Please set the wallet private key in the AevoClient constructor."
        )

    logger.info("Initiating withdrawal...")
    response = aevo.withdraw(amount=10.5)
    logger.info(response)


if __name__ == "__main__":
    asyncio.run(main())
