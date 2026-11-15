"""Generates 200 FICTIONAL sample doctors for development: data/doctors.sample.json

    .venv/bin/python scripts/generate_sample_doctors.py

Replace with your real directory by pointing DOCTORS_FILE (backend/.env) at your own
JSON or CSV file. See app/doctors.py for the expected fields.
"""
import json
import random
from pathlib import Path

random.seed(42)

SPECIALTIES = {
    "General Medicine": (["Internal Medicine", "Family Medicine", "Preventive Care"], ["fever", "viral infection", "fatigue", "hypertension", "diabetes", "cold and cough", "body pain"]),
    "Cardiology": (["Interventional Cardiology", "Heart Failure", "Electrophysiology"], ["chest pain", "hypertension", "heart attack", "arrhythmia", "palpitations", "high cholesterol", "heart failure"]),
    "Pulmonology": (["Asthma & Allergy", "Sleep Medicine", "Critical Care"], ["asthma", "copd", "chronic cough", "breathlessness", "pneumonia", "sleep apnea", "tuberculosis"]),
    "Gastroenterology": (["Hepatology", "Endoscopy", "IBD"], ["acidity", "gerd", "abdominal pain", "fatty liver", "ibs", "constipation", "jaundice", "ulcer"]),
    "Neurology": (["Stroke", "Epilepsy", "Headache Medicine"], ["migraine", "headache", "seizure", "epilepsy", "stroke", "numbness", "parkinson", "vertigo"]),
    "Orthopedics": (["Joint Replacement", "Spine Surgery", "Sports Medicine"], ["back pain", "knee pain", "fracture", "arthritis", "slip disc", "shoulder pain", "sports injury"]),
    "Dermatology": (["Cosmetic Dermatology", "Pediatric Dermatology", "Trichology"], ["acne", "eczema", "psoriasis", "skin rash", "hair loss", "fungal infection", "pigmentation"]),
    "Endocrinology": (["Diabetology", "Thyroid", "Obesity"], ["diabetes", "thyroid", "hypothyroidism", "pcos", "obesity", "hormonal imbalance", "high blood sugar"]),
    "Nephrology": (["Dialysis", "Transplant Nephrology"], ["kidney disease", "kidney stones", "high creatinine", "proteinuria", "dialysis", "swelling"]),
    "Urology": (["Andrology", "Endourology"], ["urinary infection", "kidney stones", "prostate", "burning urination", "frequent urination"]),
    "ENT": (["Otology", "Rhinology", "Head & Neck"], ["sinusitis", "ear pain", "hearing loss", "tonsillitis", "sore throat", "vertigo", "nasal blockage"]),
    "Ophthalmology": (["Cataract", "Retina", "Glaucoma"], ["blurred vision", "cataract", "eye pain", "red eye", "glaucoma", "diabetic retinopathy"]),
    "Psychiatry": (["Child Psychiatry", "Addiction", "Mood Disorders"], ["anxiety", "depression", "insomnia", "stress", "panic attacks", "bipolar", "addiction"]),
    "Obstetrics & Gynecology": (["High-risk Pregnancy", "Infertility", "Gynec Oncology"], ["pregnancy", "irregular periods", "pcos", "pelvic pain", "infertility", "menopause"]),
    "Pediatrics": (["Neonatology", "Pediatric Infectious Disease"], ["child fever", "vaccination", "growth", "child cough", "newborn care", "diarrhea in children"]),
    "Oncology": (["Medical Oncology", "Radiation Oncology", "Surgical Oncology"], ["cancer", "tumor", "lump", "breast lump", "unexplained weight loss", "chemotherapy"]),
    "Rheumatology": (["Autoimmune Disease"], ["rheumatoid arthritis", "joint pain", "lupus", "gout", "joint swelling", "ankylosing spondylitis"]),
    "Hematology": (["Clinical Hematology"], ["anemia", "low hemoglobin", "bleeding disorder", "low platelets", "thalassemia"]),
    "Infectious Disease": (["Tropical Medicine", "HIV Medicine"], ["dengue", "malaria", "typhoid", "tuberculosis", "persistent fever", "covid"]),
}
# rough share of 200 doctors per specialty
COUNTS = {"General Medicine": 26, "Cardiology": 15, "Orthopedics": 15, "Obstetrics & Gynecology": 13, "Pediatrics": 13,
          "Dermatology": 13, "Neurology": 11, "Gastroenterology": 11, "Endocrinology": 10, "ENT": 10, "Pulmonology": 10,
          "Psychiatry": 9, "Ophthalmology": 9, "Urology": 7, "Nephrology": 6, "Oncology": 7, "Rheumatology": 5,
          "Hematology": 5, "Infectious Disease": 5}
