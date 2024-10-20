#!/bin/bash

# Exit on error
set -e

# Load environmental variables from .env file
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

echo "making migrations..."
python3 manage.py makemigrations

echo "applying migrations..."
python3 manage.py migrate

# Check 'debug' value
DEBUG_VALUE=$(echo "$DEBUG_VALUE" | tr "[:upper:]" "[:lower:]")

if [ "$DEBUG_VALUE" = "false" ]; then
    echo "collecting static files..."
    python3 manage.py collectstatic --no-input
elif [ "$DEBUG_VALUE" = "true" ]; then
    echo "ensuring ssl certs [for development only]..."
    python3 generate_certs.py
fi

# Start appropriate server
case $SERVER_COMMAND in
    "daphne")
        echo "starting daphne server..."
        daphne -b 0.0.0.0 -p 8000 portal.asgi:application
        ;;
    "gunicorn")
        echo "starting gunicorn server..."
        gunicorn portal.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
        ;;
    "uvicorn")
        echo "starting uvicorn server..."
        uvicorn portal.asgi:application --host 0.0.0.0 --port 8000 --reload
        ;;
    "test")
        echo "starting tests..."
        python3 manage.py test
esac