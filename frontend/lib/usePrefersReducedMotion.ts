import { useSyncExternalStore } from "react";

// useSyncExternalStore is the correct primitive for subscribing to a browser API like
// matchMedia -- it avoids both the "setState synchronously in an effect" anti-pattern
// and SSR hydration mismatches (via the server-snapshot fallback).
function subscribe(callback: () => void): () => void {
  const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
  mq.addEventListener("change", callback);
  return () => mq.removeEventListener("change", callback);
}
function getSnapshot(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
function getServerSnapshot(): boolean {
  return false;
}

export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
