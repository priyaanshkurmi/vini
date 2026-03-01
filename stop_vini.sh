#!/bin/bash

echo "Stopping VINI..."

pkill -f "uvicorn main:app" 2>/dev/null && echo "  Backend stopped."
pkill -f "electron"         2>/dev/null && echo "  Avatar stopped."

echo "Done."