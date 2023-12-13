import asyncio

from loguru import logger

from aevo import AevoClient


async def main():
    # The following values which are used for authentication on private endpoints, can be retrieved from the Aevo UI
    aevo = AevoClient(
        signing_key="0x006421ca90740ac487e3da2842d20240b81d015704b7d9f96a4b1f91b2e446ff",
        wallet_address="0x8454945ECC1f5152E41f6C1dee5F1aB151aC0808",
        api_key="RdxcugVksjVCdvcH1rCkF3qVXrtquoRv",
        api_secret="b8c4623991bfe99938be5010ac5d32cf4f684187f14e8238ef28a3298f4bf1db",
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
