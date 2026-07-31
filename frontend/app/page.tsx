import { ChatWindow } from "@/components/ChatWindow";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <DisclaimerBanner />
      <ChatWindow />
    </div>
  );
}
