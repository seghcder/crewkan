#!/bin/bash
# Top-level build script for CrewKan
# Builds the Kanban frontend component

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="${SCRIPT_DIR}/crewkan/kanban_native/frontend"

echo "🔨 Building CrewKan Kanban Component..."
echo ""

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Error: Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm is not installed. Please install Node.js and npm."
    exit 1
fi

# Build the frontend
echo "📦 Building frontend component..."
cd "$FRONTEND_DIR"
npm run build

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build completed successfully!"
    echo "   Build output: ${FRONTEND_DIR}/build/"
    echo ""
    ls -lh build/ | grep -E "index\.(js|html)"
else
    echo ""
    echo "❌ Build failed!"
    exit 1
fi

