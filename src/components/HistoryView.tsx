import { Globe, CheckCircle2, XCircle, Clock, Loader2, ExternalLink } from 'lucide-react';
import { useApp } from '../context/AppContext';

export function HistoryView() {
    const { scrapingJobs } = useApp();

    const statusConfig: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
        completed: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/15' },
        failed: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/15' },
        running: { icon: Loader2, color: 'text-blue-400', bg: 'bg-blue-500/15' },
        pending: { icon: Clock, color: 'text-amber-400', bg: 'bg-amber-500/15' },
    };

    return (
        <div className="space-y-6 animate-fade-in-up">
            <div>
                <h2 className="text-2xl font-bold text-white">Scraping History</h2>
                <p className="text-slate-400 mt-1">Track all your web scraping jobs and their results</p>
            </div>

            {scrapingJobs.length === 0 ? (
                <div className="glass-card p-16 text-center">
                    <Globe className="w-14 h-14 text-slate-600 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-white mb-2">No scraping history</h3>
                    <p className="text-slate-400">Your scraping jobs will appear here once you start scraping websites.</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {scrapingJobs.map((job, i) => {
                        const config = statusConfig[job.status] || statusConfig.pending;
                        const StatusIcon = config.icon;
                        return (
                            <div
                                key={job.id}
                                className="glass-card-hover p-5 animate-fade-in-up"
                                style={{ animationDelay: `${Math.min(i, 9) * 50}ms` }}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex items-start gap-4 min-w-0">
                                        <div className={`w-10 h-10 rounded-xl ${config.bg} flex items-center justify-center flex-shrink-0`}>
                                            <StatusIcon className={`w-5 h-5 ${config.color} ${job.status === 'running' ? 'animate-spin-slow' : ''}`} />
                                        </div>
                                        <div className="min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <a
                                                    href={job.url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-sm font-medium text-white hover:text-blue-400 transition-colors truncate flex items-center gap-1"
                                                >
                                                    {job.url}
                                                    <ExternalLink className="w-3 h-3 flex-shrink-0" />
                                                </a>
                                            </div>
                                            <div className="flex items-center gap-4 text-xs text-slate-500">
                                                <span>{new Date(job.created_at).toLocaleString()}</span>
                                                {job.status === 'completed' && (
                                                    <span className="text-emerald-400 font-medium">{job.leads_found} lead{job.leads_found !== 1 ? 's' : ''} found</span>
                                                )}
                                                {job.completed_at && (
                                                    <span>
                                                        Duration: {Math.round((new Date(job.completed_at).getTime() - new Date(job.created_at).getTime()) / 1000)}s
                                                    </span>
                                                )}
                                            </div>
                                            {job.error_message && (
                                                <p className="text-xs text-red-400/80 mt-2">{job.error_message}</p>
                                            )}
                                        </div>
                                    </div>
                                    <span className={`status-badge ${config.bg} ${config.color} flex-shrink-0`}>
                                        {job.status}
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
