# I'm a poet and I didn't even know it. Hey, that's a haiku!

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from pprint import pformat

import inflect
import pytz
from dotenv import load_dotenv
from nltk.corpus import cmudict
from tenacity import retry, stop_after_attempt, wait_fixed
from twython import (
    Twython,
    TwythonAuthError,
    TwythonError,
    TwythonRateLimitError,
    TwythonStreamer,
)
from utils.data_base import Haiku, session_factory
from utils.data_utils import (
    get_emoticons_list,
    get_ignore_profile_list,
    get_ignore_tweet_list,
    get_syllable_dict,
    get_track_str,
)
from utils.haiku_utils import get_best_haiku, get_haiku
from utils.text_utils import (
    check_profile,
    check_text_wrapper,
    check_tweet,
    clean_text,
    date_string_to_datetime,
    get_tweet_body,
)

logging.basicConfig(format="{asctime} : {levelname} : {message}", style="{")
logger = logging.getLogger("haiku_logger")

ENVIRONMENT = os.getenv("ENVIRONMENT", default="development").lower()
assert ENVIRONMENT in [
    "development",
    "production",
], f"Invalid ENVIRONMENT: {ENVIRONMENT}"

# Set up a root_dir to support running from different locations during development
if ENVIRONMENT == "development":
    if (Path.cwd() / "data").exists():
        root_dir = Path.cwd()
    elif (Path.cwd().parent / "data").exists():
        root_dir = Path.cwd().parent
    else:
        raise OSError(f"Running from unsupported directory: {Path.cwd()}")

    # Read .env file for local development
    dotenv_file = root_dir / ".env"
    try:
        with open(dotenv_file, "r") as fp:
            _ = load_dotenv(stream=fp)
    except FileNotFoundError:
        logger.info(f"{dotenv_file} file not found. Did you set it up?")
        raise
else:
    root_dir = Path.cwd()

DEBUG_MODE = os.getenv("DEBUG_MODE", default="true").lower() == "true"

if DEBUG_MODE:
    logger.setLevel(logging.DEBUG)
    LOG_HAIKU = False
    POST_HAIKU = False
    POST_AS_REPLY = False
    FOLLOW_POET = False
    EVERY_N_SECONDS = 1
    DELETE_OLDER_THAN_DAYS = None
    ROWS_TO_KEEP = None
else:
    logger.setLevel(logging.INFO)
    LOG_HAIKU = True
    POST_HAIKU = os.getenv("POST_HAIKU", default="false").lower() == "true"
    POST_AS_REPLY = os.getenv("POST_AS_REPLY", default="false").lower() == "true"
    FOLLOW_POET = os.getenv("FOLLOW_POET", default="false").lower() == "true"
    EVERY_N_SECONDS = int(os.getenv("EVERY_N_SECONDS", default="3600"))
    DELETE_OLDER_THAN_DAYS = os.getenv("DELETE_OLDER_THAN_DAYS", default=None)
    DELETE_OLDER_THAN_DAYS = (
        float(DELETE_OLDER_THAN_DAYS) if DELETE_OLDER_THAN_DAYS else None
    )
    ROWS_TO_KEEP = os.getenv("ROWS_TO_KEEP", default=None)
    ROWS_TO_KEEP = int(ROWS_TO_KEEP) if ROWS_TO_KEEP else None

APP_KEY = os.getenv("API_KEY", default="")
APP_SECRET = os.getenv("API_SECRET", default="")
OAUTH_TOKEN = os.getenv("ACCESS_TOKEN", default="")
OAUTH_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET", default="")
DATABASE_URL = os.getenv("DATABASE_URL", default="")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")
RETRY_WAIT_SECONDS = int(os.getenv("RETRY_WAIT_SECONDS", default="60"))
MY_SCREEN_NAME = os.getenv("MY_SCREEN_NAME", default="twitter")
LANGUAGE = os.getenv("LANGUAGE", default="en")
GUESS_SYL_METHOD = os.getenv("GUESS_SYL_METHOD", default="mean")

