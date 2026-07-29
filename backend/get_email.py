# ruff: noqa: T201
import asyncio

from sqlalchemy import text

from app.infrastructure.database.connection import (
    close_engine,
    create_engine_and_factory,
    get_session_factory,
)


async def main():
    create_engine_and_factory()
    factory = get_session_factory()
    async with factory() as session:
        res = await session.execute(text("SELECT email FROM users LIMIT 1"))
        print(f"EMAIL_FOUND: {res.scalar()}")
    await close_engine()

asyncio.run(main())
