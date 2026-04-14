## Goal
Provide concise, actionable guidance for AI coding agents working on this repository so they can be productive immediately.

## High-level architecture (what to know fast)
- This repo is a small ETL/service that downloads BCV Excel files, extracts USD buy/sell rates, and inserts them into a legacy SQL Server DB via a stored procedure (`sp_carga_tasa`).
- Python runner: `main.py` contains the full orchestration (download, parse, DB calls, email notifications, logging).
- Database artifacts live under `bcv_tasa_usd_updater/sql/` (migrations, `procs/alter_sp_carga_tasa_raise_and_log.sql`, and `scripts/deploy.sql`). The target DB is `rep_post_dia`.

## Key files to reference
- `main.py` — primary program flow: env loading, download (requests + retries), Excel parsing (pandas then xlrd fallback), and DB calls using `pyodbc`.
- `requirements.txt` — pinned dependencies; note `xlrd==1.2.0` is required to read older `.xls` OLE files.
- `bcv_tasa_usd_updater/sql/procs/alter_sp_carga_tasa_raise_and_log.sql` — authoritative stored-proc behavior (RAISERROR + logging to `dbo.log_sp_errors`).
- `bcv_tasa_usd_updater/tests/integration/test_sp_carga_tasa.sql` — manual integration test cases you can run in SSMS.
- `logs/` — runtime logs (e.g. `log_bcv_YYYYMMDD.log`) and `logs/estado_correo.txt` state tracking for sent emails.

## Environment & runtime notes
- Uses `python-dotenv`; put secrets and settings in a `.env` file during dev. Important env var names used in `main.py`:
  - SQL servers: `SQL2019_SERVER`, `SQL2019_USER`, `SQL2019_PASS`, `SQL2019_DB_TEMP`, and `SQL2000_SERVER`, `SQL2000_USER`, `SQL2000_PASS`, `SQL2000_DB_FINAL`.
  - DB retry tuning: `DB_MAX_ATTEMPTS`, `DB_BACKOFF_SECONDS`.
  - Email: `SMTP_SERVER`, `SMTP_USER`, `SMTP_PASS`, `SMTP_PORT` (optional), `EMAIL_DESTINO`.

## DB integration gotchas
- The code supports two server types: `2019` (modern ODBC driver) and `2000` (legacy SQL Server). On non-Windows for SQL2000 the code expects `FreeTDS` and `TDS_Version=7.0`.
- The stored procedure uses `RAISERROR` to force exceptions and also inserts error rows into `dbo.log_sp_errors`. Python code expects exceptions from pyodbc and implements retries.

## Parsing and file formats
- The source Excel files are legacy OLE `.xls`. `main.py` first tries `pandas`/`openpyxl` path and falls back to `xlrd` (hence the pinned `xlrd==1.2.0`). Do not upgrade xlrd beyond 1.2.0 without verifying.
- The USD row is found by matching "USD" in columns 1 or 2 and expects buy/sell in columns 6/7 (0-based indices 5/6 in code). See `extraer_tasa_usd` in `main.py` for heuristics and date parsing.

## Developer workflows (how to build/test/debug)
- Install deps: `pip install -r requirements.txt` (use virtualenv/venv).
- Database: apply migrations in `bcv_tasa_usd_updater/sql/migrations/*.sql` and run `bcv_tasa_usd_updater/scripts/deploy.sql` against database `rep_post_dia`.
- Run integration SQL tests: open `bcv_tasa_usd_updater/tests/integration/test_sp_carga_tasa.sql` in SSMS and execute.
- Run the Python program locally: ensure `.env` contains required DB and SMTP vars, then run `python main.py`.
- Debugging tips: check `logs/log_bcv_YYYYMMDD.log` for detailed runtime info; stored-proc errors create rows in `dbo.log_sp_errors`.

## Project-specific conventions and patterns
- Error handling: DB-level errors are surfaced via RAISERROR and logged; Python code treats non-zero returns as failure and uses retries controlled by env vars.
- State: email-sending state is tracked in `logs/estado_correo.txt` — the program uses this file to avoid duplicate sends.
- Windows vs non-Windows branching is explicit (ODBC driver selection). When adding platform-specific code, follow same guarded branching.

## Backfill at EOD (nuevo)
- Goal: si a las 23:59 la tasa del día actual no está en la BD, insertar la tasa del día anterior (backfill).
- Implementación recomendada:
  - Añadir función en `main.py` que:
    - Se conecte a la BD final (SQL2000) y verifique si existe fila para la fecha de hoy.
    - Si no existe, leer la tasa más reciente anterior a hoy (SELECT TOP 1 ... WHERE fecha < hoy ORDER BY fecha DESC).
    - Llamar a `ejecutar_sp_carga_tasa(...)` con los valores obtenidos para asegurar consistencia con lógica existente.
  - Ejecutar esta función desde un job programado (Task Scheduler / cron) a las 23:59 o invocar `python main.py --backfill-now` para pruebas locales.
- Env vars / flags útiles:
  - `FORCE_BACKFILL=1` o argumento `--backfill-now` para pruebas fuera de horario.
- Archivos a revisar para cambios: `main.py` (nueva función + integración con `ejecutar_sp_carga_tasa`), tests de integración SQL (`bcv_tasa_usd_updater/tests/integration`) para cubrir el caso de backfill.

## Examples (explicit references)
- To inspect DB retry logic, open `ejecutar_sp_carga_tasa` in `main.py` — it reads `DB_MAX_ATTEMPTS` and `DB_BACKOFF_SECONDS`.
- To understand expected SP contract and log schema, read `bcv_tasa_usd_updater/sql/procs/alter_sp_carga_tasa_raise_and_log.sql` (it documents RETURN codes and RAISERROR behavior).

## Editing guidance for AI changes
- Prefer small, well-tested edits. If modifying Excel parsing indices, include an integration test or add a safe fallback.
- If touching DB connection strings, preserve the two-server-type flow and update both branches.
- Do not remove the `xlrd==1.2.0` pin without validating that the fallback still works with current pandas/xlrd combos.

If anything here is unclear or you'd like a sample `.env`, a Task Scheduler example, or an integration test for the backfill, indicate which and it will be added.
