FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y build-essential default-libmysqlclient-dev --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy sources
COPY . /app

# Install Python deps
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

ENV FLASK_APP=pkg
ENV FLASK_ENV=production

EXPOSE 8080

CMD ["python", "run.py"]
