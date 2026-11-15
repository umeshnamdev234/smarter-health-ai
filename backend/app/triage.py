"""Specialty triage: MedGemma maps a conversation to specialties from YOUR directory.

Falls back to keyword matching if the model is unreachable or returns unusable output,
so doctor suggestions keep working either way.
"""
import json
import re
from typing import Literal, Optional

from pydantic import BaseModel

from .medgemma_client import LLMError, LLMUnavailable, MedGemmaClient
from .prompts import TRIAGE_PROMPT
from .safety import detect_emergency
from .schemas import Message

Urgency = Literal["routine", "soon", "urgent", "emergency"]

ALIASES = {
    "cardiologist": "Cardiology", "heart": "Cardiology",
    "pulmonologist": "Pulmonology", "chest medicine": "Pulmonology", "respiratory medicine": "Pulmonology",
    "gastroenterologist": "Gastroenterology", "hepatology": "Gastroenterology",
    "neurologist": "Neurology",
    "orthopedic": "Orthopedics", "orthopaedics": "Orthopedics", "orthopedist": "Orthopedics", "orthopaedic surgery": "Orthopedics",
    "dermatologist": "Dermatology", "skin": "Dermatology",
    "endocrinologist": "Endocrinology", "diabetology": "Endocrinology",
    "nephrologist": "Nephrology", "urologist": "Urology",
    "otolaryngology": "ENT", "otorhinolaryngology": "ENT", "ear nose throat": "ENT",
    "ophthalmologist": "Ophthalmology", "eye": "Ophthalmology",
    "psychiatrist": "Psychiatry", "psychology": "Psychiatry", "mental health": "Psychiatry",
    "gynecology": "Obstetrics & Gynecology", "gynaecology": "Obstetrics & Gynecology", "obstetrics": "Obstetrics & Gynecology",
    "obgyn": "Obstetrics & Gynecology", "ob/gyn": "Obstetrics & Gynecology", "gynecologist": "Obstetrics & Gynecology",
    "pediatrician": "Pediatrics", "paediatrics": "Pediatrics",
    "oncologist": "Oncology", "rheumatologist": "Rheumatology", "hematologist": "Hematology", "haematology": "Hematology",
    "internal medicine": "General Medicine", "general physician": "General Medicine", "family medicine": "General Medicine",
    "primary care": "General Medicine", "general practice": "General Medicine",
    "infectious diseases": "Infectious Disease",
}

KEYWORDS = {
    "Cardiology": ["chest pain", "palpitation", "heart", "blood pressure", "hypertension", "cholesterol", "bp "],
    "Pulmonology": ["breath", "cough", "asthma", "wheez", "lung", "copd", "sleep apnea"],
    "Gastroenterology": ["stomach", "abdominal", "acidity", "vomit", "diarrh", "constipat", "liver", "jaundice", "gas", "bloat"],
    "Neurology": ["headache", "migraine", "seizure", "numb", "dizz", "vertigo", "stroke", "tremor", "faint"],
    "Orthopedics": ["back pain", "knee", "fracture", "joint", "shoulder", "neck pain", "sprain", "bone"],
    "Dermatology": ["skin", "rash", "acne", "itch", "hair loss", "eczema", "psoriasis", "pimple"],
    "Endocrinology": ["diabetes", "sugar", "thyroid", "hba1c", "glucose", "pcos", "weight gain"],
    "Nephrology": ["kidney", "creatinine", "dialysis", "swelling in legs"],
    "Urology": ["urine", "urinat", "prostate", "kidney stone"],
    "ENT": ["ear", "throat", "sinus", "tonsil", "nose", "hearing"],
    "Ophthalmology": ["eye", "vision", "blurr", "cataract"],
    "Psychiatry": ["anxiety", "depress", "stress", "sleep", "insomnia", "panic", "suicid", "mood"],
    "Obstetrics & Gynecology": ["period", "pregnan", "menstru", "vaginal", "pelvic", "menopause"],
    "Pediatrics": ["my child", "my son", "my daughter", "baby", "infant", "toddler", "kid"],
    "Oncology": ["cancer", "tumor", "tumour", "lump"],
    "Rheumatology": ["rheumat", "lupus", "gout", "joint swelling"],
    "Hematology": ["anemia", "anaemia", "hemoglobin", "haemoglobin", "platelet"],
    "Infectious Disease": ["dengue", "malaria", "typhoid", "tuberculosis", "fever for"],
}


