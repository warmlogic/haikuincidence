import configparser
import logging
import re
# import random
from typing import List, Dict

from text_utils import count_syllables
from data_tweets_haiku import db_update_haiku_deleted

config = configparser.ConfigParser()
config.read('config.ini')

logger_name = config['haiku'].get('logger_name', 'default_logger')

logger = logging.getLogger(logger_name)


def get_haiku(text: str,
              inflect_p,
              pronounce_dict: Dict,
              syllable_dict: Dict,
              emoticons_list: List,
              ) -> str:
    '''Attempt to turn a string into a haiku.
    Returns haiku if able, otherwise returns empty string.

    Maybe TODO: Don't allow an acronym to be split across lines

    Inspired by https://github.com/tomwardill/python-haiku/blob/master/haiku_checker.py
    '''
    haiku_form = [5, 12, 17]
    haiku = [[] for _ in range(len(haiku_form))]
    syllable_count = 0
    haiku_line = 0
    haiku_line_prev = 0

    text_split = text.split()
    # Add tokens to create potential haiku
    for i, token in enumerate(text_split):
        # if logger.isEnabledFor(logging.DEBUG):
        #     logger.debug(f'Token: {token}')
        # Add tokens with no syllables (punctuation, emoji)) to the end of the
        # previous line instead of the start of the current line
        if (re.findall(r"[^\w']", token) and (count_syllables(token, inflect_p, pronounce_dict, syllable_dict, emoticons_list) == 0)):
            if haiku_line_prev == haiku_line:
                haiku[haiku_line].append(token)
            else:
                haiku[haiku_line - 1].append(token)
            continue
        else:
            # Add token to this line of the potential haiku
            haiku[haiku_line].append(token)
            # note what line was being worked on for this token
            haiku_line_prev = haiku_line

        # Count number of syllables for this token
        syllable_count += count_syllables(token, inflect_p, pronounce_dict, syllable_dict, emoticons_list)
        # if logger.isEnabledFor(logging.DEBUG):
        #     logger.debug(f'{syllable_count} syllables counted')

        if syllable_count == haiku_form[haiku_line]:
            # Reached exactly the number of syllables for this line, go to next line
            haiku_line += 1
        if i < len(text_split) - 1 and haiku_line >= len(haiku_form) and (count_syllables(' '.join(text_split[i + 1:]), inflect_p, pronounce_dict, syllable_dict, emoticons_list) > 0):
            # There are syllables in the remaining tokens to check, but have reached the number of lines in a haiku.
            # Therefore not a haiku coincidence!
            # if logger.isEnabledFor(logging.DEBUG):
            #     logger.debug(f"Not a haiku because are more lines to check: {' '.join(text_split[i + 1:])}")
            return ''
    if haiku_line == len(haiku_form):
        # Reached the end, and found the right number of lines. Haiku coincidence!

        # # Put acronyms back together
        # for i, line in enumerate(haiku):
        #     haiku[i] = reform_acronyms(line)

        return ['\n'.join([' '.join(line) for line in haiku])][0]
    else:
        # Did not find the right number of lines. Not a haiku coincidence!
        return ''


def construct_haiku_to_post(h, this_status):
    return {
        'user_id_str': h.user_id_str,
        'user_screen_name': h.user_screen_name,
        'status_id_str': h.status_id_str,
        'favorite_count': this_status['favorite_count'],
        'retweet_count': this_status['retweet_count'],
        'followers_count': this_status['user']['followers_count'],
        'text_original': h.text_original,
        'text_clean': h.text_clean,
        'haiku': h.haiku,
    }


def get_best_haiku(haikus, twitter, session):
    '''Attempt to get the haiku by assessing verified user,
    or number of favorites, retweets, or followers.
    High probability that followers will yield a tweet. Otherwise get the most recent one.

    TODO: If there's more than 1 verified user (extremely unlikely), rank tweets
    '''
    # initialize
    haiku_to_post = {
        'status_id_str': '',
        'favorite_count': 0,
        'retweet_count': 0,
        'followers_count': 0,
    }
    # find the best haiku
    for h in haikus:
        logger.debug(f'Haiku: {h.haiku}')
        try:
            this_status = twitter.show_status(id=h.status_id_str)
        except Exception as e:
            logger.info(f'Exception when checking statuses (1): {e}')
            logger.info(f'{h.user_screen_name}/status/{h.status_id_str}')
            # Tweet no longer exists
            this_status = {}
            # soft delete
            db_update_haiku_deleted(session, h.status_id_str)
        if this_status:
            if this_status['user']['verified']:
                haiku_to_post = construct_haiku_to_post(h, this_status)
            else:
                if this_status['favorite_count'] > haiku_to_post['favorite_count']:
                    haiku_to_post = construct_haiku_to_post(h, this_status)
                elif this_status['retweet_count'] > haiku_to_post['retweet_count']:
                    haiku_to_post = construct_haiku_to_post(h, this_status)
                elif this_status['user']['followers_count'] > haiku_to_post['followers_count']:
                    haiku_to_post = construct_haiku_to_post(h, this_status)

    if haiku_to_post['status_id_str'] == '':
        # # if no tweet was better than another, pick a random one
        # h = random.choice(haikus)
        # if no tweet was better than another, pick the most recent tweet
        for h in haikus[::-1]:
            try:
                this_status = twitter.show_status(id=h.status_id_str)
            except Exception as e:
                logger.info(f'Exception when getting best status (2): {e}')
                logger.info(f'{h.user_screen_name}/status/{h.status_id_str}')
                # Tweet no longer exists, not going to post a haiku this time
                this_status = {}
                # soft delete
                db_update_haiku_deleted(session, h.status_id_str)
            if this_status:
                haiku_to_post = construct_haiku_to_post(h, this_status)
                break

    return haiku_to_post
