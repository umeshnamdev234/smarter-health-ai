"use client";

import dynamic from "next/dynamic";

// The chat lives entirely in the browser (history in localStorage, streaming from the API),
// so it is rendered client-side only to avoid hydration mismatches.
const ChatApp = dynamic(() => import("./ChatApp"), {
  ssr: false,
  loading: () => <div className="loading-screen" />,
});

export default function ClientRoot() {
  return <ChatApp />;
}
