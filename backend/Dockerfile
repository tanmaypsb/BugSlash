FROM python:3.14-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# System dependencies + analyzer toolchains
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    clang \
    clang-tidy \
    default-jdk \
    maven \
    golang \
    rustc \
    cargo \
    rust-clippy \
    rust-clippy \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Staticcheck is installed from Debian packages
RUN apt-get update && apt-get install -y go-staticcheck && ln -sf /usr/bin/go-staticcheck /usr/local/bin/staticcheck && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install JavaScript dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy BUGSLASH backend
COPY . .

# BUGSLASH API
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
