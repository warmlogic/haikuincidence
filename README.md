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

1. Install Anaconda or Miniconda (Python 3)

- https://conda.io/miniconda.html

1. Create conda environment and install the requirements.

    ```bash
    $ conda create -q --name haiku python=3 -y
    $ conda activate haiku
    $ pip install -r requirements.txt
    ```

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
- [ ] Set up database [like in this example](https://auth0.com/blog/sqlalchemy-orm-tutorial-for-python-developers/)
