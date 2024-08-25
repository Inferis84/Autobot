FROM python:3.12.5-slim

WORKDIR /app

COPY . /app/

CMD ["python autobot.py"]