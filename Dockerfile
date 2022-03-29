FROM python:3.9-slim-buster

WORKDIR /code
COPY . /code/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

RUN chmod +x /code/*.sh

ENTRYPOINT ["sh", "/code/docker-entrypoint.sh"]