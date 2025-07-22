FROM python:3.10-slim

# Set environment variables to non-interactive
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies + MS SQL ODBC Driver
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gnupg2 \
        curl \
        ca-certificates \
        apt-transport-https \
        lsb-release \
        unixodbc \
        unixodbc-dev && \
    # Add Microsoft GPG key (using modern approach)
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \
    # Add Microsoft repository with proper signing key reference
    echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list && \
    # Update package list
    apt-get update && \
    # Install MSSQL ODBC driver
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Continue with Python setup
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 9999

CMD ["python", "main.py"]

# Reset DEBIAN_FRONTEND
ENV DEBIAN_FRONTEND=