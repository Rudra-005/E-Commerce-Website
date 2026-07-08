FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

# Copy split requirements
COPY requirements/ /app/requirements/
# Also keep legacy requirements.txt for backward compatibility
COPY requirements.txt /app/

# Build arg to select which requirements to install
# Default: dev.txt (all packages) — override per service for smaller images
ARG REQUIREMENTS_FILE=requirements/dev.txt
RUN pip install --upgrade pip \
    && pip install -r ${REQUIREMENTS_FILE}

COPY . /app/
