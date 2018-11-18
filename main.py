import configparser
from pprint import pprint
import re

from big_phoney import BigPhoney
from ftfy import fix_text
import spacy
from twython import TwythonStreamer

import logging
logging.basicConfig(format='{asctime} : {levelname} : {message}', level=logging.INFO, style='{')

# https://stackabuse.com/accessing-the-twitter-api-with-python/

# Twitter streaming API:
# https://developer.twitter.com/en/docs/tweets/sample-realtime/api-reference/get-statuses-sample
# https://developer.twitter.com/en/docs/tweets/filter-realtime/api-reference/post-statuses-filter

# Twython: https://github.com/ryanmcgrath/twython
# Twython streaming: https://twython.readthedocs.io/en/latest/usage/streaming_api.html

# Regex to look for URLs
# https://gist.github.com/gruber/8891611
url_re = re.compile(r'(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))')

syllable_dict = {
    'abt': 2,  # about
    'afaik': 5,  # as far as I know
    'afk': 3,  # A F K
    'aka': 3,  # A K A
    'asap': 4,  # A S A P
    'atm': 4,  # at the moment
    'awol': 2,  # a-wol
    'bbl': 3,  # B B L / be back later
    'bc': 3,  # B C / because
    'bdrm': 2,  # bedroom
    'bf': 2,  # B F / boyfriend
    'bff': 3,  # B F F
    'bffl': 4,  # B F F L
    'brb': 3,  # B R B / be right back
    # 'btw': 3,  # by the way
    # 'btw': 4,  # B T dubs
    'btw': 5,  # B T W
    'dgaf': 2,  # dee-gaf
    'faq': 3,  # F A Q
    'fomo': 2,  # fomo
    'fml': 3,  # F M L
    'ftw': 3,  # for the win
    'fwiw': 4,  # for what it's worth
    'fyi': 3,  # F Y I
    'gf': 2,  # G F / girlfriend
    'glbt': 4,  # G L B T
    'ha': 1,
    'haha': 2,
    'hahaha': 3,
    'heh': 1,
    'hehe': 2,
    'hehehe': 3,
    'ianal': 6,  # I am not a lawyer
    'idk': 3,  # I D K / I don't know
    'imho': 7,  # in my humble opinion
    'imo': 5,  # in my opinion
    'irl': 3,  # I R L
    'jaja': 2,
    'jajaja': 3,
    'jeje': 2,
    'jejeje': 3,
    'jk': 2,  # J K
    'kthnxbye': 3,
    'kthxbye': 3,
    'ktnxbye': 3,
    'lgbt': 4,  # L G B T
    'lgbti': 5,  # L G B T I
    'lgbtq': 5,  # L G B T Q
    'lmao': 4,  # L M A O
    'lmaoo': 4,  # L M A O
    'lmaooo': 4,  # L M A O
    'lmaoooo': 4,  # L M A O
    'lmfao': 5,  # L M F A O
    'lmfaoo': 5,  # L M F A O
    'lmfaooo': 5,  # L M F A O
    'lmfaoooo': 5,  # L M F A O
    # 'lol': 1,  # lol
    'lol': 3,  # L O L
    'ny': 2,  # N Y / New York
    'nyc': 3,  # N Y C
    'omfg': 4,  # O M F G
    # 'omfg': 5,  # oh my f'ing god
    'omg': 3,  # O M G / oh my god
    # 'op': 2,  # O P
    # 'ot': 3,  # off topic
    'ppl': 2,  # people
    'rofl': 2,  # rofl
    'smdh': 5,  # shaking my damn head
    'smh': 4,  # shaking my head
    'sry': 2,  # sorry
    'stfu': 4,  # shut the f up
    'tba': 3,  # T B A
    'tbd': 3,  # T B D
    'thnx': 1,  # thanks
    'thx': 1,  # thanks
    'tmrw': 3,  # tomorrow
    'tnx': 1,  # thanks
    'ttyl': 5,  # talk to you later
    'tweet': 1,
    'twitter': 2,
    'w': 1,  # with
    'wfh': 3,  # work from home
    'wfm': 3,  # works for me
    # 'wtf': 3,  # what the f
    'wtf': 5,  # W T F
    'wtff': 5,  # W T F
    'wtfff': 5,  # W T F
    'wtffff': 5,  # W T F
    'ymmv': 6,  # your mileage may vary
    'yolo': 2,  # yolo
}

