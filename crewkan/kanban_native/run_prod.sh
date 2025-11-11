#!/bin/bash
# Production mode runner for Kanban component

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Kanban Component - Production Mode ===${NC}"
echo ""

# Set environment variables
export KANBAN_COMPONENT_RELEASE=true
export CREWKAN_BOARD_ROOT=${CREWKAN_BOARD_ROOT:-./examples/ceo_delegation_board}

echo -e "${GREEN}Environment:${NC}"
echo "  KANBAN_COMPONENT_RELEASE=true (production mode)"
echo "  CREWKAN_BOARD_ROOT=${CREWKAN_BOARD_ROOT}"
echo ""

# Check if build exists
BUILD_DIR="crewkan/kanban_native/frontend/build"
if [ ! -f "${BUILD_DIR}/index.js" ]; then
    echo -e "${YELLOW}⚠️  Build not found. Building now...${NC}"
    cd crewkan/kanban_native/frontend
    npm run build
    cd ../../..
    echo ""
fi

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Streamlit
echo -e "${GREEN}Starting Streamlit on port 8502...${NC}"
streamlit run crewkan/crewkan_ui.py --server.port 8502

