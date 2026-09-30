from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config.settings import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.database_echo,  # já que você tem esse campo no settings, aproveita ele em vez de fixar False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()