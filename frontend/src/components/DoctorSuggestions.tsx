"use client";

import { useState } from "react";
import type { Doctor, DoctorFilters, DoctorMeta, Recommendation, Urgency } from "@/lib/types";
import { Alert, Regen, Stethoscope } from "./Icons";

const URGENCY: Record<Urgency, { label: string; cls: string }> = {
  routine: { label: "Routine", cls: "u-routine" },
  soon: { label: "See a doctor this week", cls: "u-soon" },
  urgent: { label: "Urgent · within 24 hours", cls: "u-urgent" },
  emergency: { label: "Emergency", cls: "u-emergency" },
};

const initials = (name: string) =>
  name.replace(/^Dr\.?\s*/i, "").split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();

const money = (fee: number, currency: string) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: currency || "INR", maximumFractionDigits: 0 }).format(fee);

interface Props {
  rec?: Recommendation;
  loading?: boolean;
  error?: string;
  meta: DoctorMeta | null;
  onRefine: (filters: DoctorFilters) => void;
}

export default function DoctorSuggestions({ rec, loading, error, meta, onRefine }: Props) {
  const [filters, setFilters] = useState<DoctorFilters>(rec?.filters ?? {});

  const update = (patch: Partial<DoctorFilters>) => {
    const next = { ...filters, ...patch };
    setFilters(next);
    onRefine(next);
  };

  return (
    <section className="docs" aria-label="Recommended specialists">
      <header className="docs-head">
        <div className="docs-title">
          <span className="docs-ic"><Stethoscope size={16} /></span>
          <div>
            <b>Recommended specialists</b>
            <small>
              {meta ? `Matched from ${meta.count} doctors in your network` : "Matched from your doctor network"}
              {rec?.source === "keywords" && " · keyword match (AI unavailable)"}
            </small>
          </div>
        </div>
        {rec && <span className={`urgency ${URGENCY[rec.urgency].cls}`}>{URGENCY[rec.urgency].label}</span>}
      </header>

      {rec?.emergency_notice && (
        <div className="emergency" role="alert">
          <Alert />
          <div><b>Don&apos;t wait for an appointment</b>{rec.emergency_notice}</div>
        </div>
      )}

      {rec && (
        <div className="spec-list">
          {rec.specialties.map((s, i) => (
            <div key={s.name} className={`spec ${i === 0 ? "primary" : ""}`}>
              <b>{s.name}</b>
              {s.reason && <span>{s.reason}</span>}
            </div>
          ))}
        </div>
      )}

      <div className="doc-filters">
        <select aria-label="City" value={filters.city ?? ""} onChange={(e) => update({ city: e.target.value || undefined })} disabled={loading}>
          <option value="">Any city</option>
          {meta?.cities.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select aria-label="Language" value={filters.language ?? ""} onChange={(e) => update({ language: e.target.value || undefined })} disabled={loading}>
          <option value="">Any language</option>
          {meta?.languages.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        <label className="toggle">
          <input type="checkbox" checked={!!filters.teleconsult_only} onChange={(e) => update({ teleconsult_only: e.target.checked })} disabled={loading} />
          Online consult only
        </label>
      </div>

      {error && (
        <div className="err-box">
          {error}{" "}
          <button className="act inline" onClick={() => onRefine(filters)}><Regen />Retry</button>
        </div>
      )}

      {loading && !rec && (
        <div className="thinking">
          <svg className="ecg" viewBox="0 0 64 22" aria-hidden><path d="M0 11h18l4-8 6 16 5-12 3 4h28" /></svg>
          Matching your symptoms with specialists…
        </div>
      )}

      {rec && (
        <div className={`doc-grid ${loading ? "dim" : ""}`}>
          {rec.doctors.length === 0 && <p className="muted">No doctors match these filters. Try another city or turn off &quot;Online consult only&quot;.</p>}
          {rec.doctors.map((d) => <DoctorCard key={d.id} d={d} />)}
        </div>
      )}
    </section>
  );
}

function DoctorCard({ d }: { d: Doctor }) {
  const [note, setNote] = useState(false);
  return (
    <article className="doc-card">
      <div className="doc-top">
        <div className="doc-avatar" aria-hidden>{initials(d.name)}</div>
        <div className="doc-id">
          <b>{d.name}</b>
          <span>{d.specialty}{d.sub_specialties[0] ? ` · ${d.sub_specialties[0]}` : ""}</span>
          <small>{d.qualifications}</small>
        </div>
        <div className="doc-rating" title={`${d.review_count} reviews`}>★ {d.rating.toFixed(1)}</div>
      </div>

      <div className="doc-facts">
        <span>{d.experience_years} yrs exp</span>
        <span>{d.hospital}, {d.city}</span>
        <span>{money(d.fee, d.currency)}</span>
        {d.teleconsult && <span className="tele">Online</span>}
      </div>

      <div className="doc-reasons">
        {d.match_reasons.slice(1).map((r) => <span key={r}>{r}</span>)}
      </div>

      <div className="doc-foot">
        <span className="doc-next">{d.next_available ? <>Next available: <b>{d.next_available}</b></> : "Check availability"}</span>
        <button className="book" onClick={() => setNote((n) => !n)}>Book appointment</button>
      </div>
      {note && <p className="doc-note">Booking isn&apos;t connected yet. Hook up your appointment system to enable this.</p>}
    </article>
  );
}
