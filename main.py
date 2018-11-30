import configparser
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from pprint import pformat
import pytz
# import random
import re
import time

from ftfy import fix_text
import inflect
from nltk.corpus import cmudict
from twython import Twython
from twython import TwythonStreamer

from data_base import session_factory
from data_tweets_haiku import Haiku

# I'm a poet and I didn't even know it. Hey, that's a haiku!

DEBUG = False

# Whether to post as a reply (user gets notification) or not (no notification)
POST_AS_REPLY = True

if DEBUG:
    logging.basicConfig(format='{asctime} : {levelname} : {message}', level=logging.DEBUG, style='{')
    post_haiku = False
else:
    logging.basicConfig(format='{asctime} : {levelname} : {message}', level=logging.INFO, style='{')
    post_haiku = True
logger = logging.getLogger(__name__)

# Minimum amount of time between haiku posts
if DEBUG:
    EVERY_N_SECONDS = 1  # 1 second
    INITIAL_TIME = 0
else:
    # EVERY_N_SECONDS = 600  # 10 minutes
    # EVERY_N_SECONDS = 1800  # 30 minutes
    EVERY_N_SECONDS = 3600  # 1 hour
    # Wait half the rate limit time before making first post
    INITIAL_TIME = int(time.monotonic()) - (EVERY_N_SECONDS // 2)

# track tweets that contain any of these words
if (Path('data') / 'track.txt').exists():
    with open(Path('data') / 'track.txt') as fp:
        track_str = ','.join(fp.read().splitlines())
else:
    track_str = ''

# ignore tweets that contain any of these words
if (Path('data') / 'ignore.txt').exists():
    with open(Path('data') / 'ignore.txt') as fp:
        ignore_list = fp.read().splitlines()
    # ensure lowercase
    ignore_list = set(x.lower() for x in ignore_list)
else:
    ignore_list = []

# Specify syllables for certain acronyms or abbreviations
if (Path('data') / 'syllables.json').exists():
    with open(Path('data') / 'syllables.json', 'r') as fp:
        syllable_dict = json.loads(fp.read())
    # ensure lowercase
    syllable_dict = {k.lower(): v for k, v in syllable_dict.items()}
else:
    syllable_dict = {}

# Regex to look for URLs https://gist.github.com/gruber/8891611
url_re = re.compile(r'(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))')

logger.info('Initializing dependencies...')

config = configparser.ConfigParser()
config.read('config.ini')


class MyTwitterClient(Twython):
    '''Wrapper around the Twython Twitter client.
    Limits status update rate.
    '''
    def __init__(self, every_n_seconds=3600, initial_time=None, *args, **kwargs):
        super(MyTwitterClient, self).__init__(*args, **kwargs)
        if initial_time is None:
            # Wait half the rate limit time before making first post
            initial_time = int(time.monotonic()) - (every_n_seconds // 2)
        # self.twitter = twitter
        self.every_n_seconds = every_n_seconds
        self.last_post_time = initial_time

    def update_status_check_rate(self, *args, **kwargs):
        current_time = int(time.monotonic())
        logger.info(f'Current time: {current_time}')
        logger.info(f'Previous post time: {self.last_post_time}')
        logger.info(f'Difference: {current_time - self.last_post_time}')
        if (current_time - self.last_post_time) > self.every_n_seconds:
            self.update_status(*args, **kwargs)
            self.last_post_time = current_time
            logger.info('Success')
            return True
        else:
            logger.info('Not posting haiku due to rate limit')
            return False


# Establish connection to Twitter
twitter = MyTwitterClient(
    every_n_seconds=EVERY_N_SECONDS,
    initial_time=INITIAL_TIME,
    app_key=config['twitter'].get('api_key', ''),
    app_secret=config['twitter'].get('api_secret', ''),
    oauth_token=config['twitter'].get('access_token', ''),
    oauth_token_secret=config['twitter'].get('access_token_secret', ''),
)

# Establish connection to database
session = session_factory()

# Use inflect to change digits to their English word equivalent
inflect_p = inflect.engine()
# Use the CMU dictionary to count syllables
pronounce_dict = cmudict.dict()


def remove_repeat_last_letter(text: str):
    if text:
        return re.sub(rf'({text[-1]})\1+$', r'\1', text)
    else:
        return ''


def text_contains_url(text):
    return len(url_re.findall(text)) > 0


def text_has_chars_digits_together(text):
    '''It's not easy to count syllables for a token that contains letters and digits (h3llo).
    Return True if we find one of those.
    '''
    # keep only letters and spaces
    text_split = re.sub(r'[^\w\s]', '', text).split()
    # count number of tokens that are solely digits
    num_nums = sum(sum(char.isdigit() for char in token) == len(token) for token in text_split)
    # count number of tokens that are solely letters
    num_words = sum(sum(char.isalpha() for char in token) == len(token) for token in text_split)
    # are the counts above different from the length of tokens?
    return num_nums + num_words != len(text_split)


def text_is_all_uppercase(text):
    '''Return True if every character is uppercase.
    Excludes punctuation, spaces, and digits.
    '''
    return all([char.isupper() for char in re.sub(r'[^A-Za-z]', '', text)])


# def text_is_all_alpha(text):
#     '''Return True if every character is a letter.
#     Excludes punctuation and spaces.
#     '''
#     return all([char.isalpha() for char in re.sub(r'[^\w]', '', text)])


def any_token_in_ignore_list(text):
    '''Return True if any token is in the ignore_list
    '''
    return any((re.sub(r"[^\w']", '', token).lower() in ignore_list)
               for token in text.split())


def all_tokens_are_real(text):
    '''Return True if all tokens are real words (in spaCy English dictionary) or
    in syllable dictionary
    '''
    # Keep characters and apostrphes
    return all(
        (re.sub(r"[^\w']", '', token) and
            ((re.sub(r"[^\w']", '', token).lower() in pronounce_dict) or
             (re.sub(r"[^\w']", '', token).lower() in syllable_dict) or
             (remove_repeat_last_letter(
                 re.sub(r"[^\w']", '', token).lower()) in pronounce_dict) or
             (remove_repeat_last_letter(
                 re.sub(r"[^\w']", '', token).lower()) in syllable_dict))
         ) for token in text.split()
    )


def clean_text(text):
    '''Process text so it's ready for syllable counting
    '''
    def split_acronym(token):
        '''Split short acronyms. One option for all caps, one for lowercase.
        Otherwise return the token.
        '''
        if len(token) <= 5 and re.findall(r'\b[A-Z\.]{2,}s?\b', token):
            return ' '.join(token).split()
        elif len(token) <= 3 and re.findall(r'\b[a-z\.]{2,}s?\b', token):
            return ' '.join(token).split()
        else:
            return [token]

    # fix wonky characters
    text = fix_text(text)

    # # remove URLs
    # text = re.sub(r'http\S+', '', text)

    # split and rejoin to remove newlines
    text = ' '.join(text.split())

    text_final = []
    for token in text.split():
        # If it's a real word or is in the custom dictionary, keep it as is.
        # Try to split it if it's an acronym, or just keep it as is.
        if all_tokens_are_real(token):
            text_final.append(token)
        else:
            text_final.extend(split_acronym(token))

    text_final = ' '.join(text_final)

    # remove space before some punctuation ("hello ,how are you ? doing")
    text_final = re.sub(r'\s([.,;!?](?=\s|$)?)', r'\1', text_final)

    # put space after some punctuation if followed by a letter or number
    text_final = re.sub(r'(?<=[.,;!?])(?=[\w])', r' ', text_final)

    # remove spaces around apostrophe if letter-space-apostrophe-space-letter
    text_final = re.sub(r"(\w)\s[']\s(\w)", r"\1'\2", text_final)

    text_final = ' '.join(text_final.split())
    return text_final


def check_tweet(status):
    '''Return True if tweet satisfies specific criteria
    '''
    return (
        (not text_contains_url(status['text'])) and
        (not any_token_in_ignore_list(status['text'])) and
        (not text_has_chars_digits_together(status['text'])) and
        (not text_is_all_uppercase(status['text'])) and
        # (all_tokens_are_real(status['text'])) and
        (status['lang'] == 'en') and
        (not status['entities']['hashtags']) and
        (not status['entities']['urls']) and
        (not status['entities']['user_mentions']) and
        (not status['entities']['symbols']) and
        (not status['truncated']) and
        (not status['is_quote_status']) and
        (not status['in_reply_to_status_id_str']) and
        (not status['retweeted']) and
        (status['user']['friends_count'] > 10) and  # following
        (status['user']['followers_count'] > 100) and  # followers
        # (status['user']['verified']) and
        # '(media' not in status['entities']) and
        (len(status['text']) >= 17)
    )


def get_haiku(text: str) -> str:
    '''Attempt to turn a string into a haiku.
    Returns haiku if able, otherwise returns empty string.

    Maybe TODO: Don't allow an acronym to be split across lines

    Inspired by https://github.com/tomwardill/python-haiku/blob/master/haiku_checker.py
    '''
    # def reform_acronyms(text):
    #     '''TODO
    #     NB: Will only work if an acronym can't be split across lines
    #     '''
    #     return text

    def count_syllables(token):
        # add space around some punctuation if letters on both sides
        token = re.sub(r'([\w])([#@%=+&/\-](?=[\w]|$))', r'\1 \2 ', token)

        # put a space after some punctuation that precedes a letter
        token = re.sub(r'([#@%=+&/])((?=[\w]|$))', r'\1 \2', token)

        # put a space before a some punctuation that follows a letter
        token = re.sub(r'([\w])?([#@%=+&/])', r'\1 \2', token)

        # replace some punctuation with words
        token = token.replace('#', 'hashtag')
        token = token.replace('@', 'at')
        token = token.replace('%', 'percent')
        token = token.replace('=', 'equals')
        token = token.replace('+', 'plus')
        token = token.replace('&', 'and')
        # token = token.replace('/', 'slash')

        # keep letters and apostrophes
        token_clean = re.sub(r"[^\w']", ' ', token).lower()

        subsyllable_count = 0
        for subtoken in token_clean.split():
            # remove starting or ending apostrophes
            if subtoken[0] == "'":
                subtoken = subtoken[1:]
            elif subtoken[-1] == "'":
                subtoken = subtoken[:-1]

            # if logger.isEnabledFor(logging.DEBUG):
            #     logger.debug(f'    Subtoken: {subtoken}')
            if subtoken.isdigit():
                # split a string that looks like a year
                if len(subtoken) == 4:
                    if (subtoken[:2] == '18') or (subtoken[:2] == '19'):
                        subtoken = f'{subtoken[:2]} {subtoken[2:]}'
                    else:
                        subtoken = inflect_p.number_to_words(subtoken, andword='')
                else:
                    subtoken = inflect_p.number_to_words(subtoken, andword='')
            if subtoken in syllable_dict:
                subsyllable_count += syllable_dict[subtoken]['syllables']
                # if logger.isEnabledFor(logging.DEBUG):
                #     logger.debug(f"    Dict: {subtoken}: {syllable_dict[subtoken]['syllables']}")
            elif remove_repeat_last_letter(subtoken) in syllable_dict:
                subtoken = remove_repeat_last_letter(subtoken)
                subsyllable_count += syllable_dict[subtoken]['syllables']
                # if logger.isEnabledFor(logging.DEBUG):
                #     logger.debug(f"    Dict: {subtoken}: {syllable_dict[subtoken]['syllables']}")
            elif subtoken in pronounce_dict:
                subsyllable_count += max([len([y for y in x if y[-1].isdigit()]) for x in pronounce_dict[subtoken]])
                # if logger.isEnabledFor(logging.DEBUG):
                #     logger.debug(f"    CMU: {subtoken}: {max([len([y for y in x if y[-1].isdigit()]) for x in pronounce_dict[subtoken]])}")
            elif remove_repeat_last_letter(subtoken) in pronounce_dict:
                subtoken = remove_repeat_last_letter(subtoken)
                subsyllable_count += max([len([y for y in x if y[-1].isdigit()]) for x in pronounce_dict[subtoken]])
                # if logger.isEnabledFor(logging.DEBUG):
                #     logger.debug(f"    CMU: {subtoken}: {max([len([y for y in x if y[-1].isdigit()]) for x in pronounce_dict[subtoken]])}")
            else:
                # it's not a "real" word
                # if there are non-letter characters remaining
                if re.findall(r"[^\w']", subtoken):
                    subsyllable_count += count_syllables(subtoken)
                else:
                    # split on non-possessive apostrophe and guess syllables
                    if (len(subtoken) > 2 and subtoken[-2:] == "'s"):
                        subsyllable_count += guess_syllables(subtoken)[0]
                    else:
                        for subsubtoken in subtoken.split("'"):
                            subsyllable_count += guess_syllables(subsubtoken)[0]
                            # if logger.isEnabledFor(logging.DEBUG):
                            #     logger.debug(f"    Guess: {subsubtoken}: {guess_syllables(subsubtoken)[0]}")

        return subsyllable_count

    def guess_syllables(word, verbose=False):
        '''Adapted from https://github.com/akkana/scripts/blob/master/countsyl
        '''
        vowels = ['a', 'e', 'i', 'o', 'u']

        on_vowel = False
        in_diphthong = False
        minsyl = 0
        maxsyl = 0
        lastchar = None

        word = word.lower()
        for c in word:
            is_vowel = c in vowels

            if on_vowel is None:
                on_vowel = is_vowel

            # y is a special case
            if c == 'y':
                is_vowel = not on_vowel

            if is_vowel:
                if verbose:
                    print(f"{c} is a vowel")
                if not on_vowel:
                    # We weren't on a vowel before.
                    # Seeing a new vowel bumps the syllable count.
                    if verbose:
                        print("new syllable")
                    minsyl += 1
                    maxsyl += 1
                elif on_vowel and not in_diphthong and c != lastchar:
                    # We were already in a vowel.
                    # Don't increment anything except the max count,
                    # and only do that once per diphthong.
                    if verbose:
                        print(f"{c} is a diphthong")
                    in_diphthong = True
                    maxsyl += 1
            else:
                if re.findall(r'[\w]', c):
                    if verbose:
                        print("[consonant]")
                else:
                    if verbose:
                        print("[other]")

            on_vowel = is_vowel
            lastchar = c

        # Some special cases:
        if word[-1] == 'e':
            minsyl -= 1
        # if it ended with a consonant followed by y, count that as a syllable.
        if word[-1] == 'y' and not on_vowel:
            maxsyl += 1

        # if found no syllables but there's at least one letter,
        # count as one syllable
        if re.findall(r'[\w]', word):
            if not minsyl:
                minsyl = 1
            if not maxsyl:
                maxsyl = 1

        return minsyl, maxsyl

    haiku_form = [5, 12, 17]
    haiku = [[] for _ in range(len(haiku_form))]
    syllable_count = 0
    haiku_line = 0

    text_split = text.split()
    # Add tokens to create potential haiku
    for i, token in enumerate(text_split):
        # if logger.isEnabledFor(logging.DEBUG):
        #     logger.debug(f'Token: {token}')
        # Add punctuation (with no syllables) to the end of the previous line
        if ((haiku_line > 0) and re.findall(r"[^\w']", token) and (count_syllables(token) == 0)):
            haiku[haiku_line - 1].append(token)
            continue
        else:
            # Add token to this line of the potential haiku
            haiku[haiku_line].append(token)

        # Count number of syllables for this token
        syllable_count += count_syllables(token)
        # if logger.isEnabledFor(logging.DEBUG):
        #     logger.debug(f'{syllable_count} syllables counted')

        if syllable_count == haiku_form[haiku_line]:
            # Reached the number of syllables for this line, go to next line
            haiku_line += 1
        if i < len(text_split) - 1 and haiku_line >= len(haiku_form) and (count_syllables(' '.join(text_split[i + 1:])) > 0):
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


def add_haiku(tweet_haiku):
    '''Add haiku record to the database
    '''
    try:
        session.add(tweet_haiku)
        session.commit()
    except Exception as e:
        logger.info(f'Exception when adding haiku: {e}')
        session.rollback()


def get_haikus_all():
    '''Get all records
    '''
    haiku_query = session.query(Haiku)
    return haiku_query.all()


def get_haikus_unposted():
    '''Get all unposted records
    '''
    haiku_query = session.query(Haiku).filter(
        Haiku.date_posted == None).filter(Haiku.date_deleted == None)
    return haiku_query.all()


def get_haikus_unposted_timedelta(td_seconds=None):
    '''Get all unposted records from the last N seconds
    '''
    if td_seconds is None:
        td_seconds = EVERY_N_SECONDS
    filter_td = datetime.now().replace(tzinfo=pytz.UTC) - timedelta(seconds=td_seconds)
    haiku_query = session.query(Haiku).filter(
        Haiku.created_at > filter_td).filter(
            Haiku.date_posted == None).filter(Haiku.date_deleted == None)
    return haiku_query.all()


def update_haiku_posted(status_id_str):
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


def update_haiku_unposted(status_id_str):
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


def update_haiku_deleted(status_id_str):
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


def update_haiku_undeleted(status_id_str):
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


def get_haiku_to_post(h, this_status):
    return {
        'status_id_str': h.status_id_str,
        'user_screen_name': h.user_screen_name,
        'favorite_count': this_status['favorite_count'],
        'retweet_count': this_status['retweet_count'],
        'followers_count': this_status['user']['followers_count'],
        'text_original': h.text_original,
        'text_clean': h.text_clean,
        'haiku': h.haiku,
    }


def get_best_haiku(haikus):
    '''Attempt to get the haiku by assessing verified user,
    or number of favorites, retweets, or followers.
    High probability that followers will yield a tweet. Otherwise get the most recent one.
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
        logging.debug(f'Haiku: {h.haiku}')
        try:
            this_status = twitter.show_status(id=h.status_id_str)
        except Exception as e:
            logger.info(f'Exception when checking statuses (1): {e}')
            logging.info(f'{h.user_screen_name}/status/{h.status_id_str}')
            # Tweet no longer exists
            this_status = {}
            # soft delete
            update_haiku_deleted(h.status_id_str)
        if this_status:
            if this_status['user']['verified']:
                haiku_to_post = get_haiku_to_post(h, this_status)
            else:
                if this_status['favorite_count'] > haiku_to_post['favorite_count']:
                    haiku_to_post = get_haiku_to_post(h, this_status)
                elif this_status['retweet_count'] > haiku_to_post['retweet_count']:
                    haiku_to_post = get_haiku_to_post(h, this_status)
                elif this_status['user']['followers_count'] > haiku_to_post['followers_count']:
                    haiku_to_post = get_haiku_to_post(h, this_status)
    if haiku_to_post['status_id_str'] == '':
        # # if no tweet was better than another, pick a random one
        # h = random.choice(haikus)
        # if no tweet was better than another, pick the most recent tweet
        for h in haikus[::-1]:
            try:
                this_status = twitter.show_status(id=h.status_id_str)
            except Exception as e:
                logger.info(f'Exception when getting best status (2): {e}')
                logging.info(f'{h.user_screen_name}/status/{h.status_id_str}')
                # Tweet no longer exists, not going to post a haiku this time
                this_status = {}
                # soft delete
                update_haiku_deleted(h.status_id_str)
            if this_status:
                haiku_to_post = get_haiku_to_post(h, this_status)
                break
    return haiku_to_post


class MyStreamer(TwythonStreamer):
    def on_success(self, status):
        if 'text' in status and check_tweet(status):
            # print(status['text'])
            text = clean_text(status['text'])
            if text:
                haiku = get_haiku(text)
                if haiku:
                    # add tweet to database
                    tweet_haiku = Haiku(
                        status['id_str'],
                        status['user']['screen_name'],
                        status['user']['id_str'],
                        status['user']['verified'],
                        datetime.strptime(
                            status['created_at'],
                            '%a %b %d %H:%M:%S +0000 %Y').replace(tzinfo=pytz.UTC),
                        status['text'],
                        text,
                        haiku,
                        None,
                        None,
                    )
                    if not DEBUG:
                        add_haiku(tweet_haiku)
                    logger.info('=' * 50)
                    logger.info(f"Found new haiku:\n{tweet_haiku.haiku}")

                    # Get haikus from the last hour
                    if not DEBUG:
                        haikus = get_haikus_unposted_timedelta(td_seconds=EVERY_N_SECONDS)
                    else:
                        haikus = [tweet_haiku]
                    # haikus = get_haikus_unposted()
                    if len(haikus) > 0:
                        # Get the haiku to post
                        haiku_to_post = get_best_haiku(haikus)
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
                                    update_haiku_posted(haiku_to_post['status_id_str'])
                            else:
                                logger.debug('Found haiku but did not post')
                    else:
                        logger.info('No haikus to choose from')

    def on_error(self, status_code, status):
        logger.error(f'{status_code}, {status}')


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
