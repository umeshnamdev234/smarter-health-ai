import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement> & { size?: number };

const stroke = (size: number, rest: SVGProps<SVGSVGElement>) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
  ...rest,
});

export const Pulse = ({ size = 18, strokeWidth = 2.8, ...rest }: P) => (
  <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden {...rest}>
    <path d="M5 17h5l2.5-6 4.5 12 3-8 1.5 2H27" fill="none" stroke="#fff" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
export const Plus = ({ size = 18, ...r }: P) => <svg {...stroke(size, r)} strokeWidth={2.2}><path d="M12 5v14M5 12h14" /></svg>;
export const Search = ({ size = 15, ...r }: P) => <svg {...stroke(size, r)}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>;
export const ChatBubble = ({ size = 15, ...r }: P) => <svg {...stroke(size, r)}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>;
export const Trash = ({ size = 14, ...r }: P) => <svg {...stroke(size, r)}><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" /></svg>;
export const Moon = ({ size = 16, ...r }: P) => <svg {...stroke(size, r)}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg>;
export const Menu = ({ size = 20, ...r }: P) => <svg {...stroke(size, r)}><path d="M4 7h16M4 12h16M4 17h16" /></svg>;
export const Lock = ({ size = 15, ...r }: P) => <svg {...stroke(size, r)}><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></svg>;
export const Clip = ({ size = 20, ...r }: P) => <svg {...stroke(size, r)}><path d="m21.4 11.1-8.5 8.5a5.5 5.5 0 0 1-7.8-7.8l8.5-8.5a3.7 3.7 0 0 1 5.2 5.2l-8.5 8.5a1.8 1.8 0 0 1-2.6-2.6l7.8-7.8" /></svg>;
export const ArrowUp = ({ size = 18, ...r }: P) => <svg {...stroke(size, r)} strokeWidth={2.4}><path d="M12 19V5M5 12l7-7 7 7" /></svg>;
export const Stop = ({ size = 14 }: P) => <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden><rect x="5" y="5" width="14" height="14" rx="3" fill="currentColor" /></svg>;
export const Copy = ({ size = 14, ...r }: P) => <svg {...stroke(size, r)}><rect x="9" y="9" width="12" height="12" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>;
export const Check = ({ size = 14, ...r }: P) => <svg {...stroke(size, r)}><path d="M20 6 9 17l-5-5" /></svg>;
export const Regen = ({ size = 14, ...r }: P) => <svg {...stroke(size, r)}><path d="M3 12a9 9 0 0 1 15.5-6.2L21 8M21 3v5h-5M21 12a9 9 0 0 1-15.5 6.2L3 16M3 21v-5h5" /></svg>;
export const Alert = ({ size = 18, ...r }: P) => <svg {...stroke(size, r)} strokeWidth={2.2}><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /><path d="M12 9v4M12 17h.01" /></svg>;
export const Activity = ({ size = 18, ...r }: P) => <svg {...stroke(size, r)}><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>;
export const Flask = ({ size = 18, ...r }: P) => <svg {...stroke(size, r)}><path d="M9 3h6M10 3v6L4.5 18.5A2 2 0 0 0 6.2 21.5h11.6a2 2 0 0 0 1.7-3L14 9V3" /><path d="M7 15h10" /></svg>;
export const Pill = ({ size = 18, ...r }: P) => <svg {...stroke(size, r)}><rect x="3" y="9" width="18" height="6" rx="3" transform="rotate(-45 12 12)" /><path d="m8.5 8.5 7 7" /></svg>;
export const ImageIc = ({ size = 18, ...r }: P) => <svg {...stroke(size, r)}><rect x="3" y="3" width="18" height="18" rx="3" /><circle cx="9" cy="9" r="2" /><path d="m21 15-5-5L5 21" /></svg>;
export const Stethoscope = ({ size = 14, ...r }: P) => <svg {...stroke(size, r)}><path d="M5 3v5a4 4 0 0 0 8 0V3" /><path d="M9 12v2a5 5 0 0 0 10 0v-2" /><circle cx="19" cy="10" r="2" /></svg>;
