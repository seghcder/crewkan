# Kanban Board Component Frontend

This is the frontend for the bi-directional Streamlit Kanban board component.

## Development

To run in development mode:

1. Start the dev server:
   ```bash
   npm run start
   ```

2. Set the environment variable in your Streamlit app:
   ```bash
   export KANBAN_COMPONENT_RELEASE=false
   ```

3. Run your Streamlit app - it will connect to the dev server on `http://localhost:3001`

## Production Build

To build for production:

```bash
npm run build
```

This creates the `build/` directory with the compiled component.

Set `KANBAN_COMPONENT_RELEASE=true` (or don't set it, defaults to false but checks for build dir) to use the built files.

## Dependencies

- `streamlit-component-lib`: Streamlit component API
- `typescript`: TypeScript compiler
- `vite`: Build tool

## Structure

- `src/index.tsx`: Main component code
- `build/`: Generated build output (gitignored, created by `npm run build`)

