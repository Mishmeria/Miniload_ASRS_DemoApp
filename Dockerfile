# Use Python 3.10 as base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies including ODBC drivers for SQL Server
RUN apt-get update && apt-get install -y --no-install-recommends \
    unixodbc \
    unixodbc-dev \
    gnupg \
    curl \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port for the web application
EXPOSE 9999

# Expose port for the API server
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create a streamlined requirements file with only necessary dependencies
RUN echo "flet==0.28.3\n\
fastapi==0.104.1\n\
uvicorn==0.24.0\n\
sqlalchemy==2.0.23\n\
pyodbc==4.0.39\n\
pandas==2.1.3\n\
python-dotenv==1.0.0\n\
requests>=2.28.0\n\
matplotlib==3.10.3\n\
schedule==1.2.2" > requirements-minimal.txt

# Command to run both the API server and the web application
CMD ["sh", "-c", "python src/API_Reciever.py & python main.py"]