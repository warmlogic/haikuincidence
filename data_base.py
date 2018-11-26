import configparser

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

config = configparser.ConfigParser()
config.read('config.ini')

db_user = config['database'].get('DB_USER', '')
db_password = config['database'].get('DB_PASSWORD', '')
db_server = config['database'].get('DB_SERVER', 'localhost')
db_port = config['database'].get('DB_PORT', '5432')

db_url = f"postgresql://{db_user}:{db_password}@{db_server}:{db_port}/{db_user}"

engine = create_engine(db_url)
_SessionFactory = sessionmaker(bind=engine)

Base = declarative_base()


def session_factory():
    Base.metadata.create_all(engine)
    return _SessionFactory()
