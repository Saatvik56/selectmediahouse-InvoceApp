# Use the official Microsoft Playwright Python image
# This comes with Python and the necessary browser dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.48.0-focal

# Set the working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the specific browsers required by Playwright (Chromium only to save space)
RUN playwright install chromium

# Copy the rest of the application code
COPY . .

# Expose the port
EXPOSE 8000

# Run the application with Gunicorn
# CRITICAL: We use --workers 1 because of the in-memory INVOICE_DATA_CACHE
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120", "app:app"]