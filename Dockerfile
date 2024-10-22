FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 libgl1 -y 

RUN pip install --no-cache-dir -r linux-requirements.txt

EXPOSE 5000

ENV FLASK_APP=app/__init__.py

CMD ["flask", "run", "--host=0.0.0.0"]