IGNORE_USER_SCREEN_NAMES = os.getenv("IGNORE_USER_SCREEN_NAMES", default=None)
IGNORE_USER_SCREEN_NAMES = (
    [x.strip() for x in IGNORE_USER_SCREEN_NAMES.split(",")]
    if IGNORE_USER_SCREEN_NAMES
    else []
)
IGNORE_USER_ID_STR = os.getenv("IGNORE_USER_ID_STR", default=None)
IGNORE_USER_ID_STR = (
    [x.strip() for x in IGNORE_USER_ID_STR.split(",")] if IGNORE_USER_ID_STR else []
)
CHECK_USER_PROFILE = os.getenv("CHECK_USER_PROFILE", default="true").lower() == "true"
CHECK_USER_PROFILE_MATCH_SUBSTRING = (
    os.getenv("CHECK_USER_PROFILE_MATCH_SUBSTRING", default="false").lower() == "true"
)


class MyTwitterClient(Twython):
    """Wrapper around the Twython Twitter client.
    Limits status update rate.
    """

    DEFAULT_LAST_POST_TIME = datetime(1970, 1, 1).replace(tzinfo=pytz.UTC)

    def __init__(self, *args, **kwargs):
        super(MyTwitterClient, self).__init__(*args, **kwargs)
        self.last_post_time = self.get_last_post_time()

    @retry(wait=wait_fixed(RETRY_WAIT_SECONDS))
    def get_last_post_time(self):
        """if our screen_name has a recent tweet, use that timestamp as the time of the
        last post
        """
        if DEBUG_MODE:
            return self.DEFAULT_LAST_POST_TIME

        try:
            most_recent_tweet = self.get_user_timeline(
                screen_name=MY_SCREEN_NAME, count=1, trim_user=True
            )
            if len(most_recent_tweet) > 0:
                last_post_time = date_string_to_datetime(
                    most_recent_tweet[0]["created_at"]
                )
            else:
                # Wait half the rate limit time before making first post
                last_post_time = datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(
                    seconds=EVERY_N_SECONDS // 2
                )
        except TwythonRateLimitError as e:
            logger.info(f"Rate limit exceeded when getting recent tweet: {e}")
            raise
        except Exception as e:
            logger.info(f"Exception when getting recent tweet: {e}")
            last_post_time = self.DEFAULT_LAST_POST_TIME

        return last_post_time

    @retry(wait=wait_fixed(RETRY_WAIT_SECONDS), stop=stop_after_attempt(3))
    def update_status_check_rate(self, *args, **kwargs):
        current_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
        logger.info(f"Current time: {current_time}")
        logger.info(f"Previous post time: {self.last_post_time}")
        logger.info(f"Difference: {current_time - self.last_post_time}")

        posted_status = False
        if (current_time - self.last_post_time).total_seconds() > EVERY_N_SECONDS:
            try:
                self.update_status(*args, **kwargs)
                self.last_post_time = current_time
                logger.info("Success")
                posted_status = True
            except TwythonAuthError as e:
                logger.info(
                    f"Authorization error. Did you create read+write credentials? {e}"
                )
                raise
            except TwythonRateLimitError as e:
                logger.info(f"Rate limit exceeded when posting haiku: {e}")
                raise
            except TwythonError as e:
                logger.info(f"Encountered some other error: {e}")
                raise
        else:
            logger.info(
                "Not posting haiku due to our post limit, once every"
                f" {EVERY_N_SECONDS:,} seconds"
            )

        return posted_status


