FROM debian:bullseye

# Set working directory
WORKDIR /app

# Install system dependencies and Python 3.10
RUN apt-get update && \
    apt-get install -y \
    curl gnupg2 lsb-release apt-transport-https \
    gcc g++ make python3 python3-pip python3-dev python3-venv \
    unixodbc-dev && \
    curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy all project files
COPY . .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 9999
# Run the renamed Python script
CMD ["python3", "main.py"]
