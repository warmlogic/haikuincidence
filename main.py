from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
from pprint import pformat
import pytz

from dotenv import load_dotenv
import inflect
from nltk.corpus import cmudict
from twython import Twython, TwythonError
from twython import TwythonStreamer

from utils.data_utils import get_track_str, get_ignore_list, get_syllable_dict, get_emoticons_list
from utils.text_utils import date_string_to_datetime, check_tweet, clean_text, check_text_wrapper
from utils.haiku_utils import get_haiku, get_best_haiku

from utils.data_base import session_factory
from utils.data_tweets_haiku import Haiku, db_add_haiku, db_get_haikus_unposted_timedelta
from utils.data_tweets_haiku import db_update_haiku_posted, db_delete_haikus_unposted_timedelta, db_delete_haikus_posted_timedelta

# I'm a poet and I didn't even know it. Hey, that's a haiku!

logging.basicConfig(format='{asctime} : {levelname} : {message}', style='{')
logger = logging.getLogger("haikulogger")

IS_PROD = os.getenv("IS_PROD", default=None)

if IS_PROD is None:
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        raise OSError(f"{env_path} not found. Did you set it up?")

DEBUG_RUN = os.getenv("DEBUG_RUN", default="False")
if DEBUG_RUN not in ["True", "False"]:
    raise ValueError(f"DEBUG_RUN must be True or False, current value: {DEBUG_RUN}")
DEBUG_RUN = DEBUG_RUN == "True"

if DEBUG_RUN:
    logger.setLevel(logging.DEBUG)
    POST_HAIKU = False
    POST_AS_REPLY = False
    FOLLOW_POET = False
    EVERY_N_SECONDS = 1
    DELETE_OLDER_THAN_DAYS = None
    INITIAL_TIME = datetime(1970, 1, 1)
