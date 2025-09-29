# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set port environment variable
ENV PORT=5000

# Copy requirements and install dependencies
COPY ../backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code
COPY ../backend/ .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
