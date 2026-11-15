"""create doctors table

Revision ID: 0001
Revises:
Create Date: 2026-11-14 08:24:13.057349

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMPTY_ARRAY = sa.text("'{}'::text[]")


def upgrade() -> None:
    op.create_table(
        "doctors",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("specialty", sa.Text(), nullable=False),
        sa.Column("sub_specialties", postgresql.ARRAY(sa.Text()), nullable=False, server_default=EMPTY_ARRAY),
        sa.Column("conditions", postgresql.ARRAY(sa.Text()), nullable=False, server_default=EMPTY_ARRAY),
        sa.Column("qualifications", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("experience_years", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("languages", postgresql.ARRAY(sa.Text()), nullable=False, server_default=EMPTY_ARRAY),
        sa.Column("city", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("hospital", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("rating", sa.Numeric(2, 1), nullable=False, server_default=sa.text("0")),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("fee", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default=sa.text("'INR'")),
        sa.Column("available_days", postgresql.ARRAY(sa.Text()), nullable=False, server_default=EMPTY_ARRAY),
        sa.Column("teleconsult", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("gender", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("experience_years BETWEEN 0 AND 80", name=op.f("ck_doctors_experience_years")),
        sa.CheckConstraint("rating BETWEEN 0 AND 5", name=op.f("ck_doctors_rating")),
        sa.CheckConstraint("review_count >= 0", name=op.f("ck_doctors_review_count")),
        sa.CheckConstraint("fee >= 0", name=op.f("ck_doctors_fee")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_doctors")),
    )
    op.create_index("ix_doctors_specialty_lower", "doctors", [sa.text("lower(specialty)")], postgresql_where=sa.text("active"))
    op.create_index("ix_doctors_city_lower", "doctors", [sa.text("lower(city)")], postgresql_where=sa.text("active"))
    op.create_index("ix_doctors_conditions", "doctors", ["conditions"], postgresql_using="gin")

    # keep updated_at current on every UPDATE
    op.execute(
        """
        CREATE OR REPLACE FUNCTION doctors_touch_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at := now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER doctors_updated_at BEFORE UPDATE ON doctors "
        "FOR EACH ROW EXECUTE FUNCTION doctors_touch_updated_at()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS doctors_updated_at ON doctors")
    op.execute("DROP FUNCTION IF EXISTS doctors_touch_updated_at()")
    op.drop_index("ix_doctors_conditions", table_name="doctors")
    op.drop_index("ix_doctors_city_lower", table_name="doctors")
    op.drop_index("ix_doctors_specialty_lower", table_name="doctors")
    op.drop_table("doctors")
