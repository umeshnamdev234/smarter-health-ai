"""Imports doctors from a JSON or CSV file into PostgreSQL.

Run migrations first:  .venv/bin/alembic upgrade head

    .venv/bin/python scripts/import_doctors.py data/doctors.sample.json
    .venv/bin/python scripts/import_doctors.py my_doctors.csv --replace   # deactivate doctors not in the file

Rows are upserted by id, so re-running is safe. Uses DATABASE_URL from backend/.env.
"""
import argparse
import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from pydantic import ValidationError  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import DoctorRepository  # noqa: E402
from app.doctors import load_doctors_file  # noqa: E402


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="JSON or CSV file with doctors")
    ap.add_argument("--replace", action="store_true", help="deactivate doctors whose id is not in the file")
    ap.add_argument("--if-empty", action="store_true", help="only import when the doctors table has no rows (for seeding)")
    args = ap.parse_args()

    try:
        doctors = load_doctors_file(args.file)
    except ValidationError as e:
        print(f"Invalid doctor data in {args.file}:\n{e}", file=sys.stderr)
        return 1
    ids = [d.id for d in doctors]
    if len(ids) != len(set(ids)):
        print("Duplicate doctor ids in file", file=sys.stderr)
        return 1

    repo = DoctorRepository(get_settings().database_url)
    if not await repo.connect():
        print("Cannot connect to PostgreSQL. Is the tunnel running? (scripts/db-tunnel.sh)", file=sys.stderr)
        return 1
    try:
        if await repo.migration_revision() is None:
            print("Database schema missing. Run first: .venv/bin/alembic upgrade head", file=sys.stderr)
            return 1
        if args.if_empty and await repo.row_count() > 0:
            print("Doctors table already has data; skipping seed")
            return 0
        n = await repo.upsert_many(doctors)
        print(f"Imported {n} doctors from {args.file}")
        if args.replace:
            print(f"Deactivated {await repo.deactivate_except(ids)} doctors not in the file")
        meta = await repo.meta()
        print(f"Directory now has {meta['count']} active doctors in {len(meta['specialties'])} specialties")
    finally:
        await repo.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
