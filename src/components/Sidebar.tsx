import {
    LayoutDashboard, Users, Globe, History, Tag, ChevronLeft, ChevronRight, Sparkles,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { ViewType } from '../types';

const NAV_ITEMS: { view: ViewType; label: string; icon: React.ElementType }[] = [
    { view: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { view: 'leads', label: 'Leads', icon: Users },
    { view: 'scrape', label: 'Scrape Website', icon: Globe },
    { view: 'history', label: 'History', icon: History },
    { view: 'categories', label: 'Categories', icon: Tag },
];

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
    const { currentView, setCurrentView, leads } = useApp();

    return (
        <aside
            className={`fixed left-0 top-0 h-screen bg-slate-900/80 backdrop-blur-xl border-r border-slate-700/50 flex flex-col transition-all duration-300 z-40 ${collapsed ? 'w-[72px]' : 'w-64'
                }`}
        >
            {/* Logo */}
            <div className="p-4 flex items-center gap-3 border-b border-slate-700/50 min-h-[72px]">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/20">
                    <Sparkles className="w-5 h-5 text-white" />
                </div>
                {!collapsed && (
                    <div className="overflow-hidden">
                        <h1 className="text-lg font-bold gradient-text whitespace-nowrap">LeadScraper</h1>
                        <p className="text-[10px] text-slate-500 uppercase tracking-widest">Pro Edition</p>
                    </div>
                )}
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-4 px-3 space-y-1">
                {NAV_ITEMS.map(item => {
                    const Icon = item.icon;
                    const isActive = currentView === item.view;
                    return (
                        <button
                            key={item.view}
                            onClick={() => setCurrentView(item.view)}
                            className={`sidebar-link w-full ${isActive ? 'active' : ''}`}
                            title={collapsed ? item.label : undefined}
                        >
                            <Icon className="w-5 h-5 flex-shrink-0" />
                            {!collapsed && <span>{item.label}</span>}
                            {!collapsed && item.view === 'leads' && leads.length > 0 && (
                                <span className="ml-auto bg-blue-500/20 text-blue-400 text-xs font-semibold px-2 py-0.5 rounded-full">
                                    {leads.length}
                                </span>
                            )}
                        </button>
                    );
                })}
            </nav>

            {/* Collapse Toggle */}
            <div className="p-3 border-t border-slate-700/50">
                <button
                    onClick={onToggle}
                    className="w-full flex items-center justify-center gap-2 py-2 rounded-xl text-slate-500 hover:text-slate-300 hover:bg-slate-800/60 transition-all"
                >
                    {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
                    {!collapsed && <span className="text-sm">Collapse</span>}
                </button>
            </div>
        </aside>
    );
}
