FROM python:3.8-slim
ENV PYTHONUNBUFFERED=1
RUN apt-get update
RUN apt-get install

WORKDIR /code
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .

CMD ["python3", "bot.py"]