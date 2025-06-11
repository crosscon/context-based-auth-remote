FROM python:3.12.10-alpine3.21

WORKDIR /app

ADD lib/ lib/
ADD requirements.txt .
ADD main.py .
ADD create_keys.py .
ADD demo_signature.py .

RUN pip install -r requirements.txt

EXPOSE 5432
CMD [ "python", "main.py" ]
