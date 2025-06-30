#!/bin/bash

# ReadList Assistant - Database Refresh Script
# 
# This script automates the weekly database refresh process for the ReadList Assistant.
# It processes multiple recent episodes from Spotify and updates the book recommendations
# database with new content.
# 
# Features:
# - Environment variable loading from .env file
# - Virtual environment activation
# - Backend service management (start if not running)
# - Batch episode processing (5 most recent episodes)
# - Email notifications for success/failure
# - Comprehensive logging to refresh.log
# - Error handling and graceful failure
# 
# Usage:
# - Run manually: ./refresh_db.sh
# - Schedule with cron: 0 9 * * 1 /path/to/refresh_db.sh
# 
# Dependencies:
# - .env file with EMAIL_TO variable
# - Python virtual environment
# - mail command for notifications
# - curl for API communication
# 
# Author: ReadList Assistant Team

# Load environment variables from .env file
ENV_FILE="$(dirname "$0")/../.env"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
else
    echo "ERROR: .env file not found at $ENV_FILE"
    exit 1
fi

# Check if EMAIL_TO is set
if [ -z "$EMAIL_TO" ]; then
    echo "ERROR: EMAIL_TO variable is not set in .env file"
    exit 1
fi

# Configuration
LOG_FILE="$(dirname "$0")/../logs/refresh.log"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
VENV_PATH="$(dirname "$0")/../venv/bin/activate"

# Function to send email
send_email() {
    local subject="$1"
    local body="$2"
    echo "$body" | mail -s "$subject" "$EMAIL_TO"
}

# Function to log messages
log_message() {
    local message="$1"
    echo "[$TIMESTAMP] $message" | tee -a "$LOG_FILE"
}

# Change to the project directory
cd "$(dirname "$0")/.." || {
    log_message "ERROR: Failed to change to project directory"
    send_email "Database Refresh Failed" "Failed to change to project directory"
    exit 1
}

# Activate virtual environment
if [ -f "$VENV_PATH" ]; then
    log_message "Activating virtual environment..."
    source "$VENV_PATH"
else
    log_message "ERROR: Virtual environment not found at $VENV_PATH"
    send_email "Database Refresh Failed" "Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Start the backend service if it's not running
if ! pgrep -f "uvicorn app.main:app" > /dev/null; then
    log_message "Starting backend service..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    # Wait for service to start
    sleep 10
    
    # Check if service started successfully
    if ! pgrep -f "uvicorn app.main:app" > /dev/null; then
        log_message "ERROR: Failed to start backend service"
        send_email "Database Refresh Failed" "Failed to start backend service"
        exit 1
    fi
    log_message "Backend service started successfully"
fi

# Call the refresh endpoint
log_message "Starting database refresh..."
response=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:8000/api/episodes/batch/process?batch_size=5&offset=0")
status_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

# Check if the refresh was successful
if [ "$status_code" -eq 200 ]; then
    log_message "Database refresh completed successfully"
    log_message "Response: $body"
    send_email "Database Refresh Successful" "The weekly database refresh completed successfully.\n\nResponse:\n$body"
else
    log_message "ERROR: Database refresh failed with status code $status_code"
    log_message "Error response: $body"
    send_email "Database Refresh Failed" "The weekly database refresh failed with status code $status_code.\n\nError response:\n$body"
    exit 1
fi 