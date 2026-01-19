import type { PropsWithChildren } from "react";

import SidebarNav from "@/components/layout/SidebarNav";
import TopBar from "@/components/layout/TopBar";

const AppLayout = ({ children }: PropsWithChildren) => {
  return (
    <div className="flex min-h-screen bg-slate-950 dark:bg-slate-950 light:bg-slate-50 text-slate-100 dark:text-slate-100 light:text-slate-900">
      <aside className="hidden w-64 border-r border-slate-900 dark:border-slate-900 light:border-slate-200 bg-slate-950/70 dark:bg-slate-950/70 light:bg-white px-4 py-6 md:block">
        <div className="pb-6">
          <p className="text-sm font-semibold uppercase tracking-widest text-brand-400 dark:text-brand-400 light:text-brand-600">ARCHRAMPART</p>
          <p className="text-xs text-slate-500 dark:text-slate-500 light:text-slate-600">Threat Intelligence Hub</p>
          <a 
            href="https://www.archrampart.com" 
            target="_blank" 
            rel="noopener noreferrer"
            className="mt-1 block text-xs text-slate-400 dark:text-slate-400 light:text-slate-500 hover:text-brand-400 dark:hover:text-brand-400 light:hover:text-brand-600 transition"
          >
            www.archrampart.com
          </a>
          <a 
            href="mailto:security@archrampart.com" 
            className="mt-1 block text-xs text-slate-400 dark:text-slate-400 light:text-slate-500 hover:text-brand-400 dark:hover:text-brand-400 light:hover:text-brand-600 transition"
          >
            security@archrampart.com
          </a>
        </div>
        <SidebarNav />
      </aside>
      <main className="flex-1">
        <TopBar />
        <div className="px-6 py-6">
          {children}
        </div>
      </main>
    </div>
  );
};

export default AppLayout;
