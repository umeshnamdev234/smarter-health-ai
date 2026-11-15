export type Role = "user" | "assistant";

export interface ImageAttachment {
  type: string; // mime type, e.g. image/png
  data: string; // base64 (no data: prefix)
}

export interface ChatMessage {
  role: Role;
  content: string;
  images?: ImageAttachment[];
  error?: string;
  emergency?: string | null;
  stats?: string;
  recommendation?: Recommendation;
  recLoading?: boolean;
  recError?: string;
}

export interface Chat {
  id: string;
  title: string;
  messages: ChatMessage[];
  updated: number;
}

export type Theme = "auto" | "light" | "dark";

export interface ServerStatus {
  state: "ok" | "warn" | "err" | "loading";
  text: string;
  sub: string;
}

export interface Doctor {
  id: string;
  name: string;
  specialty: string;
  sub_specialties: string[];
  conditions: string[];
  qualifications: string;
  experience_years: number;
  languages: string[];
  city: string;
  hospital: string;
  rating: number;
  review_count: number;
  fee: number;
  currency: string;
  available_days: string[];
  teleconsult: boolean;
  score: number;
  match_reasons: string[];
  next_available: string | null;
}

export type Urgency = "routine" | "soon" | "urgent" | "emergency";

export interface DoctorFilters {
  city?: string;
  language?: string;
  teleconsult_only?: boolean;
}

export interface Recommendation {
  specialties: { name: string; reason: string }[];
  conditions: string[];
  urgency: Urgency;
  source: "ai" | "keywords";
  emergency_notice: string | null;
  filters: DoctorFilters;
  doctors: Doctor[];
}

export interface DoctorMeta {
  count: number;
  specialties: string[];
  cities: string[];
  languages: string[];
}