config = configparser.ConfigParser()
config.read('config.ini')

nlp = spacy.load('en')
phoney = BigPhoney()


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


def all_tokens_are_real(text):
    '''Return True if all tokens are real words (in spaCy English dictionary) or
    in syllable dictionary
    '''
    # Keep characters and apostrphes
    return all(((re.sub(r"[^\w']", '', token) in nlp.vocab) or
                (re.sub(r"[^\w']", '', token).lower() in nlp.vocab) or
                (re.sub(r"[^\w']", '', token).lower() in syllable_dict)
                ) for token in text.split())


def clean_text(text):
    '''Process text

    Maybe TODO: deal with typos like 'lmaooooo'
    '''
    def split_acronym(token):
        '''Split short acronyms, only if all caps.
        Otherwise return the token.
        '''
        if len(token) <= 5 and re.findall(r'\b[A-Z\.]{2,}s?\b', token):
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
    return ' '.join(text_final)


def check_tweet(status):
    '''Return True if tweet satisfies specific criteria
    '''
    return (
        (not text_contains_url(status['text'])) and
        (not text_has_chars_digits_together(status['text'])) and
        (not text_is_all_uppercase(status['text'])) and
        # (all_tokens_are_real(status['text'])) and
        (not status['entities']['hashtags']) and
        (not status['entities']['urls']) and
        (not status['entities']['user_mentions']) and
        (not status['entities']['symbols']) and
        (not status['truncated']) and
        # (not status['is_quote_status']) and
        # (status['user']['verified']) and
        # '(media' not in status['entities']) and
        (status['lang'] == 'en') and
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

    haiku_form = [5, 12, 17]
    haiku = [[] for _ in range(len(haiku_form))]
    syllable_count = 0
    haiku_line = 0

    text_split = text.split()
    # Add tokens to create potential haiku
    for i, token in enumerate(text_split):
        # Add punctuation (with no syllables) to the end of the previous line
        if ((haiku_line > 0) and (phoney.count_syllables(token) == 0)):
            haiku[haiku_line - 1].append(token)
            continue
        else:
            # Add token to this line of the potential haiku
            haiku[haiku_line].append(token)

        # Count number of syllables for this token
        token_clean = re.sub(r"[^\w']", '', token).lower()
        if token_clean in syllable_dict:
            syllable_count += syllable_dict[token_clean]
        else:
            syllable_count += phoney.count_syllables(token)

        if syllable_count == haiku_form[haiku_line]:
            # Reached the number of syllables for this line, go to next line
            haiku_line += 1
        if i < len(text_split) - 1 and haiku_line >= len(haiku_form):
            # There are more tokens to check, but have reached the number of lines in a haiku.
            # Therefore not a haiku coincidence!
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


class MyStreamer(TwythonStreamer):
    def on_success(self, status):
        if 'text' in status and check_tweet(status):
            # print(status['text'])
            text = clean_text(status['text'])
            # if text and phoney.count_syllables(text) == 17:
            if text:
                haiku = get_haiku(text)
                if haiku:
                    logging.info('=' * 30)
                    logging.info(pprint(status))
                    logging.info(f"Original: {status['text']}")
                    logging.info(f"Cleaned: {text}")
                    logging.info(f"Haiku:\n{haiku}")

                    # # things to save
                    # status['id_str']
                    # status['user']['screen_name']
                    # status['created_at']
                    # status['text'] # original
                    # text # cleaned
                    # haiku

    def on_error(self, status_code, status):
        logging.error(f'{status_code}, {status}')


# status = ""
# text = clean_text(status)
# print(text)
# get_haiku(text)

if __name__ == '__main__':
    stream = MyStreamer(config['twitter']['consumer_key'], config['twitter']['consumer_secret'],
                        config['twitter']['access_token_key'], config['twitter']['access_token_secret'])

    while True:
        # Use try/except to avoid ChunkedEncodingError
        # https://github.com/ryanmcgrath/twython/issues/288
        try:
            stream.statuses.sample()
            # # search a specific key word
            # stream.statuses.filter(track='twitter')
        except Exception as e:
            logging.warning(f'{e}')
            continue
