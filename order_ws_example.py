import asyncio

from loguru import logger

from aevo import AevoClient


async def main():
    # The following values which are used for authentication on private endpoints, can be retrieved from the Aevo UI
    aevo = AevoClient(
        signing_key="",
        wallet_address="",
        api_key="",
        api_secret="",
        env="testnet",
    )

    if not aevo.signing_key:
        raise Exception(
            "Signing key is not set. Please set the signing key in the AevoClient constructor."
        )

    await aevo.open_connection()

    logger.info("Creating order...")
    # ETH-PERP has an instrument id of 2054 on testnet, you can find the instrument id of other markets by looking at this endpoint: https://api-testnet.aevo.xyz/markets
    order_id = await aevo.create_order(
        instrument_id=2054,
        is_buy=True,
        limit_price=1200,
        quantity=0.01,
        post_only=False,
    )

    # Wait for order to go through
    await asyncio.sleep(1)

    # Edit the order price
    # NOTE: order id will change after editing
    logger.info("Editing order...")
    order_id = await aevo.edit_order(
        order_id=order_id,
        instrument_id=2054,
        is_buy=True,
        limit_price=1500,
        quantity=0.01,
        post_only=False,
    )

    logger.info("Cancelling order...")
    order_id = await aevo.cancel_order(
        order_id=order_id,
    )

    async for msg in aevo.read_messages():
        logger.info(msg)


if __name__ == "__main__":
    asyncio.run(main())
