import asyncio
import logging

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.services.usage_monitor import run_usage_monitor_once

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('usage-worker')


async def loop() -> None:
    while True:
        async with AsyncSessionLocal() as session:
            result = await run_usage_monitor_once(session)
            logger.info('usage monitor checked=%s charged=%s restricted=%s errors=%s', result.checked, result.charged, result.restricted, len(result.errors))
            for error in result.errors:
                logger.warning('usage monitor error: %s', error)
        await asyncio.sleep(settings.usage_poll_interval_seconds)


def main() -> None:
    asyncio.run(loop())


if __name__ == '__main__':
    main()
