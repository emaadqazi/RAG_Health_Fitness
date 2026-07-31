export function DisclaimerBanner() {
  return (
    <div className="flex w-full items-center justify-center gap-2 border-b border-teal-100 bg-teal-50/70 px-4 py-2 text-center text-sm text-teal-900 dark:border-teal-900/30 dark:bg-teal-950/25 dark:text-teal-200">
      <span aria-hidden className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-teal-600/15 text-[10px] font-semibold text-teal-700 dark:bg-teal-400/15 dark:text-teal-300">
        i
      </span>
      Educational tool that synthesizes published research to illustrate reasoning
      across evidence &mdash; not medical advice, and not a substitute for a
      conversation with a clinician who knows your actual health history.
    </div>
  );
}
