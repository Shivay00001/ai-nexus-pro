import { useState } from 'react';
import { Globe, Loader2, CheckCircle2, AlertCircle, Plus, ExternalLink, Zap, Server, Wifi } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { scrapeWebsite as clientSideScrape } from '../lib/scraper';
import { Lead } from '../types';

interface ScrapedResult {
    company_name: string;
    contact_name?: string | null;
    email?: string | null;
    phone?: string | null;
    website?: string | null;
    description?: string | null;
    source_url: string;
    category_suggestion?: string | null;
}

export function ScrapingView() {
    const { addLead, addScrapingJob, categories, addToast } = useApp();

    const [url, setUrl] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [results, setResults] = useState<ScrapedResult[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [progress, setProgress] = useState('');
    const [scrapingMode, setScrapingMode] = useState<'auto' | 'python' | 'browser'>('auto');
    const [pagesScraped, setPagesScraped] = useState(0);
    const [addedLeads, setAddedLeads] = useState<Set<number>>(new Set());

    const handleScrape = async () => {
        if (!url.trim()) return;

        setIsLoading(true);
        setResults([]);
        setError(null);
        setProgress('Initializing...');
        setPagesScraped(0);
        setAddedLeads(new Set());

        const startTime = Date.now();
        let normalizedUrl = url.trim();
        if (!normalizedUrl.startsWith('http://') && !normalizedUrl.startsWith('https://')) {
            normalizedUrl = 'https://' + normalizedUrl;
        }

        try {
            let scrapedLeads: ScrapedResult[] = [];
            let usedBackend = false;

            // Try Python backend first (if not forced to browser mode)
            if (scrapingMode !== 'browser') {
                try {
                    setProgress('🐍 Connecting to Python scraping engine...');
                    const controller = new AbortController();
                    const timeout = setTimeout(() => controller.abort(), 5000);

                    const response = await fetch('/api/scrape', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: normalizedUrl, max_pages: 5 }),
                        signal: controller.signal,
                    });
                    clearTimeout(timeout);

                    if (response.ok) {
                        const contentType = response.headers.get('content-type') || '';
                        if (!contentType.includes('application/json')) {
                            throw new Error('Backend not available');
                        }
                        const data = await response.json();
                        if (data.success && data.leads && data.leads.length > 0) {
                            scrapedLeads = data.leads;
                            setPagesScraped(data.pages_scraped || 1);
                            usedBackend = true;
                            setProgress(`✅ Python engine scraped ${data.pages_scraped} page(s)`);
                        } else if (data.error) {
                            throw new Error(data.error);
                        }
                    } else {
                        throw new Error(`Backend returned ${response.status}`);
                    }
                } catch (backendErr) {
                    if (scrapingMode === 'python') {
                        throw backendErr;
                    }
                    // Fall through to client-side scraping
                    console.log('Python backend unavailable, falling back to client-side:', backendErr);
                }
            }

            // Fallback: client-side scraping via CORS proxy
            if (!usedBackend) {
                setProgress('🌐 Using browser-side scraping (CORS proxy)...');
                const csResult = await clientSideScrape(normalizedUrl, categories);
                if (csResult.error && csResult.leads.length === 0) {
                    throw new Error(csResult.error);
                }
                scrapedLeads = csResult.leads.map(l => ({
                    company_name: l.company_name || '',
                    contact_name: l.contact_name,
                    email: l.email,
                    phone: l.phone,
                    website: l.website || normalizedUrl,
                    description: l.description,
                    source_url: l.source_url || normalizedUrl,
                    category_suggestion: l.category_suggestion,
                }));
                setPagesScraped(1);
                setProgress('✅ Browser scraping complete');
            }

            const duration = Date.now() - startTime;

            if (scrapedLeads.length > 0) {
                setResults(scrapedLeads);
                addScrapingJob({
                    url: normalizedUrl,
                    status: 'completed',
                    leads_found: scrapedLeads.length,
                    duration_ms: duration,
                });
                addToast(`Found ${scrapedLeads.length} lead(s) from ${new URL(normalizedUrl).hostname}`, 'success');
            } else {
                setError('No leads found on this website. Try a different URL with visible contact information.');
                addScrapingJob({
                    url: normalizedUrl,
                    status: 'completed',
                    leads_found: 0,
                    duration_ms: duration,
                });
            }
        } catch (err: any) {
            const duration = Date.now() - startTime;
            const errorMessage = err.message || 'Unknown error occurred';
            setError(errorMessage);
            addScrapingJob({
                url: normalizedUrl,
                status: 'failed',
                leads_found: 0,
                duration_ms: duration,
                error: errorMessage,
            });
            addToast('Scraping failed: ' + errorMessage, 'error');
        } finally {
            setIsLoading(false);
        }
    };

    const handleAddLead = (result: ScrapedResult, index: number) => {
        const matchedCategory = result.category_suggestion
            ? categories.find(c => c.name.toLowerCase() === result.category_suggestion!.toLowerCase())
            : null;

        const lead: Omit<Lead, 'id' | 'created_at'> = {
            company_name: result.company_name || 'Unknown',
            contact_name: result.contact_name || null,
            email: result.email || null,
            phone: result.phone || null,
            website: result.website || null,
            description: result.description || null,
            source_url: result.source_url,
            category_id: matchedCategory?.id || null,
            status: 'new',
        };

        addLead(lead);
        setAddedLeads(prev => new Set([...prev, index]));
        addToast(`Added "${lead.company_name}" to leads`, 'success');
    };

    const handleAddAll = () => {
        let count = 0;
        results.forEach((result, index) => {
            if (!addedLeads.has(index)) {
                const matchedCategory = result.category_suggestion
                    ? categories.find(c => c.name.toLowerCase() === result.category_suggestion!.toLowerCase())
                    : null;

                addLead({
                    company_name: result.company_name || 'Unknown',
                    contact_name: result.contact_name || null,
                    email: result.email || null,
                    phone: result.phone || null,
                    website: result.website || null,
                    description: result.description || null,
                    source_url: result.source_url,
                    category_id: matchedCategory?.id || null,
                    status: 'new',
                });
                count++;
            }
        });
        setAddedLeads(new Set(results.map((_, i) => i)));
        addToast(`Added ${count} leads to your collection`, 'success');
    };

    return (
        <div className="space-y-6 animate-fade-in-up">
            {/* Header */}
            <div>
                <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                        <Globe className="w-5 h-5 text-white" />
                    </div>
                    Scrape Website
                </h2>
                <p className="text-slate-400 mt-2">Enter a URL to extract leads, contact info, and company details.</p>
            </div>

            {/* URL Input Card */}
            <div className="glass-card p-6">
                <div className="flex flex-col sm:flex-row gap-3">
                    <div className="flex-1 relative">
                        <Globe className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Enter website URL (e.g., example.com)"
                            value={url}
                            onChange={e => setUrl(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleScrape()}
                            className="input-field pl-10"
                            disabled={isLoading}
                        />
                    </div>
                    <button
                        onClick={handleScrape}
                        disabled={isLoading || !url.trim()}
                        className="btn-primary flex items-center gap-2 px-6 whitespace-nowrap disabled:opacity-50"
                    >
                        {isLoading ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Scraping...
                            </>
                        ) : (
                            <>
                                <Zap className="w-4 h-4" />
                                Scrape for Leads
                            </>
                        )}
                    </button>
                </div>

                {/* Mode selector */}
                <div className="mt-4 flex items-center gap-4">
                    <span className="text-xs text-slate-500 font-medium">Engine:</span>
                    {[
                        { key: 'auto', label: 'Auto', icon: Zap, desc: 'Python → Browser fallback' },
                        { key: 'python', label: 'Python', icon: Server, desc: 'Backend only' },
                        { key: 'browser', label: 'Browser', icon: Wifi, desc: 'Client-side CORS proxy' },
                    ].map(mode => (
                        <button
                            key={mode.key}
                            onClick={() => setScrapingMode(mode.key as any)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${scrapingMode === mode.key
                                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                                : 'text-slate-500 hover:text-slate-300 border border-transparent'
                                }`}
                            title={mode.desc}
                        >
                            <mode.icon className="w-3.5 h-3.5" />
                            {mode.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Progress */}
            {isLoading && (
                <div className="glass-card p-5">
                    <div className="flex items-center gap-3">
                        <Loader2 className="w-5 h-5 animate-spin text-blue-400" />
                        <div>
                            <p className="text-white font-medium">Scraping in progress...</p>
                            <p className="text-sm text-slate-400 mt-0.5">{progress}</p>
                        </div>
                    </div>
                    <div className="mt-3 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full animate-pulse" style={{ width: '60%' }} />
                    </div>
                </div>
            )}

            {/* Error */}
            {error && (
                <div className="glass-card p-5 border-red-500/30">
                    <div className="flex items-start gap-3">
                        <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                        <div>
                            <p className="text-red-400 font-medium">Scraping Failed</p>
                            <p className="text-sm text-slate-400 mt-1">{error}</p>
                            <p className="text-xs text-slate-500 mt-2">
                                💡 Tip: Make sure the Python backend is running (`python backend/main.py`) for best results.
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Results */}
            {results.length > 0 && (
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-lg font-semibold text-white">
                                {results.length} Lead{results.length !== 1 ? 's' : ''} Found
                            </h3>
                            <p className="text-sm text-slate-400">
                                {pagesScraped} page(s) scraped
                            </p>
                        </div>
                        <button
                            onClick={handleAddAll}
                            disabled={addedLeads.size === results.length}
                            className="btn-primary text-sm flex items-center gap-2 disabled:opacity-50"
                        >
                            <Plus className="w-4 h-4" />
                            {addedLeads.size === results.length ? 'All Added' : `Add All (${results.length - addedLeads.size})`}
                        </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {results.map((result, index) => (
                            <div
                                key={index}
                                className={`glass-card p-5 transition-all ${addedLeads.has(index) ? 'opacity-60 border-emerald-500/30' : ''}`}
                            >
                                <div className="flex items-start justify-between mb-3">
                                    <div className="min-w-0">
                                        <h4 className="font-semibold text-white truncate">{result.company_name || 'Unknown'}</h4>
                                        {result.category_suggestion && (
                                            <span className="inline-block mt-1 px-2 py-0.5 text-[10px] font-semibold rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
                                                {result.category_suggestion}
                                            </span>
                                        )}
                                    </div>
                                    <button
                                        onClick={() => handleAddLead(result, index)}
                                        disabled={addedLeads.has(index)}
                                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex-shrink-0 ${addedLeads.has(index)
                                            ? 'bg-emerald-500/20 text-emerald-400'
                                            : 'btn-primary'
                                            }`}
                                    >
                                        {addedLeads.has(index) ? (
                                            <><CheckCircle2 className="w-3.5 h-3.5" /> Added</>
                                        ) : (
                                            <><Plus className="w-3.5 h-3.5" /> Add</>
                                        )}
                                    </button>
                                </div>

                                <div className="space-y-1.5 text-sm text-slate-400">
                                    {result.contact_name && <p>👤 {result.contact_name}</p>}
                                    {result.email && <p>📧 {result.email}</p>}
                                    {result.phone && <p>📞 {result.phone}</p>}
                                    {result.website && (
                                        <p className="flex items-center gap-1">
                                            🔗 <a href={result.website} target="_blank" rel="noopener noreferrer" className="hover:text-blue-400 truncate transition-colors">
                                                {result.website.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}
                                                <ExternalLink className="w-3 h-3 inline ml-1" />
                                            </a>
                                        </p>
                                    )}
                                </div>

                                {result.description && (
                                    <p className="text-xs text-slate-500 mt-3 pt-3 border-t border-slate-700/50 line-clamp-2">
                                        {result.description}
                                    </p>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Getting Started */}
            {!isLoading && results.length === 0 && !error && (
                <div className="glass-card p-10 text-center">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 mx-auto flex items-center justify-center mb-5">
                        <Zap className="w-8 h-8 text-blue-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-white mb-2">Ready to Scrape</h3>
                    <p className="text-slate-400 max-w-md mx-auto mb-6">
                        Enter any website URL above to automatically extract emails, phone numbers, company details, and more.
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-lg mx-auto">
                        {[
                            { mode: '🐍 Python Backend', desc: 'Multi-page crawl, best accuracy' },
                            { mode: '🌐 Browser Scraping', desc: 'CORS proxy, no setup needed' },
                            { mode: '⚡ Auto Mode', desc: 'Python first, browser fallback' },
                        ].map(({ mode, desc }) => (
                            <div key={mode} className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/30">
                                <p className="text-sm font-medium text-white">{mode}</p>
                                <p className="text-xs text-slate-500 mt-1">{desc}</p>
                            </div>
                        ))}
                    </div>
                    <div className="mt-6 p-4 rounded-xl bg-slate-800/30 border border-slate-700/30 max-w-md mx-auto text-left">
                        <p className="text-xs text-slate-400">
                            <strong className="text-slate-300">💡 For best results:</strong> Start the Python backend:
                        </p>
                        <code className="block mt-2 text-xs text-cyan-400 bg-slate-900/50 rounded-lg px-3 py-2 font-mono">
                            python backend/main.py
                        </code>
                    </div>
                </div>
            )}
        </div>
    );
}
