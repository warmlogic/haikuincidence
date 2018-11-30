from sqlalchemy import Column, String, Integer, Boolean, DateTime

from data_base import Base


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
