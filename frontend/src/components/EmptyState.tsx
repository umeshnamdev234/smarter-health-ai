"use client";

import type { ReactNode } from "react";
import { Activity, Flask, ImageIc, Pill, Pulse } from "./Icons";

export interface Suggestion {
  title: string;
  prompt: string;
  icon: ReactNode;
  image?: boolean;
}

export const SUGGESTIONS: Suggestion[] = [
  { title: "Check my symptoms", prompt: "I have had a headache and mild fever for 2 days. What could it be?", icon: <Activity /> },
  { title: "Explain lab results", prompt: "Explain what HbA1c 6.8%, fasting glucose 132 mg/dL and LDL 160 mean.", icon: <Flask /> },
  { title: "Medication guide", prompt: "What are the common side effects and precautions of metformin?", icon: <Pill /> },
  { title: "Analyze a medical image", prompt: "Upload an X-ray, skin photo or scan for an AI description.", icon: <ImageIc />, image: true },
];

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export default function EmptyState({ onPick }: { onPick: (s: Suggestion) => void }) {
  return (
    <div className="hero">
      <div className="hero-orb"><Pulse size={40} strokeWidth={2.6} /></div>
      <h1>
        {greeting()}. <span className="grad-text">How are you feeling today?</span>
      </h1>
      <p>Ask about symptoms, medications, lab reports or medical images. Everything stays private on your device.</p>
      <div className="cards">
        {SUGGESTIONS.map((s) => (
          <button key={s.title} className="card" onClick={() => onPick(s)}>
            <div className="card-ic">{s.icon}</div>
            <div>
              <b>{s.title}</b>
              <span>{s.prompt}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
