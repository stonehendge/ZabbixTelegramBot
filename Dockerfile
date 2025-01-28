FROM python:3.12-slim

WORKDIR /app
COPY ./*.py /app
COPY ./*.txt /app
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "/app/start.py"]
