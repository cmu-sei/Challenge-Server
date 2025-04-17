FROM python:3.13

WORKDIR /app

# Add required system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    procps \
    net-tools \
    curl \
    sshpass \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src .

EXPOSE 8888
CMD ["python", "app.py"]