class MyStreamer(TwythonStreamer):
    def __init__(
        self,
        twitter,
        db_session,
        track_str: str = "",
        ignore_tweet_list: list = [],
        ignore_profile_list: list = [],
        syllable_dict: dict = {},
        emoticons_list: list = [],
        inflect_p=None,
        pronounce_dict: dict = None,
        *args,
        **kwargs,
    ):
        super(MyStreamer, self).__init__(*args, **kwargs)
        self.twitter = twitter
        self.db_session = db_session
        self.track_str = track_str
        self.ignore_tweet_list = ignore_tweet_list
        self.ignore_profile_list = ignore_profile_list
        self.syllable_dict = syllable_dict
        self.emoticons_list = emoticons_list
        self.inflect_p = inflect_p
        self.pronounce_dict = pronounce_dict

    @retry(wait=wait_fixed(RETRY_WAIT_SECONDS))
    def stream_tweets(self):
        # Use try/except to avoid ChunkedEncodingError
        # https://github.com/ryanmcgrath/twython/issues/288#issuecomment-66360160
        try:
            if self.track_str:
                # search specific keywords
                self.statuses.filter(track=self.track_str)
            else:
                # get samples from stream
                self.statuses.sample()
        except TwythonRateLimitError as e:
            logger.info(f"Rate limit exceeded when streaming tweets: {e}")
            raise
        except Exception as e:
            logger.info(f"Exception when streaming tweets: {e}")
            raise

    def on_success(self, status):
        # If this tweet was truncated, get the full text
        if "truncated" in status and status["truncated"]:
            status_full = self.twitter.get_user_timeline(
                user_id=status["user"]["id"],
                tweet_mode="extended",
                max_id=status["id"],
                count=1,
            )
            if status_full and (status_full[0]["id"] == status["id"]):
                logger.debug(f"Retrieved full text for truncated tweet {status['id']}")
                status = status_full[0]
            else:
                logger.debug(f"Didn't get full text for truncated tweet {status['id']}")

        tweet_passes = check_tweet(
            status,
            language=LANGUAGE,
            ignore_user_screen_names=IGNORE_USER_SCREEN_NAMES,
            ignore_user_id_str=IGNORE_USER_ID_STR,
        )

        if not tweet_passes:
            return

        if CHECK_USER_PROFILE:
            profile_passes = check_profile(
                status,
                ignore_profile_list=self.ignore_profile_list,
                match_substring=CHECK_USER_PROFILE_MATCH_SUBSTRING,
            )

            if not profile_passes:
                logger.info(
                    f"Failed check_profile: {status['user']['screen_name']}:"
                    f" {' '.join(status['user']['description'].splitlines())}"
                )
                return

        text_passes = check_text_wrapper(status, ignore_list=self.ignore_tweet_list)

        if not text_passes:
            logger.info(
                f"Failed check_text_wrapper: {status['user']['screen_name']}, tweet"
                f" {status['id_str']}: {get_tweet_body(status)}"
            )
            return

        text = clean_text(get_tweet_body(status))

        haiku = get_haiku(
            text,
            self.inflect_p,
            self.pronounce_dict,
            self.syllable_dict,
            self.emoticons_list,
            GUESS_SYL_METHOD,
        )

        if not haiku:
            return

        # Add it to the database
        tweet_haiku = Haiku.add_haiku(
            self.db_session, status, text, haiku, log_haiku=LOG_HAIKU
        )
        logger.info("=" * 50)
        logger.info(f"Found new haiku:\n{tweet_haiku.haiku}")

        if not DEBUG_MODE:
            # Get haikus from the last hour
            haikus = Haiku.get_haikus_unposted_timedelta(
                self.db_session, td_seconds=EVERY_N_SECONDS
            )

            # Delete old data by row count
            Haiku.keep_haikus_n_rows(self.db_session, n=ROWS_TO_KEEP)

            # Delete old data by timestamp
            Haiku.delete_haikus_unposted_timedelta(
                self.db_session, days=DELETE_OLDER_THAN_DAYS
            )
            Haiku.delete_haikus_posted_timedelta(
                self.db_session, days=DELETE_OLDER_THAN_DAYS
            )
        else:
            # Use the current haiku
            haikus = [tweet_haiku]

        # # Get all unposted haikus
        # haikus = Haiku.get_haikus_unposted(self.db_session)

        if len(haikus) == 0:
            logger.info("No haikus to choose from")
            return

        # Get the haiku to post
        haiku_to_post = get_best_haiku(haikus, self.twitter, self.db_session)
        if haiku_to_post["status_id_str"] == "":
            return

        status = self.twitter.show_status(id=haiku_to_post["status_id_str"])

        # Format the haiku with attribution
        haiku_attributed = (
            f"{haiku_to_post['haiku']}\n\nA haiku by @{status['user']['screen_name']}"
        )

        tweet_url = (
            f"https://twitter.com/{status['user']['screen_name']}"
            f"/status/{status['id_str']}"
        )

        logger.info("=" * 50)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(pformat(status))
            logger.debug(tweet_url)
            logger.debug(f"Original: {haiku_to_post['text_original']}")
            logger.debug(f"Cleaned:  {haiku_to_post['text_clean']}")
        logger.info(f"Haiku to post:\n{haiku_attributed}")

        # Try to post haiku (client checks rate limit time internally)
        if not POST_HAIKU:
            logger.debug(f"Found haiku but did not post: {haiku_attributed}")
            return

        if POST_AS_REPLY:
            logger.info("Attempting to post haiku as reply...")
            # Post a tweet, sending as a reply to the coincidental haiku
            posted_status = self.twitter.update_status_check_rate(
                status=haiku_attributed,
                in_reply_to_status_id=status["id_str"],
                attachment_url=tweet_url,
            )
        else:
            logger.info("Attempting to post haiku, but not as reply...")
            # Post a tweet, but not as a reply to the coincidental haiku
            # The user will not get a notification
            posted_status = self.twitter.update_status_check_rate(
                status=haiku_attributed,
                attachment_url=tweet_url,
            )
        if posted_status:
            logger.info("Attempting to follow this poet...")
            Haiku.update_haiku_posted(self.db_session, haiku_to_post["status_id_str"])

            # follow the user
            if FOLLOW_POET:
                try:
                    followed = self.twitter.create_friendship(
                        screen_name=haiku_to_post["user_screen_name"],
                        # follow: enable notifications
                        follow="false",
                    )
                    if followed["following"]:
                        logger.info("Success")
                    else:
                        logger.info("Could not follow")
                except TwythonError as e:
                    logger.info(e)

    def on_error(self, status_code, content, headers=None):
        content = (
            content.decode().strip() if isinstance(content, bytes) else content.strip()
        )
        logger.info("Error while streaming.")
        logger.info(f"status_code: {status_code}")
        logger.info(f"content: {content}")
        logger.info(f"headers: {headers}")
        if status_code == 420:
            # Server overloaded, try again in a few seconds
            # Exceeded connection limit for user
            # Too many requests recently
            raise TwythonRateLimitError("Too many requests recently")
        else:
            # Unable to decode response
            # (or something else)
            pass


