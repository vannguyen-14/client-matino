# database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# DB_URL = "mysql+aiomysql://root:@localhost:3306/super_matino"
# DB_URL = "mysql+aiomysql://nguyen:Metatek99%401@192.168.1.41:3306/super_matino"
DB_URL = "mysql+aiomysql://nguyen:EgH8%40BdGkE7k7pk@43.231.65.179:3306/super_matino"

# ⚡ Thêm pool_pre_ping & pool_recycle để tránh connection chết
engine = create_async_engine(
    DB_URL,
    echo=True,
    pool_pre_ping=True,   # test connection trước khi dùng
    pool_recycle=3600     # tái chế connection sau 1h
)

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False  # ⚡ tránh lỗi khi access sau commit
)

Base = declarative_base()

# from utils.launch_filter import apply_launch_filter
# from models.myid_models import MyIDCustomer, MyIDCustomerHistory, MyIDCustomerCancel

# TARGET_MODELS = {
#     MyIDCustomer: "create_date",
#     MyIDCustomerHistory: "created_at",
#     MyIDCustomerCancel: "cancel_date",
# }

# apply_launch_filter(AsyncSession, TARGET_MODELS)

# Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
