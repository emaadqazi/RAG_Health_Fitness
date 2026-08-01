"use client";

import { useState } from "react";
import { ChatWindow } from "./ChatWindow";
import { DisclaimerBanner } from "./DisclaimerBanner";
import { LandingPage } from "./LandingPage";

export function AppShell() {
  const [started, setStarted] = useState(false);

  if (!started) {
    return (
      <div className="flex flex-1 flex-col">
        <LandingPage onBegin={() => setStarted(true)} />
      </div>
    );
  }

  // Hands off cleanly into ChatWindow's existing empty state (disclaimer + example
  // questions) -- no duplication of that content on the landing page itself.
  return (
    <div className="flex flex-1 flex-col">
      <DisclaimerBanner />
      <ChatWindow />
    </div>
  );
}
