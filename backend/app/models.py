"""SQLAlchemy table definitions: the schema source of truth for Alembic.

Runtime queries use asyncpg directly (app/db.py); these definitions exist so that
`alembic revision --autogenerate` and `alembic check` can compare code with the database.
When you change a table here, create a migration:

    .venv/bin/alembic revision --autogenerate -m "describe the change"
"""
from sqlalchemy import (
    CHAR, TIMESTAMP, Boolean, CheckConstraint, Column, Index, Integer, MetaData, Numeric, Table, Text, func, text,
)
from sqlalchemy.dialects.postgresql import ARRAY

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

EMPTY_ARRAY = text("'{}'::text[]")

doctors = Table(
    "doctors",
    metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("specialty", Text, nullable=False),
    Column("sub_specialties", ARRAY(Text), nullable=False, server_default=EMPTY_ARRAY),
    Column("conditions", ARRAY(Text), nullable=False, server_default=EMPTY_ARRAY),
    Column("qualifications", Text, nullable=False, server_default=text("''")),
    Column("experience_years", Integer, nullable=False, server_default=text("0")),
    Column("languages", ARRAY(Text), nullable=False, server_default=EMPTY_ARRAY),
    Column("city", Text, nullable=False, server_default=text("''")),
    Column("hospital", Text, nullable=False, server_default=text("''")),
    Column("rating", Numeric(2, 1), nullable=False, server_default=text("0")),
    Column("review_count", Integer, nullable=False, server_default=text("0")),
    Column("fee", Integer, nullable=False, server_default=text("0")),
    Column("currency", CHAR(3), nullable=False, server_default=text("'INR'")),
    Column("available_days", ARRAY(Text), nullable=False, server_default=EMPTY_ARRAY),  # e.g. {Mon,Wed,Fri}
    Column("teleconsult", Boolean, nullable=False, server_default=text("false")),
    Column("gender", Text),
    Column("active", Boolean, nullable=False, server_default=text("true")),  # soft delete
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("experience_years BETWEEN 0 AND 80", name="experience_years"),
    CheckConstraint("rating BETWEEN 0 AND 5", name="rating"),
    CheckConstraint("review_count >= 0", name="review_count"),
    CheckConstraint("fee >= 0", name="fee"),
)

Index("ix_doctors_specialty_lower", func.lower(doctors.c.specialty), postgresql_where=doctors.c.active)
Index("ix_doctors_city_lower", func.lower(doctors.c.city), postgresql_where=doctors.c.active)
Index("ix_doctors_conditions", doctors.c.conditions, postgresql_using="gin")
