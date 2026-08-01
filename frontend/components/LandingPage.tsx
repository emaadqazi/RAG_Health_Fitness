"use client";

import { useEffect, useRef } from "react";
import { usePrefersReducedMotion } from "@/lib/usePrefersReducedMotion";

/** Ambient background motif: a slow ECG/pulse-line drift, tying "biomedical
 * literature" to "fitness" without a gym-cliche icon. Purely decorative. */
function PulseBackdrop({ reducedMotion }: { reducedMotion: boolean }) {
  return (
    <svg
      aria-hidden
      className="pointer-events-none absolute inset-x-0 top-1/2 -z-10 h-32 w-[140%] -translate-x-[10%] -translate-y-1/2 text-teal-600 opacity-[0.15] dark:text-teal-400 dark:opacity-[0.12]"
      viewBox="0 0 800 100"
      preserveAspectRatio="none"
    >
      <path
        d="M0 50 L260 50 L285 15 L310 85 L335 5 L360 50 L800 50"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={reducedMotion ? undefined : "animate-pulse-drift"}
      />
    </svg>
  );
}

function PulseIcon({ reducedMotion }: { reducedMotion: boolean }) {
  return (
    <div
      className={`mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-teal-50 dark:bg-teal-950/40 ${
        reducedMotion ? "" : "animate-heartbeat"
      }`}
    >
      <svg viewBox="0 0 24 24" className="h-6 w-6 text-teal-600 dark:text-teal-400" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 12h4l2-7 4 14 2-7h6" />
      </svg>
    </div>
  );
}

const MAX_TILT_DEG = 6;

export function LandingPage({ onBegin }: { onBegin: () => void }) {
  const cardRef = useRef<HTMLDivElement>(null);
  const reducedMotion = usePrefersReducedMotion();

  useEffect(() => {
    // Skip attaching the tilt listener entirely when the user has asked for less
    // motion -- not just disabling the visual effect, avoiding the work.
    if (reducedMotion) return;
    const card = cardRef.current;
    if (!card) return;

    function handleMove(e: MouseEvent) {
      const rect = card!.getBoundingClientRect();
      const px = (e.clientX - rect.left) / rect.width - 0.5;
      const py = (e.clientY - rect.top) / rect.height - 0.5;
      card!.style.setProperty("--tilt-x", `${(py * -MAX_TILT_DEG).toFixed(2)}deg`);
      card!.style.setProperty("--tilt-y", `${(px * MAX_TILT_DEG).toFixed(2)}deg`);
    }
    function handleLeave() {
      card!.style.setProperty("--tilt-x", "0deg");
      card!.style.setProperty("--tilt-y", "0deg");
    }

    card.addEventListener("mousemove", handleMove);
    card.addEventListener("mouseleave", handleLeave);
    return () => {
      card.removeEventListener("mousemove", handleMove);
      card.removeEventListener("mouseleave", handleLeave);
    };
  }, [reducedMotion]);

  return (
    <div className="relative flex flex-1 flex-col items-center justify-center overflow-hidden px-6 py-16" style={{ perspective: "1200px" }}>
      <PulseBackdrop reducedMotion={reducedMotion} />
      <div
        ref={cardRef}
        className="relative w-full max-w-md rounded-3xl border border-stone-200 bg-white/85 p-8 text-center shadow-xl backdrop-blur-sm transition-transform duration-150 ease-out dark:border-stone-700 dark:bg-stone-800/85"
        style={
          reducedMotion
            ? undefined
            : { transform: "rotateX(var(--tilt-x, 0deg)) rotateY(var(--tilt-y, 0deg))", transformStyle: "preserve-3d" }
        }
      >
        <PulseIcon reducedMotion={reducedMotion} />
        <h1 className="mt-4 text-2xl font-semibold text-stone-900 dark:text-stone-100">Evidence, not guesswork</h1>
        <p className="mt-2 text-sm leading-relaxed text-stone-600 dark:text-stone-400">
          Ask a health or fitness question and get an answer reasoned through real PubMed,
          Semantic Scholar, and Europe PMC research.
        </p>
        <button
          type="button"
          onClick={onBegin}
          className="mt-6 w-full rounded-full bg-teal-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-teal-700 dark:hover:bg-teal-500"
          style={reducedMotion ? undefined : { transform: "translateZ(30px)" }}
        >
          Let&rsquo;s begin
        </button>
      </div>
    </div>
  );
}
