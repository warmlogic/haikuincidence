import configparser
from datetime import datetime, timedelta
import logging
from pprint import pformat
import pytz

import inflect
from nltk.corpus import cmudict
from twython import Twython, TwythonError
from twython import TwythonStreamer

from data_utils import get_track_str, get_ignore_list, get_syllable_dict, get_emoticons_list
from text_utils import date_string_to_datetime, check_tweet, clean_text, check_text_wrapper
from haiku_utils import get_haiku, get_best_haiku

from data_base import session_factory
from data_tweets_haiku import Haiku, db_add_haiku, db_get_haikus_unposted_timedelta
from data_tweets_haiku import db_update_haiku_posted, db_delete_haikus_unposted_timedelta

# I'm a poet and I didn't even know it. Hey, that's a haiku!

config = configparser.ConfigParser()
config.read('config.ini')

logger_name = config['haiku'].get('logger_name', 'default_logger')
logger = logging.getLogger(logger_name)

debug_run = config['haiku'].getboolean('debug_run', False)

if debug_run:
    logging.basicConfig(format='{asctime} : {levelname} : {message}', level=logging.DEBUG, style='{')
    post_haiku = False
    post_as_reply = False
    follow_poet = False
    every_n_seconds = 1
    initial_time = datetime(1970, 1, 1)
    delete_older_than_days = None
else:
    logging.basicConfig(format='{asctime} : {levelname} : {message}', level=logging.INFO, style='{')
    post_haiku = config['haiku'].getboolean('post_haiku', False)
    post_as_reply = config['haiku'].getboolean('post_as_reply', False)
    follow_poet = config['haiku'].getboolean('follow_poet', False)
    # Minimum amount of time between haiku posts
    every_n_seconds = config['haiku'].getint('every_n_seconds', 3600)
    # Wait half the rate limit time before making first post
    initial_time = datetime.now().replace(tzinfo=pytz.UTC) - timedelta(seconds=every_n_seconds // 2)
    # Delete unposted haikus from database that are older than this many days
    delete_older_than_days = config['haiku'].getint('delete_older_than_days', 180)


class MyTwitterClient(Twython):
    '''Wrapper around the Twython Twitter client.
    Limits status update rate.
    '''
    def __init__(self, every_n_seconds=3600, initial_time=None, *args, **kwargs):
        super(MyTwitterClient, self).__init__(*args, **kwargs)
        if initial_time is None:
            # Wait half the rate limit time before making first post
            initial_time = datetime.now().replace(tzinfo=pytz.UTC) - timedelta(seconds=every_n_seconds // 2)
        self.every_n_seconds = every_n_seconds
        self.last_post_time = initial_time

    def update_status_check_rate(self, *args, **kwargs):
        current_time = datetime.now().replace(tzinfo=pytz.UTC)
        logger.info(f'Current time: {current_time}')
        logger.info(f'Previous post time: {self.last_post_time}')
        logger.info(f'Difference: {current_time - self.last_post_time}')
        if (current_time - self.last_post_time).total_seconds() > self.every_n_seconds:
            self.update_status(*args, **kwargs)
            self.last_post_time = current_time
            logger.info('Success')
            return True
        else:
            logger.info('Not posting haiku due to rate limit')
            return False


class MyStreamer(TwythonStreamer):
    def on_success(self, status):
        if 'text' in status and check_tweet(status, ignore_list):
            # print(status['text'])
            text = clean_text(status['text'])
            if check_text_wrapper(text, ignore_list):
                haiku = get_haiku(text, inflect_p, pronounce_dict, syllable_dict, emoticons_list)
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
                    if not debug_run:
                        # Add it to the database
                        db_add_haiku(session, tweet_haiku)
                    logger.info('=' * 50)
                    logger.info(f"Found new haiku:\n{tweet_haiku.haiku}")

                    if not debug_run:
                        # Get haikus from the last hour
                        haikus = db_get_haikus_unposted_timedelta(session, td_seconds=every_n_seconds)
                        # Prune old haikus
                        db_delete_haikus_unposted_timedelta(session, td_days=delete_older_than_days)
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
                            if post_haiku:
                                if post_as_reply:
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
                                    if follow_poet:
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
twitter = MyTwitterClient(
    every_n_seconds=every_n_seconds,
    initial_time=initial_time,
    app_key=config['twitter'].get('api_key', ''),
    app_secret=config['twitter'].get('api_secret', ''),
    oauth_token=config['twitter'].get('access_token', ''),
    oauth_token_secret=config['twitter'].get('access_token_secret', ''),
)

# if this screen_name has a recent tweet, use that timestamp as the time of the last post
my_screen_name = config['haiku'].get('my_screen_name', 'twitter')
most_recent_tweet = twitter.get_user_timeline(screen_name=my_screen_name, count=1, trim_user=True)
if len(most_recent_tweet) > 0:
    twitter.last_post_time = date_string_to_datetime(most_recent_tweet[0]['created_at'])

# Establish connection to database
session = session_factory()


if __name__ == '__main__':
    logger.info('Initializing tweet streamer...')
    stream = MyStreamer(
        app_key=config['twitter']['api_key'],
        app_secret=config['twitter']['api_secret'],
        oauth_token=config['twitter']['access_token'],
        oauth_token_secret=config['twitter']['access_token_secret'],
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
        except Exception as e:
            logger.warning(f'Exception when streaming tweets: {e}')
            continue
