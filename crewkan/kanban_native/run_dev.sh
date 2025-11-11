#!/bin/bash
# Development mode runner for Kanban component
# Requires two terminals: one for this script, one for npm dev server

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Kanban Component - Development Mode ===${NC}"
echo ""
echo -e "${YELLOW}Note: This script runs Streamlit only.${NC}"
echo -e "${YELLOW}You must also run 'npm run start' in another terminal:${NC}"
echo -e "  ${GREEN}cd crewkan/kanban_native/frontend && npm run start${NC}"
echo ""

# Set environment variables
export KANBAN_COMPONENT_RELEASE=false
export CREWKAN_BOARD_ROOT=${CREWKAN_BOARD_ROOT:-./examples/ceo_delegation_board}

echo -e "${GREEN}Environment:${NC}"
echo "  KANBAN_COMPONENT_RELEASE=false (dev mode)"
echo "  CREWKAN_BOARD_ROOT=${CREWKAN_BOARD_ROOT}"
echo ""

# Check if npm dev server is running
if ! curl -s http://localhost:3001 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Warning: npm dev server not detected on port 3001${NC}"
    echo -e "${YELLOW}   Make sure to run 'npm run start' in crewkan/kanban_native/frontend${NC}"
    echo ""
fi

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Streamlit
echo -e "${GREEN}Starting Streamlit on port 8502...${NC}"
streamlit run crewkan/crewkan_ui.py --server.port 8502

