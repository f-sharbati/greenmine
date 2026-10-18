# GreenMine (mehrava sharbati) — Streamlit Deployment

## Run locally
```
pip install -r requirements.txt
streamlit run proj1.py
```

## Streamlit Community Cloud / GitHub
- Main file path: `proj1.py`
- Python 3.11+ recommended.
- Data file `inverter.CSV` is at the repo root; the DB `greenmine.db` is created automatically by `init_db.py` / `proj1.py` at first run.
- `run` helper scripts (`start.bat`, `test_smtp.py`, `migrate_*.py`, `create_user.py`, `check_users.py`, `csv_importer.py`, `seed_data.py`) are included for local maintenance; Cloud deployment only needs `proj1.py` and its imports.

## Secrets
`.streamlit/secrets.toml` currently contains SMTP credentials.
- For a **private repo** you may keep it in the repo as-is.
- For a **public repo**, delete `.streamlit/secrets.toml` and instead paste its contents into
  Streamlit Cloud -> your app -> Manage app -> Settings -> Secrets.

`.streamlit/config.toml` holds the theme. Streamlit Cloud runs apps headless and injects
the port automatically; no `port = 8501` entry is required there.
