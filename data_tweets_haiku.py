import configparser
from datetime import datetime, timedelta
import logging
import pytz

from sqlalchemy import Column, String, Integer, Boolean, DateTime
from data_base import Base

config = configparser.ConfigParser()
config.read('config.ini')

logger_name = config['haiku'].get('logger_name', 'default_logger')

logger = logging.getLogger(logger_name)

EVERY_N_SECONDS = config['haiku'].getint('every_n_seconds', 3600)


class Haiku(Base):
    '''To drop this table, run Haiku.metadata.drop_all(engine)
    '''
    __tablename__ = 'haikus'

    id = Column(Integer, primary_key=True)
    status_id_str = Column(String)
    user_screen_name = Column(String)
    user_id_str = Column(String)
    user_verified = Column(Boolean)
    created_at = Column(DateTime)
    text_original = Column(String)
    text_clean = Column(String)
    haiku = Column(String)
    date_posted = Column(DateTime, nullable=True)
    date_deleted = Column(DateTime, nullable=True)

    def __init__(
        self,
        status_id_str,
        user_screen_name,
        user_id_str,
        user_verified,
        created_at,
        text_original,
        text_clean,
        haiku,
        date_posted,
        date_deleted,
    ):
        self.status_id_str = status_id_str
        self.user_screen_name = user_screen_name
        self.user_id_str = user_id_str
        self.user_verified = user_verified
        self.created_at = created_at
        self.text_original = text_original
        self.text_clean = text_clean
        self.haiku = haiku
        self.date_posted = date_posted
        self.date_deleted = date_deleted


def db_add_haiku(session, tweet_haiku):
    '''Add haiku record to the database
    '''
    try:
        session.add(tweet_haiku)
        session.commit()
    except Exception as e:
        logger.info(f'Exception when adding haiku: {e}')
        session.rollback()


def db_get_haikus_all(session):
    '''Get all records
    '''
    haiku_query = session.query(Haiku)
    return haiku_query.all()


def db_get_haikus_posted(session):
    '''Get all posted records
    '''
    haiku_query = session.query(Haiku).filter(
        Haiku.date_posted != None).filter(Haiku.date_deleted == None)  # noqa: E711
    return haiku_query.all()


def db_get_haikus_unposted(session):
    '''Get all unposted records
    '''
    haiku_query = session.query(Haiku).filter(
        Haiku.date_posted == None).filter(Haiku.date_deleted == None)  # noqa: E711
    return haiku_query.all()


def db_get_haikus_unposted_timedelta(session, td_seconds=None):
    '''Get all unposted records from the last N seconds
    '''
    if td_seconds is None:
        td_seconds = EVERY_N_SECONDS
    filter_td = datetime.now().replace(tzinfo=pytz.UTC) - timedelta(seconds=td_seconds)
    haiku_query = session.query(Haiku).filter(
        Haiku.created_at > filter_td).filter(
            Haiku.date_posted == None).filter(Haiku.date_deleted == None)  # noqa: E711
    return haiku_query.all()


def db_update_haiku_posted(session, status_id_str):
    '''Mark haiku as posted
    '''
    try:
        session.query(Haiku).filter(
            Haiku.status_id_str == status_id_str).update(
                {'date_posted': datetime.now().replace(tzinfo=pytz.UTC)})
        session.commit()
    except Exception as e:
        logger.info(f'Exception when updating haiku as posted: {e}')
        session.rollback()


def db_update_haiku_unposted(session, status_id_str):
    '''Mark haiku as unposted
    '''
    try:
        session.query(Haiku).filter(
            Haiku.status_id_str == status_id_str).update(
                {'date_posted': None})
        session.commit()
    except Exception as e:
        logger.info(f'Exception when updating haiku as unposted: {e}')
        session.rollback()


def db_update_haiku_deleted(session, status_id_str):
    '''Mark haiku as deleted
    '''
    try:
        session.query(Haiku).filter(
            Haiku.status_id_str == status_id_str).update(
                {'date_deleted': datetime.now().replace(tzinfo=pytz.UTC)})
        session.commit()
    except Exception as e:
        logger.info(f'Exception when updating haiku as deleted: {e}')
        session.rollback()


def db_update_haiku_undeleted(session, status_id_str):
    '''Mark haiku as undeleted
    '''
    try:
        session.query(Haiku).filter(
            Haiku.status_id_str == status_id_str).update(
                {'date_deleted': None})
        session.commit()
    except Exception as e:
        logger.info(f'Exception when updating haiku as undeleted: {e}')
        session.rollback()
