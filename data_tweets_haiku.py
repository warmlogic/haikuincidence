from sqlalchemy import Column, String, Integer, Boolean, DateTime

from data_base import Base


class Haiku(Base):
    '''To drop it, run Haiku.metadata.drop_all(engine)
    '''
    __tablename__ = 'haikus'

    id = Column(Integer, primary_key=True)
    tweet_id_str = Column(String)
    user_screen_name = Column(String)
    user_id_str = Column(String)
    user_verified = Column(Boolean)
    created_at = Column(DateTime)
    text_original = Column(String)
    text_clean = Column(String)
    haiku = Column(String)

    def __init__(
        self,
        tweet_id_str,
        user_screen_name,
        user_id_str,
        user_verified,
        created_at,
        text_original,
        text_clean,
        haiku,
    ):
        self.tweet_id_str = tweet_id_str
        self.user_screen_name = user_screen_name
        self.user_id_str = user_id_str
        self.user_verified = user_verified
        self.created_at = created_at
        self.text_original = text_original
        self.text_clean = text_clean
        self.haiku = haiku
