# Haikuincidence

Find tweets that contain coincidental haikus.

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
