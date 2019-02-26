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

1. Add phrases to `data/track.txt` to only search for tweets that contain any of the exact strings, one string per line (see [the documentation about `track`](https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters) for more info)
    1. If file does not exist or is empty, gets tweets from the [sample stream](https://developer.twitter.com/en/docs/tweets/sample-realtime/api-reference/get-statuses-sample)
1. Add phrases to `data/ignore.txt` to ignore tweets that contain tokens from any of these strings, one string per line. Uses `AND` and `OR` logic like the track list, but tokens for `AND` (a single line) can match anywhere. Matches substrings (e.g., `dogs` in `ignore.txt` will match `dogs` in a tweet's text).
    1. Whether or not this file exists, by default this program ignores tweets with words read in the `get_ignore_list` function (in `data_utils.py`)
1. Add additional pre-defined syllable counts to `data/syllables.json`
1. `sudo cp haikuincidence.service /etc/systemd/system/haikuincidence.service`
1. `sudo systemctl daemon-reload`
1. `sudo systemctl enable haikuincidence`
1. `sudo systemctl start haikuincidence`

### Logs

- To read systemd's logs (includes log messages from Python): `sudo journalctl -u haikuincidence`
- To follow systemd's logs (includes log messages from Python): `sudo journalctl -f -u haikuincidence`

## Attribution

I borrowed and adapted code from these nice resources. Thank you!

- Default oppressive word filter from [this repo](https://github.com/dariusk/wordfilter)
- Syllable counting from [this script](https://github.com/akkana/scripts/blob/master/countsyl)
- Haiku checker from [this script](https://github.com/tomwardill/python-haiku/blob/master/haiku_checker.py)
- URL regex from [this gist](https://gist.github.com/gruber/8891611)

## License

Copyright (c) 2018 Matt Mollison Licensed under the MIT license.
