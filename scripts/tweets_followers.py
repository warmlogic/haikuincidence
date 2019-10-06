import logging
import os
from pathlib import Path
from time import sleep

from dotenv import load_dotenv
from twython import Twython, TwythonError

logger = logging.getLogger(__name__)
logging.basicConfig(format='{asctime} : {levelname} : {message}', level=logging.INFO, style='{')

IS_PROD = os.getenv("IS_PROD", default=None)

if IS_PROD is None:
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        raise OSError(f"{env_path} not found. Did you set it up?")

APP_KEY = os.getenv("API_KEY", default="")
APP_SECRET = os.getenv("API_SECRET", default="")
OAUTH_TOKEN = os.getenv("ACCESS_TOKEN", default="")
OAUTH_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET", default="")
MY_SCREEN_NAME = os.getenv("MY_SCREEN_NAME", default="haikuincidence")

twitter = Twython(
    app_key=APP_KEY,
    app_secret=APP_SECRET,
    oauth_token=OAUTH_TOKEN,
    oauth_token_secret=OAUTH_TOKEN_SECRET,
)

# https://twython.readthedocs.io/en/latest/api.html

# get the screen names I have replied to
# can only make 1500 requests in a 15-minute window (100 per minute)
# https://developer.twitter.com/en/docs/tweets/timelines/api-reference/get-statuses-user_timeline
sleep_seconds = 1
poets_list = []
mytweets = twitter.get_user_timeline(screen_name=MY_SCREEN_NAME, count=200, exclude_replies='false', include_rts='true')
poets_list.extend([tweet['in_reply_to_screen_name'] for tweet in mytweets])
max_id = mytweets[-1]['id_str']
while True:
    logging.info(f'Tweet max id: {max_id}')
    mytweets = twitter.get_user_timeline(screen_name=MY_SCREEN_NAME, count=200, exclude_replies='false', include_rts='true', max_id=max_id)
    max_id_next = mytweets[-1]['id_str']
    if max_id_next == max_id:
        break
    else:
        max_id = max_id_next
    poets_list.extend([tweet['in_reply_to_screen_name'] for tweet in mytweets])
    logging.info(f'Sleeping for {sleep_seconds} seconds')
    sleep(sleep_seconds)

poets_list = list(set([sn for sn in poets_list if sn]))

# get the screen names I follow
# can only make 15 requests in a 15-minute window
# https://developer.twitter.com/en/docs/accounts-and-users/follow-search-get-users/api-reference/get-friends-list
sleep_seconds = 65
cursor_if = -1
i_follow_list = []
while True:
    logging.info(f'I follow cursor: {cursor_if}')
    ifollow = twitter.get_friends_list(screen_name=MY_SCREEN_NAME, count=200, skip_status='true', cursor=cursor_if)
    if len(ifollow['users']) == 0:
        break
    cursor_if = ifollow['next_cursor']
    i_follow_list.extend([user['screen_name'] for user in ifollow['users']])
    # # find the screen names with notifications turned on
    # i_follow_list.extend([user['screen_name'] for user in ifollow['users'] if user['notifications']])
    logging.info(f'Sleeping for {sleep_seconds} seconds')
    sleep(sleep_seconds)


# get the screen names that follow me
# can only make 15 requests in a 15-minute window
# https://developer.twitter.com/en/docs/accounts-and-users/follow-search-get-users/api-reference/get-followers-list
sleep_seconds = 65
cursor_fm = -1
follow_me_list = []
while True:
    logging.info(f'Follow me cursor: {cursor_fm}')
    followme = twitter.get_followers_list(screen_name=MY_SCREEN_NAME, count=200, skip_status='true', cursor=cursor_fm)
    if len(followme['users']) == 0:
        break
    cursor_fm = followme['next_cursor']
    follow_me_list.extend([user['screen_name'] for user in followme['users']])
    logging.info(f'Sleeping for {sleep_seconds} seconds')
    sleep(sleep_seconds)


# unfollow poets who no longer follow me
# https://developer.twitter.com/en/docs/accounts-and-users/follow-search-get-users/api-reference/post-friendships-destroy
unfollowed_list = []
sleep_seconds = 0.1
to_unfollow_list = [sn for sn in i_follow_list if sn and (sn in poets_list) and (sn not in follow_me_list) and (sn not in unfollowed_list)]
for sn in to_unfollow_list:
    if sn:
        try:
            unfollowed = twitter.destroy_friendship(screen_name=sn)
            unfollowed_list.append(sn)
            logging.info(f'unfollowed {sn}')
        except TwythonError:
            logging.exception(f'exception for {sn}')
    # logging.info(f'Sleeping for {sleep_seconds} seconds')
    sleep(sleep_seconds)


# # follow accounts I have replied to but not followed
# # https://developer.twitter.com/en/docs/accounts-and-users/follow-search-get-users/api-reference/post-friendships-create
# # update notification settings
# # https://developer.twitter.com/en/docs/accounts-and-users/follow-search-get-users/api-reference/post-friendships-update
# to_follow_list = [sn for sn in poets_list if sn and (sn not in i_follow_list)]
# sleep_seconds = 0.5
# for sn in i_follow_list:
#     if sn:
#         try:
#             # follow='false' means don't turn on notifications
#             followed = twitter.create_friendship(screen_name=sn, follow='false')
#             logging.info(f'followed {sn}')
#             # device='false' means turn off notifications
#             # followed = twitter.update_friendship(screen_name=sn, device='false')
#             # logging.info(f'updated {sn}')
#         except TwythonError:
#             logging.exception(f'exception for {sn}')
#     # logging.info(f'Sleeping for {sleep_seconds} seconds')
#     sleep(sleep_seconds)
