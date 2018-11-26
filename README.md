# Haikuincidence

Find tweets that contain coincidental haikus, and [tweet these beautiful poems](https://twitter.com/haikuincidence).

```text
You're a poet and
you didn't even know it.
Hey, that's a haiku! ✌️
```

## Environment setup

### Account configuration variables

1. Copy the `config_template.ini` file to `config.ini`, and edit it to include your credentials.

### Install required packages

1. Install Miniconda (Python 3), create a conda environment, and install the requirements.

- https://conda.io/miniconda.html

    ```bash
    $ ./python_env_setup.sh
    ```

### Additional setup

1. Add phrases to `data/ignore.txt` to ignore tweets that contain these exact strings, one string per line
    1. If file does not exist or is empty, does not ignore any tweets
1. Add phrases to `data/track.txt` to only search for tweets that contain any of the exact strings, one string per line (see [the documentation about `track`](https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters) for more info)
    1. If file does not exist or is empty, gets tweets from the [sample stream](https://developer.twitter.com/en/docs/tweets/sample-realtime/api-reference/get-statuses-sample)
1. Add additional pre-defined syllable counts to `data/syllables.json`
1. `sudo cp haikuincidence.service /etc/systemd/system/haikuincidence.service`
1. `sudo systemctl daemon-reload`
1. `sudo systemctl enable haikuincidence`
1. `sudo systemctl start haikuincidence`

### Logs

- To read systemd's logs (includes log messages from Python): `sudo journalctl -u haikuincidence`
- To follow systemd's logs (includes log messages from Python): `sudo journalctl -f -u haikuincidence`

## TODO

- [ ] Retweet with comment, rather than as reply
    - Not sure Twitter's API supports this
- [x] Lower memory requirement method for checking if word is in a dictionary (currently using `spaCy`; maybe try `nltk`?)
    - Reason: Can't install `spaCy` on a GCP `f1-micro` instance
    - [Possible solution](https://stackoverflow.com/questions/3788870/how-to-check-if-a-word-is-an-english-word-with-python)
- [x] Lower memory requirement method for counting syllables (currently using `big-phoney`; maybe a heuristics-based function that counts vowels?)
    - Reason: Can't initialize `big-phoney` on a GCP `f1-micro` instance
    - [Possible solution](https://stackoverflow.com/questions/5513391/code-for-counting-the-number-of-syllables-in-the-words-in-a-file), but won't work if word is not in the dictionary.
- [ ] Decide whether to count pronounced punctuation (e.g., "slash"). Currently not counting.
- [x] Store haiku tweets in a database, set up [like in this example](https://auth0.com/blog/sqlalchemy-orm-tutorial-for-python-developers/)
