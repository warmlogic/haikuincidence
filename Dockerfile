FROM python:3.9-slim-buster

RUN apt-get update && apt-get install build-essential -y

# Create the user that will run the app
RUN adduser --disabled-password --gecos '' app-user

WORKDIR /app

ENV NLTK_DATA /app/nltk_data/

ADD . /app
ADD . $NLTK_DATA

RUN python -m pip install --upgrade pip
RUN python -m pip install poetry
RUN make poetry-install
RUN make nltk-resources

RUN chmod +x run.sh
RUN chown -R app-user:app-user ./

USER app-user

CMD ["bash", "./run.sh"]