else:
    logger.setLevel(logging.INFO)
    POST_HAIKU = os.getenv("POST_HAIKU", default="False") == "True"
    POST_AS_REPLY = os.getenv("POST_AS_REPLY", default="False") == "True"
    FOLLOW_POET = os.getenv("FOLLOW_POET", default="False") == "True"
    EVERY_N_SECONDS = int(os.getenv("EVERY_N_SECONDS", default="3600"))
    DELETE_OLDER_THAN_DAYS = int(os.getenv("DELETE_OLDER_THAN_DAYS", default="45"))
    # Wait half the rate limit time before making first post
    INITIAL_TIME = datetime.now().replace(tzinfo=pytz.UTC) - timedelta(seconds=EVERY_N_SECONDS // 2)

APP_KEY = os.getenv("API_KEY", default="")
APP_SECRET = os.getenv("API_SECRET", default="")
OAUTH_TOKEN = os.getenv("ACCESS_TOKEN", default="")
OAUTH_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET", default="")
DATABASE_URL = os.getenv("DATABASE_URL", default="")
MY_SCREEN_NAME = os.getenv("MY_SCREEN_NAME", default="twitter")
LANGUAGE = os.getenv("LANGUAGE", default="en")
GUESS_SYL_METHOD = os.getenv("GUESS_SYL_METHOD", default="min")


class MyTwitterClient(Twython):
    '''Wrapper around the Twython Twitter client.
    Limits status update rate.
    '''
    def __init__(self, initial_time=None, *args, **kwargs):
        super(MyTwitterClient, self).__init__(*args, **kwargs)
        if initial_time is None:
            # Wait half the rate limit time before making first post
            initial_time = datetime.now().replace(tzinfo=pytz.UTC) - timedelta(seconds=EVERY_N_SECONDS // 2)
        self.last_post_time = initial_time

    def update_status_check_rate(self, *args, **kwargs):
        current_time = datetime.now().replace(tzinfo=pytz.UTC)
        logger.info(f'Current time: {current_time}')
        logger.info(f'Previous post time: {self.last_post_time}')
        logger.info(f'Difference: {current_time - self.last_post_time}')
        if (current_time - self.last_post_time).total_seconds() > EVERY_N_SECONDS:
            self.update_status(*args, **kwargs)
            self.last_post_time = current_time
            logger.info('Success')
            return True
        else:
            logger.info('Not posting haiku due to rate limit')
            return False


class MyStreamer(TwythonStreamer):
    def on_success(self, status):
        if 'text' in status and check_tweet(status, ignore_list, language=LANGUAGE):
            # print(status['text'])
            text = clean_text(status['text'])
            if check_text_wrapper(text, ignore_list):
                haiku = get_haiku(text, inflect_p, pronounce_dict, syllable_dict, emoticons_list, GUESS_SYL_METHOD)
                if haiku:
                    # add tweet to database
                    tweet_haiku = Haiku(
                        status['id_str'],
                        status['user']['screen_name'],
                        status['user']['id_str'],
                        status['user']['verified'],
                        date_string_to_datetime(status['created_at']),
                        status['text'],
                        text,
                        haiku,
                        None,
                        None,
                    )
                    if not DEBUG_RUN:
                        # Add it to the database
                        db_add_haiku(session, tweet_haiku)
                    logger.info('=' * 50)
                    logger.info(f"Found new haiku:\n{tweet_haiku.haiku}")

                    if not DEBUG_RUN:
                        # Get haikus from the last hour
                        haikus = db_get_haikus_unposted_timedelta(session, td_seconds=EVERY_N_SECONDS)
                        # Prune old haikus
                        db_delete_haikus_unposted_timedelta(session, td_days=DELETE_OLDER_THAN_DAYS)
                        db_delete_haikus_posted_timedelta(session, td_days=DELETE_OLDER_THAN_DAYS)
                    else:
                        # Use the current haiku
                        haikus = [tweet_haiku]

                    # # Get all unposted haikus
                    # haikus = db_get_haikus_unposted(session)

                    if len(haikus) > 0:
                        # Get the haiku to post
                        haiku_to_post = get_best_haiku(haikus, twitter, session)
                        if haiku_to_post['status_id_str'] != '':
                            status = twitter.show_status(id=haiku_to_post['status_id_str'])

                            # Format the haiku with attribution
                            haiku_attributed = f"{haiku_to_post['haiku']}\n\nA haiku by @{status['user']['screen_name']}"

                            tweet_url = f"https://twitter.com/{status['user']['screen_name']}/status/{status['id_str']}"

                            logger.info('=' * 50)
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug(pformat(status))
                                logger.debug(tweet_url)
                                logger.debug(f"Original: {haiku_to_post['text_original']}")
                                logger.debug(f"Cleaned:  {haiku_to_post['text_clean']}")
                            logger.info(f"Haiku to post:\n{haiku_attributed}")

                            # Try to post haiku (client checks rate limit time internally)
                            if POST_HAIKU:
                                if POST_AS_REPLY:
                                    logger.info('Attempting to post haiku as reply...')
                                    # Post a tweet, sending as a reply to the coincidental haiku
                                    posted_status = twitter.update_status_check_rate(
                                        status=haiku_attributed,
                                        in_reply_to_status_id=status['id_str'],
                                        attachment_url=tweet_url,
                                    )
                                else:
                                    logger.info('Attempting to post haiku, but not as reply...')
                                    # Post a tweet, but not as a reply to the coincidental haiku
                                    # The user will not get a notification
                                    posted_status = twitter.update_status_check_rate(
                                        status=haiku_attributed,
                                        attachment_url=tweet_url,
                                    )
                                if posted_status:
                                    logger.info('Attempting to follow this poet...')
                                    db_update_haiku_posted(session, haiku_to_post['status_id_str'])

                                    # follow the user
                                    if FOLLOW_POET:
                                        try:
                                            followed = twitter.create_friendship(
                                                screen_name=haiku_to_post['user_screen_name'], follow='false')
                                            if followed['following']:
                                                logger.info('Success')
                                            else:
                                                logger.info('Could not follow')
                                        except TwythonError as e:
                                            logger.info(e)

                            else:
                                logger.debug('Found haiku but did not post')
                    else:
                        logger.info('No haikus to choose from')

    def on_error(self, status_code, status):
        logger.error(f'{status_code}, {status}')


logger.info('Initializing dependencies...')

# get data to use for dealing with tweets
track_str = get_track_str()
ignore_list = get_ignore_list()
syllable_dict = get_syllable_dict()
emoticons_list = get_emoticons_list()

# Use inflect to change digits to their English word equivalent
inflect_p = inflect.engine()
# Use the CMU dictionary to count syllables
pronounce_dict = cmudict.dict()

# Establish connection to Twitter
# Uses OAuth1 ("user auth") for authentication
twitter = MyTwitterClient(
    initial_time=INITIAL_TIME,
    app_key=APP_KEY,
    app_secret=APP_SECRET,
    oauth_token=OAUTH_TOKEN,
    oauth_token_secret=OAUTH_TOKEN_SECRET,
)

# if this screen_name has a recent tweet, use that timestamp as the time of the last post
most_recent_tweet = twitter.get_user_timeline(screen_name=MY_SCREEN_NAME, count=1, trim_user=True)
if len(most_recent_tweet) > 0:
    twitter.last_post_time = date_string_to_datetime(most_recent_tweet[0]['created_at'])

# Establish connection to database
session = session_factory(DATABASE_URL)


if __name__ == '__main__':
    logger.info('Initializing tweet streamer...')
    stream = MyStreamer(
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        oauth_token=OAUTH_TOKEN,
        oauth_token_secret=OAUTH_TOKEN_SECRET,
    )

    logger.info('Looking for haikus...')
    while True:
        # Use try/except to avoid ChunkedEncodingError
        # https://github.com/ryanmcgrath/twython/issues/288
        try:
            if track_str:
                # search specific keywords
                stream.statuses.filter(track=track_str)
            else:
                # get samples from stream
                stream.statuses.sample()
        except Exception:
            logger.exception('Exception when streaming tweets')
            continue
