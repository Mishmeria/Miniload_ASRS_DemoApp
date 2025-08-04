#!/bin/bash

# Stop and remove the existing Docker container
echo "Stopping existing container..."
docker stop asrs-viewer-app

echo "Removing existing container..."
docker rm asrs-viewer-app

# Remove the existing cloned directory
echo "Removing old project directory..."
rm -rf Miniload_ASRS_DemoApp/

# Clone the new version from GitHub
echo "Cloning latest project from GitHub..."
git clone https://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@github.com/Mishmeria/Miniload_ASRS_DemoApp.git

# Go into the project directory
cd Miniload_ASRS_DemoApp || { echo "Failed to enter directory."; exit 1; }

# Build the Docker image
echo "Building Docker image..."
docker build -t miniload_frontend .

# Run the new container
echo "Starting new container..."
docker run -d -p 7777:7777 --add-host=api-server:10.0.0.2 --name asrs-viewer-app miniload_frontend

echo "Deployment complete."
