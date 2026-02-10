import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { Lead, Category, ScrapingJob, ViewType, Toast } from '../types';

const DEFAULT_CATEGORIES: Omit<Category, 'id' | 'created_at'>[] = [
    { name: 'Technology', description: 'Technology and software companies', color: '#3B82F6' },
    { name: 'Healthcare', description: 'Healthcare and medical services', color: '#10B981' },
    { name: 'Finance', description: 'Financial services and banking', color: '#F59E0B' },
    { name: 'E-commerce', description: 'Online retail and e-commerce', color: '#8B5CF6' },
    { name: 'Marketing', description: 'Marketing and advertising agencies', color: '#EF4444' },
    { name: 'Real Estate', description: 'Real estate and property services', color: '#06B6D4' },
    { name: 'Education', description: 'Educational institutions and services', color: '#EC4899' },
    { name: 'Manufacturing', description: 'Manufacturing and industrial', color: '#6366F1' },
    { name: 'Other', description: 'Uncategorized leads', color: '#6B7280' },
];

type AppContextType = {
    currentView: ViewType;
    setCurrentView: (v: ViewType) => void;

    leads: Lead[];
    addLead: (lead: Omit<Lead, 'id' | 'created_at' | 'updated_at'>) => void;
    addLeads: (leads: Omit<Lead, 'id' | 'created_at' | 'updated_at'>[]) => void;
    updateLead: (id: string, updates: Partial<Lead>) => void;
    deleteLead: (id: string) => void;

    categories: Category[];
    addCategory: (cat: Omit<Category, 'id' | 'created_at'>) => void;
    updateCategory: (id: string, updates: Partial<Category>) => void;
    deleteCategory: (id: string) => void;

    scrapingJobs: ScrapingJob[];
    addScrapingJob: (job: ScrapingJob) => void;
    updateScrapingJob: (id: string, updates: Partial<ScrapingJob>) => void;

    searchQuery: string;
    setSearchQuery: (q: string) => void;
    selectedCategory: string | null;
    setSelectedCategory: (id: string | null) => void;
    selectedStatus: string | null;
    setSelectedStatus: (s: string | null) => void;

    toasts: Toast[];
    addToast: (message: string, type: Toast['type']) => void;
    removeToast: (id: string) => void;
};

const AppContext = createContext<AppContextType | undefined>(undefined);

function loadFromStorage<T>(key: string, fallback: T): T {
    try {
        const stored = localStorage.getItem(key);
        return stored ? JSON.parse(stored) : fallback;
    } catch {
        return fallback;
    }
}

function saveToStorage<T>(key: string, value: T) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch {
        // localStorage full or inaccessible
    }
}

function initializeCategories(): Category[] {
    const stored = loadFromStorage<Category[]>('lsp_categories', []);
    if (stored.length > 0) return stored;
    const now = new Date().toISOString();
    const cats = DEFAULT_CATEGORIES.map(c => ({
        ...c,
        id: crypto.randomUUID(),
        created_at: now,
    }));
    saveToStorage('lsp_categories', cats);
    return cats;
}

export function AppProvider({ children }: { children: ReactNode }) {
    const [currentView, setCurrentView] = useState<ViewType>('dashboard');
    const [leads, setLeads] = useState<Lead[]>(() => loadFromStorage('lsp_leads', []));
    const [categories, setCategories] = useState<Category[]>(() => initializeCategories());
    const [scrapingJobs, setScrapingJobs] = useState<ScrapingJob[]>(() => loadFromStorage('lsp_jobs', []));
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
    const [selectedStatus, setSelectedStatus] = useState<string | null>(null);
    const [toasts, setToasts] = useState<Toast[]>([]);

    useEffect(() => { saveToStorage('lsp_leads', leads); }, [leads]);
    useEffect(() => { saveToStorage('lsp_categories', categories); }, [categories]);
    useEffect(() => { saveToStorage('lsp_jobs', scrapingJobs); }, [scrapingJobs]);

    const addToast = useCallback((message: string, type: Toast['type']) => {
        const id = crypto.randomUUID();
        setToasts(prev => [...prev, { id, message, type }]);
        setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
    }, []);

    const removeToast = useCallback((id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    const addLead = useCallback((lead: Omit<Lead, 'id' | 'created_at' | 'updated_at'>) => {
        const now = new Date().toISOString();
        const newLead: Lead = { ...lead, id: crypto.randomUUID(), created_at: now, updated_at: now };
        setLeads(prev => [newLead, ...prev]);
        addToast('Lead added successfully', 'success');
    }, [addToast]);

    const addLeads = useCallback((newLeads: Omit<Lead, 'id' | 'created_at' | 'updated_at'>[]) => {
        const now = new Date().toISOString();
        const leadsWithIds = newLeads.map(l => ({
            ...l,
            id: crypto.randomUUID(),
            created_at: now,
            updated_at: now,
        }));
        setLeads(prev => [...leadsWithIds, ...prev]);
    }, []);

    const updateLead = useCallback((id: string, updates: Partial<Lead>) => {
        setLeads(prev => prev.map(l =>
            l.id === id ? { ...l, ...updates, updated_at: new Date().toISOString() } : l
        ));
        addToast('Lead updated', 'success');
    }, [addToast]);

    const deleteLead = useCallback((id: string) => {
        setLeads(prev => prev.filter(l => l.id !== id));
        addToast('Lead deleted', 'info');
    }, [addToast]);

    const addCategory = useCallback((cat: Omit<Category, 'id' | 'created_at'>) => {
        const newCat: Category = { ...cat, id: crypto.randomUUID(), created_at: new Date().toISOString() };
        setCategories(prev => [...prev, newCat]);
        addToast('Category added', 'success');
    }, [addToast]);

    const updateCategory = useCallback((id: string, updates: Partial<Category>) => {
        setCategories(prev => prev.map(c => (c.id === id ? { ...c, ...updates } : c)));
        addToast('Category updated', 'success');
    }, [addToast]);

    const deleteCategory = useCallback((id: string) => {
        setCategories(prev => prev.filter(c => c.id !== id));
        setLeads(prev => prev.map(l => (l.category_id === id ? { ...l, category_id: null } : l)));
        addToast('Category deleted', 'info');
    }, [addToast]);

    const addScrapingJob = useCallback((job: ScrapingJob) => {
        setScrapingJobs(prev => [job, ...prev]);
    }, []);

    const updateScrapingJob = useCallback((id: string, updates: Partial<ScrapingJob>) => {
        setScrapingJobs(prev => prev.map(j => (j.id === id ? { ...j, ...updates } : j)));
    }, []);

    return (
        <AppContext.Provider
            value={{
                currentView, setCurrentView,
                leads, addLead, addLeads, updateLead, deleteLead,
                categories, addCategory, updateCategory, deleteCategory,
                scrapingJobs, addScrapingJob, updateScrapingJob,
                searchQuery, setSearchQuery,
                selectedCategory, setSelectedCategory,
                selectedStatus, setSelectedStatus,
                toasts, addToast, removeToast,
            }}
        >
            {children}
        </AppContext.Provider>
    );
}

export function useApp() {
    const ctx = useContext(AppContext);
    if (!ctx) throw new Error('useApp must be used within AppProvider');
    return ctx;
}
