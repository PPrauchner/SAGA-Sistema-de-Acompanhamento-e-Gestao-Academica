import { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { MobileBottomNav } from "./MobileBottomNav";

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="flex h-screen w-full overflow-hidden" style={{ background: "var(--background)" }}>
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <TopBar />
        {/* Mobile: p-4 pb-24 (extra bottom for bottom nav). Desktop: p-6 pb-6 */}
        <main className="flex-1 overflow-y-auto p-4 pb-24 md:p-6 md:pb-6" style={{ background: "var(--background)" }}>
          {children}
        </main>
      </div>
      <MobileBottomNav />
    </div>
  );
}
