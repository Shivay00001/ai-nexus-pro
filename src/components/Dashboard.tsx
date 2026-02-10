import { Users, TrendingUp, CheckCircle, Clock, Globe, ArrowUpRight } from 'lucide-react';
import { useApp } from '../context/AppContext';

export function Dashboard() {
    const { leads, categories, scrapingJobs, setCurrentView } = useApp();

    const stats = {
        total: leads.length,
        new: leads.filter(l => l.status === 'new').length,
        qualified: leads.filter(l => l.status === 'qualified').length,
        contacted: leads.filter(l => l.status === 'contacted').length,
        closed: leads.filter(l => l.status === 'closed').length,
    };

    const recentLeads = leads.slice(0, 5);
    const recentJobs = scrapingJobs.slice(0, 5);

    const categoryBreakdown = categories
        .map(cat => ({
            ...cat,
            count: leads.filter(l => l.category_id === cat.id).length,
        }))
        .filter(c => c.count > 0)
        .sort((a, b) => b.count - a.count)
        .slice(0, 6);

    const statCards = [
        { label: 'Total Leads', value: stats.total, icon: Users, gradient: 'from-blue-500 to-cyan-500', shadowColor: 'shadow-blue-500/20' },
        { label: 'New Leads', value: stats.new, icon: TrendingUp, gradient: 'from-emerald-500 to-green-500', shadowColor: 'shadow-emerald-500/20' },
        { label: 'Qualified', value: stats.qualified, icon: CheckCircle, gradient: 'from-amber-500 to-orange-500', shadowColor: 'shadow-amber-500/20' },
        { label: 'Contacted', value: stats.contacted, icon: Clock, gradient: 'from-violet-500 to-purple-500', shadowColor: 'shadow-violet-500/20' },
    ];

    return (
        <div className="space-y-6 animate-fade-in-up">
            {/* Page Title */}
            <div>
                <h2 className="text-2xl font-bold text-white">Dashboard</h2>
                <p className="text-slate-400 mt-1">Overview of your lead generation pipeline</p>
            </div>

            {/* Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {statCards.map((stat, i) => {
                    const Icon = stat.icon;
                    return (
                        <div
                            key={stat.label}
                            className={`glass-card p-5 relative overflow-hidden animate-fade-in-up`}
                            style={{ animationDelay: `${i * 75}ms` }}
                        >
                            <div className="flex items-start justify-between relative z-10">
                                <div>
                                    <p className="text-sm text-slate-400 font-medium">{stat.label}</p>
                                    <p className="text-3xl font-bold text-white mt-2">{stat.value}</p>
                                </div>
                                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.gradient} flex items-center justify-center shadow-lg ${stat.shadowColor}`}>
                                    <Icon className="w-6 h-6 text-white" />
                                </div>
                            </div>
                            {/* Decorative gradient */}
                            <div className={`absolute -bottom-6 -right-6 w-24 h-24 rounded-full bg-gradient-to-br ${stat.gradient} opacity-[0.07] blur-xl`} />
                        </div>
                    );
                })}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Recent Leads */}
                <div className="lg:col-span-2 glass-card p-5">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="font-semibold text-white">Recent Leads</h3>
                        <button onClick={() => setCurrentView('leads')} className="text-sm text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1">
                            View all <ArrowUpRight className="w-3 h-3" />
                        </button>
                    </div>
                    {recentLeads.length === 0 ? (
                        <div className="py-8 text-center">
                            <Users className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                            <p className="text-slate-400">No leads yet. Start scraping to generate leads!</p>
                            <button onClick={() => setCurrentView('scrape')} className="btn-primary mt-4 text-sm">
                                <Globe className="w-4 h-4 inline mr-2" />
                                Start Scraping
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {recentLeads.map(lead => {
                                const cat = categories.find(c => c.id === lead.category_id);
                                return (
                                    <div key={lead.id} className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-700/30 transition-colors">
                                        <div className="w-10 h-10 rounded-xl bg-slate-700/60 flex items-center justify-center text-sm font-bold text-slate-300 flex-shrink-0">
                                            {(lead.company_name || '?')[0].toUpperCase()}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-white truncate">{lead.company_name || 'Unknown'}</p>
                                            <p className="text-xs text-slate-400 truncate">{lead.email || lead.website || 'No contact info'}</p>
                                        </div>
                                        {cat && (
                                            <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full text-white flex-shrink-0" style={{ backgroundColor: cat.color }}>
                                                {cat.name}
                                            </span>
                                        )}
                                        <span className={`status-badge flex-shrink-0 ${lead.status === 'new' ? 'bg-emerald-500/15 text-emerald-400'
                                            : lead.status === 'contacted' ? 'bg-blue-500/15 text-blue-400'
                                                : lead.status === 'qualified' ? 'bg-amber-500/15 text-amber-400'
                                                    : 'bg-slate-500/15 text-slate-400'
                                            }`}>
                                            {lead.status}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Category Breakdown */}
                <div className="glass-card p-5">
                    <h3 className="font-semibold text-white mb-4">Categories</h3>
                    {categoryBreakdown.length === 0 ? (
                        <div className="py-8 text-center">
                            <p className="text-slate-400 text-sm">No categorized leads yet</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {categoryBreakdown.map(cat => {
                                const percentage = stats.total > 0 ? Math.round((cat.count / stats.total) * 100) : 0;
                                return (
                                    <div key={cat.id}>
                                        <div className="flex items-center justify-between mb-1.5">
                                            <div className="flex items-center gap-2">
                                                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: cat.color }} />
                                                <span className="text-sm text-slate-300">{cat.name}</span>
                                            </div>
                                            <span className="text-sm font-medium text-slate-400">{cat.count}</span>
                                        </div>
                                        <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
                                            <div
                                                className="h-full rounded-full transition-all duration-700"
                                                style={{ width: `${percentage}%`, backgroundColor: cat.color }}
                                            />
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* Recent Scraping Jobs */}
            {recentJobs.length > 0 && (
                <div className="glass-card p-5">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="font-semibold text-white">Recent Scraping Jobs</h3>
                        <button onClick={() => setCurrentView('history')} className="text-sm text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1">
                            View all <ArrowUpRight className="w-3 h-3" />
                        </button>
                    </div>
                    <div className="space-y-2">
                        {recentJobs.map(job => (
                            <div key={job.id} className="flex items-center justify-between p-3 rounded-xl hover:bg-slate-700/30 transition-colors">
                                <div className="flex items-center gap-3 min-w-0">
                                    <Globe className="w-4 h-4 text-slate-400 flex-shrink-0" />
                                    <span className="text-sm text-slate-300 truncate">{job.url}</span>
                                </div>
                                <div className="flex items-center gap-3 flex-shrink-0">
                                    <span className="text-xs text-slate-400">{job.leads_found} leads</span>
                                    <span className={`status-badge ${job.status === 'completed' ? 'bg-emerald-500/15 text-emerald-400'
                                        : job.status === 'failed' ? 'bg-red-500/15 text-red-400'
                                            : job.status === 'running' ? 'bg-blue-500/15 text-blue-400'
                                                : 'bg-slate-500/15 text-slate-400'
                                        }`}>
                                        {job.status}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
