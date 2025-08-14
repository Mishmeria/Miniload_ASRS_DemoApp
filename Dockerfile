# was: FROM python:3.10-slim-bullseye
FROM python:3.11-slim-bullseye

WORKDIR /app

# (keep the rest of your Dockerfile exactly as you had it)
# ODBC + tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl gnupg2 lsb-release apt-transport-https \
      unixodbc-dev \
      iputils-ping net-tools iproute2 traceroute \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
ENV PIP_ROOT_USER_ACTION=ignore
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip --version \
 && pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 7777
CMD ["python", "main.py"]
