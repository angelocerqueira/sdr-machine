import { Sidebar } from "@/components/sidebar";
import { TopBar } from "@/components/top-bar";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <TopBar />
      <Sidebar />
      <main className="pt-[52px] ml-0 md:ml-14 lg:ml-[260px] transition-[margin] duration-250">
        <div className="mx-auto max-w-7xl px-4 py-6 md:px-5 md:py-7 lg:px-6 lg:py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
