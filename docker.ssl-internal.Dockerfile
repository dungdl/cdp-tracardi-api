FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10

RUN apt-get update
RUN apt-get install -y git

# set the working directory in the container
RUN mkdir app/
WORKDIR /app

## Install dependencies
COPY app/requirements.txt .
RUN pip install wheel
RUN pip --default-timeout=180 install -r requirements.txt

## Copy application
COPY app app/
COPY uix uix/
COPY ssl ssl/

# Remove test page

RUN rm -rf app/tracker/index.html
RUN rm -rf app/tracker/index.css

WORKDIR /

## Copy manual
COPY docs docs/
COPY mkdocs.yml /

## Install docs dependencies
RUN pip --default-timeout=240 install -r docs/requirements.txt

# Install manual

RUN mkdocs build
RUN mv site app
RUN mv docs app

ENV VARIABLE_NAME="application"

RUN pip show tracardi
RUN pip list

EXPOSE 443
CMD ["gunicorn", "-b", "0.0.0.0:443", "--workers", "25", "--keyfile", "/app/ssl/key.pem", "--certfile", "/app/ssl/cert.pem", "-k", "uvicorn.workers.UvicornWorker", "app.main:application"]

