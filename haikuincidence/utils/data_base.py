import logging
from datetime import datetime, timedelta

import pytz
from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from .text_utils import date_string_to_datetime, get_tweet_body

logger = logging.getLogger("haiku_logger")

Base = declarative_base()


def session_factory(DATABASE_URL: str, echo: bool = False):
    engine = create_engine(DATABASE_URL, poolclass=NullPool, echo=echo)
    Base.metadata.create_all(engine)
    _SessionFactory = sessionmaker(bind=engine)
    return _SessionFactory()


class Haiku(Base):
    """To drop this table, run Haiku.metadata.drop_all(engine)"""

    __tablename__ = "haikus"

    id = Column(Integer, primary_key=True)
    status_id_str = Column(String, nullable=False)
    user_screen_name = Column(String, nullable=False)
    user_id_str = Column(String, nullable=False)
    user_verified = Column(Boolean, nullable=False)
    created_at = Column(DateTime, nullable=False)
    text_original = Column(String, nullable=False)
    text_clean = Column(String, nullable=False)
    haiku = Column(String, nullable=False)
    date_posted = Column(DateTime, nullable=True)
    date_deleted = Column(DateTime, nullable=True)

    @classmethod
    def add_haiku(cls, db_session, status, text, haiku, log_haiku: bool = True):
        """Add haiku record to the database"""
        tweet_haiku = cls(
            status_id_str=status["id_str"],
            user_screen_name=status["user"]["screen_name"],
            user_id_str=status["user"]["id_str"],
            user_verified=status["user"]["verified"],
            created_at=date_string_to_datetime(status["created_at"]),
            text_original=get_tweet_body(status),
            text_clean=text,
            haiku=haiku,
            date_posted=None,
            date_deleted=None,
        )

        if log_haiku:
            db_session.add(tweet_haiku)
            try:
                db_session.commit()
            except Exception as e:
                logger.warning(f"Exception when adding haiku: {e}")
                db_session.rollback()

        return tweet_haiku

    @classmethod
    def get_haikus_all(cls, db_session) -> list:
        """Get all records"""
        q = db_session.query(cls)
        return q.all()

    @classmethod
    def get_haikus_posted(cls, db_session) -> list:
        """Get all posted records"""
        q = (
            db_session.query(cls)
            .filter(cls.date_posted != None)  # noqa: E711
            .filter(cls.date_deleted == None)  # noqa: E711
        )
        return q.all()

    @classmethod
    def get_haikus_unposted(cls, db_session) -> list:
        """Get all unposted records"""
        q = (
            db_session.query(cls)
            .filter(cls.date_posted == None)  # noqa: E711
            .filter(cls.date_deleted == None)  # noqa: E711
        )
        return q.all()

    @classmethod
    def get_haikus_unposted_timedelta(cls, db_session, td_seconds: int = None) -> list:
        """Get all unposted records from the last N seconds"""
        if td_seconds is None:
            td_seconds = 3600
        filter_td = datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(
            seconds=td_seconds
        )
        q = (
            db_session.query(cls)
            .filter(cls.created_at > filter_td)
            .filter(cls.date_posted == None)  # noqa: E711
            .filter(cls.date_deleted == None)  # noqa: E711
        )
        return q.all()

    @classmethod
    def update_haiku_posted(cls, db_session, status_id_str: str):
        """Mark haiku as posted"""
        try:
            db_session.query(cls).filter(cls.status_id_str == status_id_str).update(
                {"date_posted": datetime.utcnow().replace(tzinfo=pytz.UTC)}
            )
            db_session.commit()
        except Exception as e:
            logger.warning(f"Exception when updating haiku as posted: {e}")
            db_session.rollback()

    @classmethod
    def update_haiku_unposted(cls, db_session, status_id_str: str):
        """Mark haiku as unposted"""
        try:
            db_session.query(cls).filter(cls.status_id_str == status_id_str).update(
                {"date_posted": None}
            )
            db_session.commit()
        except Exception as e:
            logger.warning(f"Exception when updating haiku as unposted: {e}")
            db_session.rollback()

    @classmethod
    def update_haiku_deleted(cls, db_session, status_id_str: str):
        """Mark haiku as deleted"""
        try:
            db_session.query(cls).filter(cls.status_id_str == status_id_str).update(
                {"date_deleted": datetime.utcnow().replace(tzinfo=pytz.UTC)}
            )
            db_session.commit()
        except Exception as e:
            logger.warning(f"Exception when updating haiku as deleted: {e}")
            db_session.rollback()

    @classmethod
    def update_haiku_undeleted(cls, db_session, status_id_str: str):
        """Mark haiku as undeleted"""
        try:
            db_session.query(cls).filter(cls.status_id_str == status_id_str).update(
                {"date_deleted": None}
            )
            db_session.commit()
        except Exception as e:
            logger.warning(f"Exception when updating haiku as undeleted: {e}")
            db_session.rollback()

    @classmethod
    def delete_haikus_unposted_timedelta(cls, db_session, days: float = None) -> list:
        """Delete all unposted records older than N days"""
        if days is not None:
            ts_end = datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(days=days)
            try:
                logger.info(f"Deleting unposted haikus older than {days} days")
                delete_q = (
                    cls.__table__.delete()
                    .where(cls.created_at < ts_end)
                    .where(cls.date_posted == None)  # noqa: E711
                )

                db_session.execute(delete_q)
                db_session.commit()
            except Exception as e:
                logger.warning(f"Exception when deleting old unposted haikus: {e}")
                db_session.rollback()

    @classmethod
    def delete_haikus_posted_timedelta(cls, db_session, days: float = None) -> list:
        """Delete all posted records older than N days"""
        if days is not None:
            ts_end = datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(days=days)
            try:
                logger.info(f"Deleting posted haikus older than {days} days")
                delete_q = (
                    cls.__table__.delete()
                    .where(cls.created_at < ts_end)
                    .where(cls.date_posted != None)  # noqa: E711
                )

                db_session.execute(delete_q)
                db_session.commit()
            except Exception as e:
                logger.warning(f"Exception when deleting old posted haikus: {e}")
                db_session.rollback()

    @classmethod
    def keep_haikus_n_rows(cls, db_session, n: int = None):
        """Keep the most recent n rows"""
        if n is not None:
            ids = db_session.query(cls.id).order_by(desc(cls.created_at)).all()
            ids_to_delete = [x[0] for x in ids[n:]]

            if ids_to_delete:
                try:
                    logger.info(f"Keeping most recent {n} rows of haikus")
                    delete_q = cls.__table__.delete().where(cls.id.in_(ids_to_delete))

                    db_session.execute(delete_q)
                    db_session.commit()
                except Exception as e:
                    logger.warning(
                        f"Exception when keeping most recent rows of haikus: {e}"
                    )
                    db_session.rollback()
