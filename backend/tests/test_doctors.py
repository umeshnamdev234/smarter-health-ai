"""Tests for doctor ranking, specialty normalisation and keyword triage (no model needed)."""
from datetime import date

import pytest

from app.doctors import Doctor, load_doctors_file, next_available, rank_doctors
from app.triage import keyword_triage, normalize_specialty

DOCS = [
    {"id": "1", "name": "Dr. A", "specialty": "Neurology", "conditions": ["migraine"], "city": "Pune", "rating": 4.0,
     "experience_years": 10, "languages": ["English", "Marathi"], "available_days": ["Mon"], "teleconsult": False},
    {"id": "2", "name": "Dr. B", "specialty": "Neurology", "conditions": ["epilepsy"], "city": "Delhi", "rating": 4.9,
     "experience_years": 25, "languages": ["English"], "available_days": ["Tue"], "teleconsult": True},
    {"id": "3", "name": "Dr. C", "specialty": "Cardiology", "conditions": ["chest pain"], "city": "Pune", "rating": 5.0,
     "experience_years": 30, "languages": ["English"], "available_days": ["Mon"], "teleconsult": True},
    {"id": "4", "name": "Dr. D", "specialty": "General Medicine", "conditions": ["fever"], "city": "Pune", "rating": 4.5,
     "experience_years": 5, "languages": ["English"], "available_days": ["Mon"], "teleconsult": False},
]
MONDAY = date(2026, 11, 16)


class Directory:
    """Test helper: ranks the in-memory DOCS like the API does with rows from PostgreSQL."""
    def __init__(self):
        self.doctors = [Doctor.model_validate(d) for d in DOCS]

    def rank(self, *args, **kwargs):
        return rank_doctors(self.doctors, *args, **kwargs)


@pytest.fixture
def directory():
    return Directory()


def test_only_requested_specialties_are_returned(directory):
    ranked = directory.rank(["Neurology"], [], today=MONDAY)
    assert {d.specialty for d in ranked} == {"Neurology"}


def test_city_language_and_condition_beat_raw_rating(directory):
    ranked = directory.rank(["Neurology"], ["migraine"], city="Pune", language="Marathi", today=MONDAY)
    assert ranked[0].id == "1"
    assert {"Treats migraine", "In Pune", "Speaks Marathi", "Available today"} <= set(ranked[0].match_reasons)


def test_primary_specialty_outranks_secondary(directory):
    ranked = directory.rank(["General Medicine", "Cardiology"], [], today=MONDAY)
    assert ranked[0].specialty == "General Medicine"


def test_teleconsult_only_filter(directory):
    ranked = directory.rank(["Neurology"], [], teleconsult_only=True, today=MONDAY)
    assert [d.id for d in ranked] == ["2"]


def test_city_match_ranks_local_doctor_first(directory):
    ranked = directory.rank(["Neurology"], [], city="Delhi", today=MONDAY)
    assert ranked[0].id == "2" and "In Delhi" in ranked[0].match_reasons


def test_csv_loading(tmp_path):
    p = tmp_path / "docs.csv"
    p.write_text("id,name,specialty,conditions,languages,available_days,teleconsult,rating,city\n"
                 "9,Dr. Z,Dermatology,acne;eczema,English;Hindi,Mon;Thu,yes,4.4,Mumbai\n")
    d = load_doctors_file(p)[0]
    assert d.conditions == ["acne", "eczema"] and d.teleconsult is True and d.rating == 4.4


@pytest.mark.parametrize("raw,expected", [
    ("Cardiologist", "Cardiology"), ("dermatology", "Dermatology"), ("Gynaecology", "Obstetrics & Gynecology"),
    ("Otolaryngology", "ENT"), ("Internal Medicine", "General Medicine"), ("Astrology", None),
])
def test_normalize_specialty(raw, expected):
    allowed = ["Cardiology", "Dermatology", "Obstetrics & Gynecology", "ENT", "General Medicine"]
    assert normalize_specialty(raw, allowed) == expected


def test_keyword_fallback():
    allowed = ["Dermatology", "Neurology", "General Medicine"]
    picks = [p.name for p in keyword_triage("I have an itchy rash on my arm", allowed)]
    assert picks[0] == "Dermatology" and "General Medicine" in picks


def test_next_available():
    assert next_available(["Mon"], MONDAY) == ("Today", 0)
    assert next_available(["Tue"], MONDAY) == ("Tomorrow", 1)
    assert next_available([], MONDAY) == (None, None)
