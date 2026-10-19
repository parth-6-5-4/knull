# Hive Lite Console

React + TypeScript orchestration console for the hive.

```bash
npm install
npm run dev        # dev server (proxy /v1 to a running FastAPI on :8000)
npm run build      # production build in dist/
```

- Live mode: launch a run from Overview; the console polls `GET /v1/hive/runs/{id}`.
- Demo mode: open with `?demo=1` to replay `public/demo-run.json` (a recorded
  offline hive run) with no API keys and no server.
