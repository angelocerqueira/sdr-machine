import { AppSidebar } from "@/components/app-sidebar";
import { ToastProvider } from "@/components/ui/toast";
import "@/components/app-sidebar.css";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <div className="min-h-screen">
        <AppSidebar />
        <main className="pt-12 md:pt-0 md:pl-[72px] min-h-screen min-w-0">
          {children}
        </main>
      </div>
    </ToastProvider>
  );
}
