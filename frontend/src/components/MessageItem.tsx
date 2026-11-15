"use client";

import { memo, useState } from "react";
import type { ChatMessage, DoctorFilters, DoctorMeta } from "@/lib/types";
import DoctorSuggestions from "./DoctorSuggestions";
import { Alert, Check, Copy, Pulse, Regen, Stethoscope } from "./Icons";
import Markdown from "./Markdown";

interface Props {
  message: ChatMessage;
  index: number;
  meta: DoctorMeta | null;
  onFindDoctors: (index: number, filters: DoctorFilters) => void;
  isLast: boolean;
  streaming: boolean; // this message is currently being generated
  canRegenerate: boolean;
  onRegenerate: () => void;
}

function MessageItem({ message: m, index, meta, onFindDoctors, isLast, streaming, canRegenerate, onRegenerate }: Props) {
  const [copied, setCopied] = useState(false);

  if (m.role === "user") {
    return (
      <div className="msg user">
        <div className="user-col">
          {!!m.images?.length && (
            <div className="msg-imgs">
              {m.images.map((im, i) => (
                // eslint-disable-next-line @next/next/no-img-element -- local base64 data, nothing to optimise
                <img key={i} src={`data:${im.type};base64,${im.data}`} alt="Attached medical image" />
              ))}
            </div>
          )}
          {m.content && <div className="bubble">{m.content}</div>}
        </div>
      </div>
    );
  }

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(m.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      /* clipboard blocked */
    }
  };

  return (
    <div className={`msg ai ${isLast ? "last" : ""}`}>
      <div className="avatar"><Pulse /></div>
      <div className="bubble">
        <div className="who">
          Smarter Health AI {m.stats && <span className="meta">{m.stats}</span>}
        </div>

        {m.emergency && (
          <div className="emergency" role="alert">
            <Alert />
            <div><b>Possible emergency</b>{m.emergency}</div>
          </div>
        )}

        {m.error ? (
          <div className="err-box">{m.error}</div>
        ) : streaming && !m.content ? (
          <div className="thinking">
            <svg className="ecg" viewBox="0 0 64 22" aria-hidden><path d="M0 11h18l4-8 6 16 5-12 3 4h28" /></svg>
            Analyzing…
          </div>
        ) : (
          <div className={`content ${streaming ? "streaming" : ""}`}>
            <Markdown text={m.content} />
          </div>
        )}

        {!streaming && !m.error && m.content && (
          <div className="actions">
            <button className="act" onClick={copy}>{copied ? <><Check />Copied</> : <><Copy />Copy</>}</button>
            {isLast && canRegenerate && <button className="act" onClick={onRegenerate}><Regen />Regenerate</button>}
            {!m.recommendation && !m.recLoading && (
              <button className="act primary-act" onClick={() => onFindDoctors(index, {})}><Stethoscope />Find a specialist</button>
            )}
          </div>
        )}

        {(m.recommendation || m.recLoading || m.recError) && (
          <DoctorSuggestions
            rec={m.recommendation}
            loading={m.recLoading}
            error={m.recError}
            meta={meta}
            onRefine={(f) => onFindDoctors(index, f)}
          />
        )}
      </div>
    </div>
  );
}

export default memo(MessageItem);
