import configparser
from datetime import datetime, timedelta
import logging
import pytz
from typing import List

from sqlalchemy import Column, String, Integer, Boolean, DateTime
from data_base import Base

config = configparser.ConfigParser()
config.read('config.ini')

logging.basicConfig(format='{asctime} : {levelname} : {message}', level=logging.INFO, style='{')
logger = logging.getLogger(__name__)

EVERY_N_SECONDS = config['haiku'].getint('EVERY_N_SECONDS', 3600)


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


def db_get_haikus_all(session) -> List:
    '''Get all records
    '''
    haiku_query = session.query(Haiku)
    return haiku_query.all()


def db_get_haikus_posted(session) -> List:
    '''Get all posted records
    '''
    haiku_query = session.query(Haiku).filter(
        Haiku.date_posted != None).filter(Haiku.date_deleted == None)  # noqa: E711
    return haiku_query.all()


def db_get_haikus_unposted(session) -> List:
    '''Get all unposted records
    '''
    haiku_query = session.query(Haiku).filter(
        Haiku.date_posted == None).filter(Haiku.date_deleted == None)  # noqa: E711
    return haiku_query.all()


def db_get_haikus_unposted_timedelta(session, td_seconds=None) -> List:
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


def db_delete_haikus_unposted_timedelta(session, td_days: int = None) -> List:
    '''Delete all unposted records older than N days
    '''
    if td_days:
        filter_td = datetime.now().replace(tzinfo=pytz.UTC) - timedelta(days=td_days)
        try:
            delete_q = Haiku.__table__.delete().where(
                Haiku.created_at <= filter_td).where(
                    Haiku.date_posted == None)  # noqa: E711

            session.execute(delete_q)
            session.commit()
        except Exception:
            logger.exception(f'Exception when deleting unposted haikus older than {td_days} days')
            session.rollback()
