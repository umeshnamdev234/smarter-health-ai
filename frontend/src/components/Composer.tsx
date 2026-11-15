"use client";

import { useEffect, useState, type Dispatch, type RefObject, type SetStateAction } from "react";
import type { ImageAttachment } from "@/lib/types";
import { ArrowUp, Clip, Stop } from "./Icons";

const MAX_IMAGES = 4;

interface Props {
  value: string;
  onChange: (v: string) => void;
  images: ImageAttachment[];
  onImagesChange: Dispatch<SetStateAction<ImageAttachment[]>>;
  streaming: boolean;
  onSend: () => void;
  onStop: () => void;
  fileInputRef: RefObject<HTMLInputElement | null>;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
}

function readImage(file: File): Promise<ImageAttachment> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve({ type: file.type, data: String(r.result).split(",")[1] });
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}

export default function Composer({ value, onChange, images, onImagesChange, streaming, onSend, onStop, fileInputRef, textareaRef }: Props) {
  const [drag, setDrag] = useState(false);

  // auto-grow textarea
  useEffect(() => {
    const t = textareaRef.current;
    if (!t) return;
    t.style.height = "auto";
    t.style.height = Math.min(t.scrollHeight, 200) + "px";
  }, [value, textareaRef]);

  const addFiles = async (files: FileList | File[]) => {
    const imgs = [...files].filter((f) => f.type.startsWith("image/"));
    if (!imgs.length) return;
    const read = await Promise.all(imgs.map(readImage));
    onImagesChange((prev) => [...prev, ...read].slice(0, MAX_IMAGES));
  };

  const canSend = !!value.trim() || images.length > 0;

  return (
    <div className="composer-wrap">
      <div
        className={`composer ${drag ? "drag" : ""}`}
        onDragEnter={(e) => { e.preventDefault(); setDrag(true); }}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={(e) => { e.preventDefault(); setDrag(false); }}
        onDrop={(e) => { e.preventDefault(); setDrag(false); addFiles(e.dataTransfer.files); }}
      >
        {images.length > 0 && (
          <div className="previews">
            {images.map((p, i) => (
              <div className="pv" key={i}>
                {/* eslint-disable-next-line @next/next/no-img-element -- local preview */}
                <img src={`data:${p.type};base64,${p.data}`} alt="Attachment preview" />
                <button aria-label="Remove image" onClick={() => onImagesChange((prev) => prev.filter((_, j) => j !== i))}>×</button>
              </div>
            ))}
          </div>
        )}
        <div className="row">
          <button className="icon-btn" title="Attach medical image (X-ray, scan, skin photo, report)" aria-label="Attach image" onClick={() => fileInputRef.current?.click()}>
            <Clip />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            hidden
            onChange={(e) => {
              if (e.target.files) addFiles(e.target.files);
              e.target.value = "";
              textareaRef.current?.focus();
            }}
          />
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            placeholder="Describe symptoms, ask about a medication, or attach a scan…"
            onChange={(e) => onChange(e.target.value)}
            onPaste={(e) => { if (e.clipboardData.files.length) addFiles(e.clipboardData.files); }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                if (!streaming && canSend) onSend();
              }
            }}
          />
          {streaming ? (
            <button className="send stop" aria-label="Stop generating" onClick={onStop}><Stop /></button>
          ) : (
            <button className="send" aria-label="Send" disabled={!canSend} onClick={onSend}><ArrowUp /></button>
          )}
        </div>
      </div>
      <div className="disclaimer">
        Smarter Health AI can make mistakes and is not a substitute for professional medical advice. In an emergency, call your local emergency number.
      </div>
    </div>
  );
}
