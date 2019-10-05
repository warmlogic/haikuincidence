from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


def session_factory(DB_USER, DB_PASSWORD, DB_SERVER, DB_PORT):
    DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_USER}"
    engine = create_engine(DB_URL, poolclass=NullPool)
    Base = declarative_base()
    Base.metadata.create_all(engine)
    _SessionFactory = sessionmaker(bind=engine)
    return _SessionFactory()
