# Kindred web app

Vite + React + TypeScript. See the repository README for what it does and how it was measured.

```bash
npm ci
npm run dev      # local
npm test         # engine tests, including parity with the Python reference
npm run build    # static site in dist/
```

The data it loads is in `public/data/` and is produced by `uv run python -m kindred.export_web` and `kindred.export_evidence` from the repository root.
