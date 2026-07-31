import { ChatWindow } from "@/components/ChatWindow";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col bg-zinc-50 font-sans dark:bg-black">
      <DisclaimerBanner />
      <ChatWindow />
    </div>
  );
}