class SpecialtyPick(BaseModel):
    name: str
    reason: str = ""


class TriageResult(BaseModel):
    specialties: list[SpecialtyPick]
    conditions: list[str]
    urgency: Urgency
    source: Literal["ai", "keywords"]


def normalize_specialty(name: str, allowed: list[str]) -> Optional[str]:
    n = re.sub(r"\s+", " ", name.strip().lower())
    by_lower = {a.lower(): a for a in allowed}
    if n in by_lower:
        return by_lower[n]
    if n in ALIASES and ALIASES[n] in allowed:
        return ALIASES[n]
    for key, target in ALIASES.items():
        if key in n and target in allowed:
            return target
    for a in allowed:
        if a.lower() in n or n in a.lower():
            return a
    return None


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in model output")
    return json.loads(m.group(0))


def keyword_triage(text: str, allowed: list[str]) -> list[SpecialtyPick]:
    t = text.lower()
    scored = []
    for spec, words in KEYWORDS.items():
        if spec not in allowed:
            continue
        hits = sum(1 for w in words if w in t)
        if hits:
            scored.append((hits, spec))
    scored.sort(reverse=True)
    picks = [SpecialtyPick(name=s, reason="Matches the symptoms you described") for _, s in scored[:2]]
    if "General Medicine" in allowed and all(p.name != "General Medicine" for p in picks):
        picks.append(SpecialtyPick(name="General Medicine", reason="A general physician can assess and refer you"))
    return picks[:3]


async def triage(llm: MedGemmaClient, messages: list[Message], allowed: list[str]) -> TriageResult:
    user_text = "\n".join(m.content for m in messages if m.role == "user")
    emergency = detect_emergency(user_text)
    transcript = "\n".join(
        f"{'Patient' if m.role == 'user' else 'Assistant'}: {m.content.strip()}" for m in messages if m.content.strip()
    )[-6000:]
    images = [im for m in messages if m.role == "user" for im in m.images][-2:]
    prompt = TRIAGE_PROMPT.format(specialties=", ".join(allowed), transcript=transcript or "(patient shared an image)")

    content: str | list[dict] = prompt
    if images:
        content = [{"type": "text", "text": prompt}] + [
            {"type": "image_url", "image_url": {"url": f"data:{im.mime_type};base64,{im.data}"}} for im in images
        ]

    try:
        res = await llm.chat([{"role": "user", "content": content}], temperature=0, max_tokens=350, json_mode=True)
        data = _parse_json(res["content"])
        picks: list[SpecialtyPick] = []
        for item in data.get("specialties") or []:
            name = item.get("name", "") if isinstance(item, dict) else str(item)
            norm = normalize_specialty(name, allowed)
            if norm and all(p.name != norm for p in picks):
                picks.append(SpecialtyPick(name=norm, reason=str(item.get("reason", "")) if isinstance(item, dict) else ""))
        if not picks:
            raise ValueError("model chose no valid specialty")
        conditions = [str(c) for c in (data.get("conditions") or []) if isinstance(c, (str, int))][:4]
        urgency = data.get("urgency") if data.get("urgency") in ("routine", "soon", "urgent", "emergency") else "routine"
        result = TriageResult(specialties=picks[:3], conditions=conditions, urgency=urgency, source="ai")
    except (LLMUnavailable, LLMError, ValueError, json.JSONDecodeError):
        result = TriageResult(specialties=keyword_triage(user_text, allowed), conditions=[], urgency="routine", source="keywords")

    if emergency:
        result.urgency = "emergency"
    if not result.specialties and allowed:
        fallback = "General Medicine" if "General Medicine" in allowed else allowed[0]
        result.specialties = [SpecialtyPick(name=fallback, reason="Start with a general assessment")]
    return result
