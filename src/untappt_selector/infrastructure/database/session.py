from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from untappt_selector.core.config import get_settings

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
