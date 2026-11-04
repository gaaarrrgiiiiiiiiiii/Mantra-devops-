# Mantra frontend

React and TypeScript interface built with Vite. Run these commands from `frontend/`:

```bash
npm ci
npm run dev
npm run build
npm run lint
```

The development server defaults to port 5174 and proxies `/api` to `http://localhost:8000`. Its server-side proxy reads the local `VITE_API_KEY` from an ignored `frontend/.env` file. Use a development-only key, never production credentials, and never reference that variable from browser code. Restart the development server after changing its configuration.

Production builds are served by Nginx behind the authenticated Caddy gateway. The gateway supplies the backend API key; do not embed production credentials in the browser bundle.

Built-in ingestion samples are in `public/samples/`. See the [root README](../README.md) for the complete stack, access and deployment instructions.