assert sum(COUNTS.values()) == 200

CITIES = {
    "Pune": ["Marathi", "Hindi"], "Mumbai": ["Marathi", "Hindi"], "Bengaluru": ["Kannada", "Hindi", "Tamil"],
    "Delhi": ["Hindi", "Punjabi"], "Hyderabad": ["Telugu", "Hindi", "Urdu"], "Chennai": ["Tamil", "Telugu"],
    "Indore": ["Hindi"],
}
HOSPITAL_A = ["Lotus", "Riverside", "Green Valley", "Sunrise", "Silver Oak", "Harmony", "Bluebell", "Northstar", "Meadow", "Cedar"]
HOSPITAL_B = ["Multispeciality Hospital", "Medical Centre", "Clinic", "Hospital", "Health Centre"]
FIRST = ["Aarav", "Ananya", "Rohan", "Priya", "Vikram", "Sneha", "Arjun", "Kavya", "Rahul", "Meera", "Siddharth", "Isha",
         "Karthik", "Neha", "Aditya", "Pooja", "Nikhil", "Divya", "Varun", "Shruti", "Manish", "Anjali", "Suresh", "Lakshmi",
         "Farhan", "Zoya", "Harpreet", "Gurleen", "Venkat", "Revathi", "Amit", "Ritu", "Sanjay", "Deepa", "Imran", "Nandini"]
LAST = ["Sharma", "Patel", "Iyer", "Reddy", "Kulkarni", "Deshpande", "Nair", "Menon", "Gupta", "Joshi", "Rao", "Singh",
        "Khan", "Verma", "Bhat", "Chatterjee", "Pillai", "Agarwal", "Mehta", "Saxena", "Kapoor", "Naidu", "Shetty", "Mishra"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
QUAL = {"General Medicine": "MBBS, MD (Medicine)", "Pediatrics": "MBBS, MD (Pediatrics)", "Obstetrics & Gynecology": "MBBS, MS (OBG)",
        "Orthopedics": "MBBS, MS (Ortho)", "ENT": "MBBS, MS (ENT)", "Ophthalmology": "MBBS, MS (Ophthalmology)",
        "Dermatology": "MBBS, MD (Dermatology)", "Psychiatry": "MBBS, MD (Psychiatry)"}

doctors = []
n = 0
for spec, count in COUNTS.items():
    subs, conds = SPECIALTIES[spec]
    for _ in range(count):
        n += 1
        city = random.choice(list(CITIES))
        exp = random.randint(3, 32)
        doctors.append({
            "id": f"D{n:03d}",
            "name": f"Dr. {random.choice(FIRST)} {random.choice(LAST)}",
            "specialty": spec,
            "sub_specialties": random.sample(subs, k=min(len(subs), random.randint(1, 2))),
            "conditions": random.sample(conds, k=min(len(conds), random.randint(4, 6))),
            "qualifications": QUAL.get(spec, "MBBS, MD, DM" if spec not in ("Urology",) else "MBBS, MS, MCh"),
            "experience_years": exp,
            "languages": ["English"] + random.sample(CITIES[city], k=random.randint(1, len(CITIES[city]))),
            "city": city,
            "hospital": f"{random.choice(HOSPITAL_A)} {random.choice(HOSPITAL_B)}",
            "rating": round(min(5.0, random.uniform(3.8, 4.6) + exp / 100), 1),
            "review_count": random.randint(15, 900),
            "fee": random.choice([400, 500, 600, 700, 800, 1000, 1200, 1500]) + (300 if exp > 20 else 0),
            "currency": "INR",
            "available_days": sorted(random.sample(DAYS, k=random.randint(3, 6)), key=DAYS.index),
            "teleconsult": random.random() < 0.6,
            "gender": None,
        })

out = Path(__file__).resolve().parent.parent / "data" / "doctors.sample.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({"_note": "FICTIONAL sample data for development only", "doctors": doctors}, indent=1, ensure_ascii=False))
print(f"Wrote {len(doctors)} sample doctors to {out}")
