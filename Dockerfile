FROM python:3.7.4-alpine3.10

WORKDIR /app

ADD . /app

RUN pip install --trusted-host pypi.python.org --no-cache-dir -r requirements.txt

RUN sudo cp haikuincidence.service /etc/systemd/system/haikuincidence.service
RUN sudo systemctl daemon-reload
RUN sudo systemctl enable haikuincidence
RUN sudo systemctl start haikuincidence

CMD ["python", "main.py"]
