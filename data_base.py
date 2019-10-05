from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from data_tweets_haiku import Haiku


def session_factory(DATABASE_URL: str):
    engine = create_engine(DATABASE_URL, poolclass=NullPool)
    Base = declarative_base()
    Base.metadata.create_all(engine, tables=[Haiku.__table__])
    _SessionFactory = sessionmaker(bind=engine)
    return _SessionFactory()
