# Kanban Component Development Guide

## Overview

The Kanban board component is a bi-directional Streamlit component built with TypeScript. It supports both development and production modes.

## Development vs Production

### Development Mode
- Frontend runs on a separate dev server (port 3001) with hot reload
- Changes to TypeScript files are reflected immediately
- Requires running both the npm dev server and Streamlit

### Production Mode
- Uses pre-built static files from `frontend/build/`
- No separate dev server needed
- Faster startup, but requires rebuilding after code changes

## Remote VSCode Setup

When using remote VSCode, you need to forward both ports:
- **Port 8502** (or your Streamlit port): For the Streamlit app
- **Port 3001**: For the frontend dev server (development mode only)

**Important**: 
- The dev server is configured to bind to `0.0.0.0` (see `vite.config.ts`), which allows remote connections
- When the component iframe loads `http://localhost:3001`, it resolves to the **remote machine's** localhost (where Streamlit is running)
- VSCode port forwarding makes the remote port 3001 accessible to your browser
- **Alternative**: Use production mode (no separate dev server needed) - component files are served through the same Streamlit port

### VSCode Port Forwarding

1. Open the "Ports" tab in VSCode (usually at the bottom)
2. Click "Forward a Port" or use the "+" button
3. Forward port **3001** for the dev server (development mode)
4. Forward port **8502** (or your chosen Streamlit port) for the Streamlit app

Alternatively, add to `.vscode/settings.json` in your workspace:
```json
{
  "remote.portsAttributes": {
    "3001": {
      "label": "Kanban Dev Server",
      "onAutoForward": "notify"
    },
    "8502": {
      "label": "Streamlit App",
      "onAutoForward": "notify"
    }
  }
}
```

### How It Works

1. **Development Mode**: 
   - Streamlit runs on remote port 8502 → forwarded to your local machine
   - npm dev server runs on remote port 3001 → forwarded to your local machine
   - Browser loads Streamlit from forwarded port 8502
   - Streamlit component iframe loads from `localhost:3001` (which resolves to remote machine)
   - VSCode port forwarding makes remote port 3001 accessible to your browser

2. **Production Mode**:
   - Only need to forward port 8502
   - Component files are served directly by Streamlit (no separate server needed)

## Running Commands

### Development Mode

**Terminal 1 - Frontend Dev Server:**
```bash
cd crewkan/kanban_native/frontend
npm run start
```

**Terminal 2 - Streamlit App:**
```bash
export KANBAN_COMPONENT_RELEASE=false
export CREWKAN_BOARD_ROOT=./examples/ceo_delegation_board
cd /path/to/crewkan
source venv/bin/activate
streamlit run crewkan/crewkan_ui.py --server.port 8502
```

**Or as a single command:**
```bash
KANBAN_COMPONENT_RELEASE=false CREWKAN_BOARD_ROOT=./examples/ceo_delegation_board streamlit run crewkan/crewkan_ui.py --server.port 8502
```

### Production Mode

**Build the frontend first:**
```bash
cd crewkan/kanban_native/frontend
npm run build
```

**Then run Streamlit:**
```bash
export CREWKAN_BOARD_ROOT=./examples/ceo_delegation_board
cd /path/to/crewkan
source venv/bin/activate
streamlit run crewkan/crewkan_ui.py --server.port 8502
```

**Or as a single command:**
```bash
CREWKAN_BOARD_ROOT=./examples/ceo_delegation_board streamlit run crewkan/crewkan_ui.py --server.port 8502
```

## Quick Reference

### Development (with hot reload)

**Option 1: Using helper scripts**
```bash
# Terminal 1 - Frontend dev server
cd crewkan/kanban_native/frontend
npm run start

# Terminal 2 - Streamlit (from project root)
CREWKAN_BOARD_ROOT=./examples/ceo_delegation_board ./crewkan/kanban_native/run_dev.sh
```

**Option 2: Manual commands**
```bash
# Terminal 1
cd crewkan/kanban_native/frontend && npm run start

# Terminal 2
KANBAN_COMPONENT_RELEASE=false CREWKAN_BOARD_ROOT=./examples/ceo_delegation_board streamlit run crewkan/crewkan_ui.py --server.port 8502
```

### Production (pre-built)

**Option 1: Using helper script**
```bash
# Build once (if not already built)
cd crewkan/kanban_native/frontend && npm run build && cd ../..

# Run (from project root)
CREWKAN_BOARD_ROOT=./examples/ceo_delegation_board ./crewkan/kanban_native/run_prod.sh
```

**Option 2: Manual commands**
```bash
# Build once
cd crewkan/kanban_native/frontend && npm run build

# Run
CREWKAN_BOARD_ROOT=./examples/ceo_delegation_board streamlit run crewkan/crewkan_ui.py --server.port 8502
```

## Troubleshooting

### Component not loading
- **Dev mode**: Ensure npm dev server is running on port 3001
- **Prod mode**: Ensure `npm run build` was run and `build/index.js` exists
- Check browser console for errors

### Port conflicts
- Change Streamlit port: `--server.port 8503`
- Change dev server port: Edit `vite.config.ts` and update port in `__init__.py`

### Remote access issues
- Ensure both ports are forwarded in VSCode
- Check firewall settings on remote machine
- Verify `localhost` vs `0.0.0.0` binding (Vite defaults to localhost)

## Environment Variables

- `KANBAN_COMPONENT_RELEASE`: Set to `"true"` for production, `"false"` for development (default: `"false"`)
- `CREWKAN_BOARD_ROOT`: Path to the board directory (default: current directory)

## File Structure

```
crewkan/kanban_native/
├── __init__.py              # Python component wrapper
├── frontend/
│   ├── src/
│   │   └── index.tsx        # Main component code
│   ├── package.json         # npm dependencies
│   ├── tsconfig.json        # TypeScript config
│   ├── vite.config.ts       # Build config
│   └── build/               # Generated build output (gitignored)
└── kanban.html              # Original HTML (reference only)
```

