import logging
import os
from pathlib import Path
from time import sleep

from dotenv import load_dotenv
from twython import Twython, TwythonError

logging.basicConfig(format='{asctime} : {levelname} : {message}', style='{')
logger = logging.getLogger("tweet_followers")
logger.setLevel(logging.DEBUG)

IS_PROD = os.getenv("IS_PROD", default=None)

if IS_PROD is None:
    env_path = Path.cwd().parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        raise OSError(f"{env_path} not found. Did you set it up?")

APP_KEY = os.getenv("API_KEY", default="")
APP_SECRET = os.getenv("API_SECRET", default="")
OAUTH_TOKEN = os.getenv("ACCESS_TOKEN", default="")
OAUTH_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET", default="")
MY_SCREEN_NAME = os.getenv("MY_SCREEN_NAME", default="haikuincidence")

# Uses OAuth1 ("user auth") for authentication
twitter = Twython(
    app_key=APP_KEY,
    app_secret=APP_SECRET,
    oauth_token=OAUTH_TOKEN,
    oauth_token_secret=OAUTH_TOKEN_SECRET,
)

# https://twython.readthedocs.io/en/latest/api.html

# get the screen names I follow
# can only make 15 requests in a 15-minute window (1 per minute)
# https://developer.twitter.com/en/docs/accounts-and-users/follow-search-get-users/api-reference/get-friends-list
sleep_seconds = 65
cursor_if = -1
i_follow = []
counter = 1
while True:
    logger.info(f'Query {counter}, I follow cursor: {cursor_if}')
    result = twitter.get_friends_list(screen_name=MY_SCREEN_NAME, count=200, skip_status='true', cursor=cursor_if)
    if len(result['users']) == 0:
        break
    else:
        counter += 1
    user_list = [user['screen_name'] for user in result['users']]
    i_follow.extend(user_list)
    cursor_if = result['next_cursor']
    logger.info(f'Added {len(user_list)} users who I follow (total: {len(i_follow)})')
    # # find the screen names with notifications turned on
    # user_list_notif = [user['screen_name'] for user in ifollow['users'] if user['notifications']]
    # logger.info(f'Found {len(user_list_notif)} users with notifications turned on who I follow')
    # i_follow.extend(user_list_notif)
    logger.info(f'Sleeping for {sleep_seconds} seconds')
    sleep(sleep_seconds)

i_follow = list(set([sn for sn in i_follow if sn]))


# get the screen names that follow me
# can only make 15 requests in a 15-minute window (1 per minute)
# https://developer.twitter.com/en/docs/accounts-and-users/follow-search-get-users/api-reference/get-followers-list
sleep_seconds = 65
cursor_fm = -1
follows_me = []
counter = 1
while True:
    logger.info(f'Query {counter}, Follow me cursor: {cursor_fm}')
    result = twitter.get_followers_list(screen_name=MY_SCREEN_NAME, count=200, skip_status='true', cursor=cursor_fm)
    if len(result['users']) == 0:
        break
    else:
        counter += 1
    user_list = [user['screen_name'] for user in result['users']]
    follows_me.extend(user_list)
    cursor_fm = result['next_cursor']
    logger.info(f'Added {len(user_list)} users who follow me (total: {len(follows_me)})')
    logger.info(f'Sleeping for {sleep_seconds} seconds')
    sleep(sleep_seconds)

follows_me = list(set([sn for sn in follows_me if sn]))


# unfollow people I follow who do not follow me, to make room for following more new poets
# https://developer.twitter.com/en/docs/accounts-and-users/follow-search-get-users/api-reference/post-friendships-destroy
unfollowed = []
does_not_follow_me = set(i_follow) - set(follows_me)
to_unfollow = list(set([sn for sn in does_not_follow_me if (sn not in unfollowed)]))
sleep_seconds = 0.1
for sn in to_unfollow:
    if sn:
        try:
            result = twitter.destroy_friendship(screen_name=sn)
            unfollowed.append(sn)
            logger.info(f'unfollowed {len(unfollowed)} / {len(to_unfollow)}: {sn}')
        except TwythonError:
            logger.exception(f'exception for {sn}')
    # logger.info(f'Sleeping for {sleep_seconds} seconds')
    sleep(sleep_seconds)


# get the screen names I have replied to
# with user auth, can only make 900 requests in a 15-minute window (60 per minute)
# if instead was using app auth, could make 1500 requests in a 15-minute window (100 per minute)
# Twitter's API limits this to the most recent 3200 tweets, there's no way around this limit
# https://developer.twitter.com/en/docs/tweets/timelines/api-reference/get-statuses-user_timeline
counter = 1
poets = []
mytweets = twitter.get_user_timeline(screen_name=MY_SCREEN_NAME, count=200, exclude_replies='false', include_rts='true')
poets.extend([tweet['in_reply_to_screen_name'] for tweet in mytweets])
max_id = mytweets[-1]['id_str']
sleep_seconds = 1.1
while True:
    logger.info(f'Query {counter}, Tweet max id: {max_id}')
    mytweets = twitter.get_user_timeline(screen_name=MY_SCREEN_NAME, count=200, exclude_replies='false', include_rts='true', max_id=max_id)
    max_id_next = mytweets[-1]['id_str']
    if max_id_next == max_id:
        break
    else:
        max_id = max_id_next
        counter += 1
    user_list = [tweet['in_reply_to_screen_name'] for tweet in mytweets]
    poets.extend(user_list)
    logger.info(f'Added {len(user_list)} users who I have replied to (total: {len(poets)})')
    logger.info(f'Sleeping for {sleep_seconds} seconds')
    sleep(sleep_seconds)

poets = list(set([sn for sn in poets if sn]))


# follow accounts I have replied to but not followed
# can only make 400 requests in a 24-hour window, also seems to require waiting a bit between requests
# https://developer.twitter.com/en/docs/accounts-and-users/follow-search-get-users/api-reference/post-friendships-create
# update notification settings
# https://developer.twitter.com/en/docs/accounts-and-users/follow-search-get-users/api-reference/post-friendships-update
followed = []  # don't overwrite this
do_not_follow = []  # don't overwrite this
to_follow = list(set([sn for sn in poets if sn and (sn not in i_follow) and (sn not in followed) and (sn not in do_not_follow)]))
stop_reasons = [
    "You are unable to follow more people at this time",
]
exclude_reasons = [
    "Cannot find specified user",
    "You have been blocked from following",
]
sleep_seconds = 5
for sn in to_follow:
    if sn:
        try:
            # follow='false' means don't turn on notifications
            result = twitter.create_friendship(screen_name=sn, follow='false')
            followed.append(sn)
            logger.info(f'followed {len(followed)} / {len(to_follow)}: {sn}')
            # device='false' means turn off notifications
            # result = twitter.update_friendship(screen_name=sn, device='false')
            # logger.info(f'updated {len(followed)} / {len(to_follow)}: {sn}')
        except TwythonError as e:
            logger.exception(f'exception for {sn}')
            # remove the screenname from the list if it matches a valid reason
            if any([reason in str(e) for reason in exclude_reasons]):
                do_not_follow.append(sn)
            elif any([reason in str(e) for reason in stop_reasons]):
                break

    logger.info(f'Sleeping for {sleep_seconds} seconds')
    sleep(sleep_seconds)

to_follow = [sn for sn in to_follow if sn not in do_not_follow]
