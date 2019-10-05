import configparser

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

config = configparser.ConfigParser()
config.read('config.ini')

DB_USER = config['database'].get('DB_USER', '')
DB_PASSWORD = config['database'].get('DB_PASSWORD', '')
DB_SERVER = config['database'].get('DB_SERVER', 'localhost')
DB_PORT = config['database'].get('DB_PORT', '5432')

DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_USER}"

engine = create_engine(DB_URL, poolclass=NullPool)
_SessionFactory = sessionmaker(bind=engine)

Base = declarative_base()


def session_factory():
    Base.metadata.create_all(engine)
    return _SessionFactory()
