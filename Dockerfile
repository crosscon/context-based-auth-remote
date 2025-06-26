FROM python:3.12.10-slim

RUN apt update && apt install -y build-essential

WORKDIR /app

ADD lib/ lib/
ADD requirements.txt .
ADD main.py .
ADD create_keys.py .
ADD demo_signature.py .

RUN pip install -r requirements.txt

EXPOSE 5432
CMD [ "python", "main.py" ]
