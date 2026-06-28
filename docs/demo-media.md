# Demo Media

The README demo footage is generated from real `rad-device-watch` CLI commands against a synthetic SQLite database.

```bash
python -m pip install -e ".[media]"
python scripts/generate_demo_media.py
```

Generated assets:

- `docs/assets/demo-poster.png`
- `docs/assets/demo.gif`
- `docs/assets/demo.mp4`

The generated device records, downtime events, usage records, and alerts are synthetic examples for demonstration.