def main():
    logger.info("Initializing dependencies...")

    # get data to use for dealing with tweets
    data_dir = root_dir / "data"
    track_str = get_track_str(data_dir / "track.txt")
    ignore_tweet_list = get_ignore_tweet_list(data_dir / "ignore_tweet.txt")
    ignore_profile_list = get_ignore_profile_list(data_dir / "ignore_profile.txt")
    syllable_dict = get_syllable_dict(data_dir / "syllables.json")
    emoticons_list = get_emoticons_list(data_dir / "emoticons.txt")

    # Use inflect to change digits to their English word equivalent
    inflect_p = inflect.engine()
    # Use the CMU dictionary to count syllables
    pronounce_dict = cmudict.dict()

    # Establish connection to Twitter
    # Uses OAuth1 ("user auth") for authentication
    twitter = MyTwitterClient(
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        oauth_token=OAUTH_TOKEN,
        oauth_token_secret=OAUTH_TOKEN_SECRET,
    )

    # Establish connection to database
    db_session = session_factory(DATABASE_URL)

    logger.info("Initializing tweet streamer...")
    stream = MyStreamer(
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        oauth_token=OAUTH_TOKEN,
        oauth_token_secret=OAUTH_TOKEN_SECRET,
        twitter=twitter,
        db_session=db_session,
        track_str=track_str,
        ignore_tweet_list=ignore_tweet_list,
        ignore_profile_list=ignore_profile_list,
        syllable_dict=syllable_dict,
        emoticons_list=emoticons_list,
        inflect_p=inflect_p,
        pronounce_dict=pronounce_dict,
    )

    logger.info("Looking for haikus...")
    stream.stream_tweets()


if __name__ == "__main__":
    main()
