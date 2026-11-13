# MFL Core Service (generated bundle)

- `PRODUCT_SPEC.md` – master product/engineering spec (feed to an AI to regenerate the system)
- `schema.sql` – MySQL 8 schema (addresses, customers, loans, payment_schedule, payments)
- `app/` – FastAPI layered code (core, util, domain, dao, service, api/v1)

## Run locally
```bash
mysql -uroot -p < schema.sql
cp .env.example .env            # edit credentials
uv venv && uv pip install -r requirements.txt
set -a; source .env; set +a
uv run uvicorn app.main:app --reload --port 8000
```
Docs: http://127.0.0.1:8000/docs — base path `/mfl-core/api/v1`; send `X-User-Id` header for audit fields.
