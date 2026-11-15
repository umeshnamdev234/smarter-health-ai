"""PostgreSQL access for the doctor directory (asyncpg)."""
import functools
import logging
from typing import Optional

import asyncpg

from .doctors import Doctor

log = logging.getLogger("smarter_health.db")

COLUMNS = [
    "id", "name", "specialty", "sub_specialties", "conditions", "qualifications", "experience_years",
    "languages", "city", "hospital", "rating", "review_count", "fee", "currency", "available_days",
    "teleconsult", "gender",
]
SELECT = f"SELECT {', '.join(COLUMNS)} FROM doctors"


class DatabaseUnavailable(Exception):
    pass


UNAVAILABLE_MSG = "Doctor database is unreachable. Is the minikube tunnel running? (scripts/db-tunnel.sh)"
_CONNECTION_ERRORS = (OSError, TimeoutError, asyncpg.InterfaceError, asyncpg.PostgresConnectionError,
                      asyncpg.CannotConnectNowError)


def db_call(fn):
    """Turns connection-level failures (tunnel down, pod restarting) into DatabaseUnavailable -> HTTP 503."""
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except _CONNECTION_ERRORS as e:
            log.warning("database call %s failed: %s", fn.__name__, e)
            raise DatabaseUnavailable(UNAVAILABLE_MSG) from e
    return wrapper


def _to_doctor(row: asyncpg.Record) -> Doctor:
    d = dict(row)
    d["rating"] = float(d["rating"])
    d["currency"] = (d["currency"] or "INR").strip()
    return Doctor.model_validate(d)


class DoctorRepository:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> bool:
        """Opens the pool. Returns False (instead of raising) so the API can start without the DB."""
        if self.pool:
            return True
        try:
            self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5, timeout=5, command_timeout=10)
            return True
        except (OSError, asyncpg.PostgresError, TimeoutError) as e:
            log.warning("PostgreSQL unavailable: %s", e)
            return False

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def _pool(self) -> asyncpg.Pool:
        if not self.pool and not await self.connect():
            raise DatabaseUnavailable(UNAVAILABLE_MSG)
        assert self.pool
        return self.pool

    async def ping(self) -> bool:
        try:
            pool = await self._pool()
            await pool.fetchval("SELECT 1")
            return True
        except (DatabaseUnavailable, asyncpg.PostgresError, *_CONNECTION_ERRORS):
            return False

    @db_call
    async def migration_revision(self) -> Optional[str]:
        """Current Alembic revision of the database (None if migrations were never run)."""
        pool = await self._pool()
        if not await pool.fetchval("SELECT to_regclass('alembic_version') IS NOT NULL"):
            return None
        return await pool.fetchval("SELECT version_num FROM alembic_version")

    # ---------- reads ----------
    @db_call
    async def meta(self) -> dict:
        pool = await self._pool()
        row = await pool.fetchrow(
            """SELECT count(*) AS count,
                      coalesce(array_agg(DISTINCT specialty ORDER BY specialty), '{}') AS specialties,
                      coalesce(array_agg(DISTINCT city ORDER BY city) FILTER (WHERE city <> ''), '{}') AS cities
               FROM doctors WHERE active"""
        )
        languages = await pool.fetchval(
            "SELECT coalesce(array_agg(DISTINCT l ORDER BY l), '{}') FROM doctors, unnest(languages) l WHERE active"
        )
        return {"count": row["count"], "specialties": list(row["specialties"]), "cities": list(row["cities"]),
                "languages": list(languages)}

    @db_call
    async def row_count(self) -> int:
        """All rows, including deactivated doctors."""
        pool = await self._pool()
        return await pool.fetchval("SELECT count(*) FROM doctors")

    @db_call
    async def specialties(self) -> list[str]:
        pool = await self._pool()
        return [r[0] for r in await pool.fetch("SELECT DISTINCT specialty FROM doctors WHERE active ORDER BY 1")]

    @db_call
    async def get(self, doctor_id: str) -> Optional[Doctor]:
        pool = await self._pool()
        row = await pool.fetchrow(f"{SELECT} WHERE id = $1 AND active", doctor_id)
        return _to_doctor(row) if row else None

    @db_call
    async def search(self, specialty: Optional[str] = None, city: Optional[str] = None,
                     q: Optional[str] = None, limit: int = 50) -> list[Doctor]:
        pool = await self._pool()
        rows = await pool.fetch(
            f"""{SELECT}
                WHERE active
                  AND ($1::text IS NULL OR lower(specialty) = lower($1))
                  AND ($2::text IS NULL OR lower(city) = lower($2))
                  AND ($3::text IS NULL OR name ILIKE '%' || $3 || '%' OR hospital ILIKE '%' || $3 || '%'
                       OR EXISTS (SELECT 1 FROM unnest(conditions) c WHERE c ILIKE '%' || $3 || '%'))
                ORDER BY rating DESC, experience_years DESC
                LIMIT $4""",
            specialty, city, q, limit,
        )
        return [_to_doctor(r) for r in rows]

    @db_call
    async def candidates(self, specialties: list[str], teleconsult_only: bool = False) -> list[Doctor]:
        """Active doctors in the given specialties; ranking happens in Python (app.doctors.rank_doctors)."""
        pool = await self._pool()
        rows = await pool.fetch(
            f"""{SELECT} WHERE active AND lower(specialty) = ANY($1::text[]) AND (NOT $2 OR teleconsult)""",
            [s.lower() for s in specialties], teleconsult_only,
        )
        return [_to_doctor(r) for r in rows]

    # ---------- writes ----------
    @db_call
    async def upsert_many(self, doctors: list[Doctor]) -> int:
        pool = await self._pool()
        cols = ", ".join(COLUMNS)
        params = ", ".join(f"${i + 1}" for i in range(len(COLUMNS)))
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in COLUMNS if c != "id")
        sql = f"INSERT INTO doctors ({cols}, active) VALUES ({params}, true) ON CONFLICT (id) DO UPDATE SET {updates}, active = true"
        async with pool.acquire() as conn, conn.transaction():
            await conn.executemany(sql, [[getattr(d, c) for c in COLUMNS] for d in doctors])
        return len(doctors)

    async def upsert(self, doctor: Doctor) -> Doctor:
        await self.upsert_many([doctor])
        return await self.get(doctor.id)  # type: ignore[return-value]

    @db_call
    async def deactivate(self, doctor_id: str) -> bool:
        pool = await self._pool()
        status = await pool.execute("UPDATE doctors SET active = false WHERE id = $1 AND active", doctor_id)
        return status.endswith("1")

    @db_call
    async def deactivate_except(self, keep_ids: list[str]) -> int:
        pool = await self._pool()
        status = await pool.execute("UPDATE doctors SET active = false WHERE active AND NOT (id = ANY($1::text[]))", keep_ids)
        return int(status.split()[-1])
