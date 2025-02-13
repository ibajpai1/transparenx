# Use Python 3.12 slim
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create and set permissions for .env file
RUN touch .env && chmod 666 .env

# Expose port 80
EXPOSE 80

# Command to run the application
CMD ["python", "app.py"]