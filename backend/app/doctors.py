"""Doctor model, file loading (for imports) and deterministic ranking.

Doctors are stored in PostgreSQL (queries: app/db.py; schema: app/models.py + alembic/versions). Files are only used to
import data: scripts/import_doctors.py accepts JSON (a list, or {"doctors": [...]}) or CSV.

CSV columns (list fields separated by ';'):
  id,name,specialty,sub_specialties,conditions,qualifications,experience_years,languages,
  city,hospital,rating,review_count,fee,currency,available_days,teleconsult
"""
import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
LIST_FIELDS = {"sub_specialties", "conditions", "languages", "available_days"}


class Doctor(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1)
    specialty: str = Field(..., min_length=1)
    sub_specialties: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    qualifications: str = ""
    experience_years: int = Field(0, ge=0, le=80)
    languages: list[str] = Field(default_factory=list)
    city: str = ""
    hospital: str = ""
    rating: float = Field(0.0, ge=0, le=5)
    review_count: int = Field(0, ge=0)
    fee: int = Field(0, ge=0)
    currency: str = Field("INR", min_length=3, max_length=3)
    available_days: list[str] = Field(default_factory=list)  # e.g. ["Mon", "Wed", "Fri"]
    teleconsult: bool = False
    gender: Optional[str] = None


class RankedDoctor(Doctor):
    score: float
    match_reasons: list[str]
    next_available: Optional[str] = None


# ---------- file loading (imports) ----------
def _from_csv(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            row: dict = {k.strip(): (v or "").strip() for k, v in r.items() if k}
            for k in LIST_FIELDS & row.keys():
                row[k] = [x.strip() for x in row[k].split(";") if x.strip()]
            if "teleconsult" in row:
                row["teleconsult"] = str(row["teleconsult"]).lower() in ("1", "true", "yes", "y")
            for k in ("experience_years", "review_count", "fee", "rating", "gender", "currency"):
                if row.get(k) == "":
                    row.pop(k)
            rows.append(row)
    return rows


def load_doctors_file(file: str | Path) -> list[Doctor]:
    path = Path(file)
    if path.suffix.lower() == ".csv":
        raw = _from_csv(path)
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data["doctors"] if isinstance(data, dict) else data
    return [Doctor.model_validate(d) for d in raw]


# ---------- ranking ----------
def next_available(days: list[str], today: date) -> tuple[Optional[str], Optional[int]]:
    wanted = {d[:3].title() for d in days}
    for i in range(7):
        day = today + timedelta(days=i)
        if DAYS[day.weekday()] in wanted:
            label = "Today" if i == 0 else "Tomorrow" if i == 1 else day.strftime("%a, %d %b")
            return label, i
    return None, None


def rank_doctors(
    doctors: list[Doctor],
    specialties: list[str],
    conditions: list[str],
    city: Optional[str] = None,
    language: Optional[str] = None,
    teleconsult_only: bool = False,
    limit: int = 5,
    today: Optional[date] = None,
) -> list[RankedDoctor]:
    """Scores doctors for a triage result. Each result carries human-readable match reasons."""
    weights = [1.0, 0.65, 0.45]
    spec_w = {s.lower(): weights[i] for i, s in enumerate(specialties[:3])}
    conds = [c.lower().strip() for c in conditions if len(c.strip()) >= 4]
    today = today or date.today()
    results: list[RankedDoctor] = []

    for d in doctors:
        w = spec_w.get(d.specialty.lower())
        if w is None or (teleconsult_only and not d.teleconsult):
            continue
        score, reasons = w, [f"{d.specialty} specialist"]

        doc_conds = [c.lower() for c in d.conditions]
        matched = next((c for c in conds if any(c in dc or dc in c for dc in doc_conds)), None)
        if matched:
            score += 0.3
            reasons.append(f"Treats {matched}")

        score += d.rating / 5 * 0.3 + min(d.experience_years, 30) / 30 * 0.2

        if city:
            if d.city.lower() == city.lower():
                score += 0.35
                reasons.append(f"In {d.city}")
            elif d.teleconsult:
                score += 0.1
                reasons.append("Online consultation")
            else:
                score -= 0.3

        if language and any(lang.lower() == language.lower() for lang in d.languages):
            score += 0.1
            reasons.append(f"Speaks {language}")

        label, in_days = next_available(d.available_days, today)
        if in_days == 0:
            score += 0.1
            reasons.append("Available today")

        results.append(RankedDoctor(**d.model_dump(), score=round(score, 3), match_reasons=reasons, next_available=label))

    results.sort(key=lambda r: (-r.score, -r.rating))
    return results[:limit]
