FROM python:3.12.5-slim

ADD autobot.py .

RUN pip install discord.py python-dotenv

CMD ["python", "./autobot.py"]