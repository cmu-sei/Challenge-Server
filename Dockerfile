FROM python:3.13-slim

WORKDIR /app

# Add required system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    iproute2 \
    iputils-ping \
    open-vm-tools \
    openssh-client \
    sshpass \
    systemd \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src .

EXPOSE 8888
CMD ["python", "app.py"]
