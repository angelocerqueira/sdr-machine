import { AppSidebar } from "@/components/app-sidebar";
import "@/components/app-sidebar.css";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <AppSidebar />
      <main className="pt-12 md:pt-0 md:pl-16 min-h-screen overflow-x-hidden">
        {children}
      </main>
    </div>
  );
}
