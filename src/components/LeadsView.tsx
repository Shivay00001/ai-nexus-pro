import { useState, useMemo } from 'react';
import {
    Search, Plus, Download, Upload, Trash2, Edit3, Mail, Phone, Globe,
    ExternalLink, User, Users, Filter, Grid3X3, List, X,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { LeadModal } from './LeadModal';
import { Lead } from '../types';

export function LeadsView() {
    const {
        leads, deleteLead, categories,
        searchQuery, setSearchQuery,
        selectedCategory, setSelectedCategory,
        selectedStatus, setSelectedStatus,
        addLeads, addToast,
    } = useApp();

    const [editingLead, setEditingLead] = useState<Lead | null>(null);
    const [showAddModal, setShowAddModal] = useState(false);
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    const [showFilters, setShowFilters] = useState(false);
    const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

    const filteredLeads = useMemo(() => {
        return leads.filter(lead => {
            const matchesSearch = !searchQuery || [
                lead.company_name, lead.contact_name, lead.email, lead.phone, lead.description,
            ].some(field => field?.toLowerCase().includes(searchQuery.toLowerCase()));

            const matchesCategory = !selectedCategory || lead.category_id === selectedCategory;
            const matchesStatus = !selectedStatus || lead.status === selectedStatus;

            return matchesSearch && matchesCategory && matchesStatus;
        });
    }, [leads, searchQuery, selectedCategory, selectedStatus]);

    const handleExportCSV = () => {
        const headers = ['Company', 'Contact', 'Email', 'Phone', 'Website', 'Category', 'Status', 'Description', 'Source'];
        const rows = filteredLeads.map(lead => {
            const cat = categories.find(c => c.id === lead.category_id);
            return [lead.company_name, lead.contact_name, lead.email, lead.phone, lead.website, cat?.name || '', lead.status, lead.description, lead.source_url]
                .map(f => `"${(f || '').replace(/"/g, '""')}"`);
        });
        const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `leads-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        addToast(`Exported ${filteredLeads.length} leads to CSV`, 'success');
    };

    const handleImportCSV = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            const text = ev.target?.result as string;
            const lines = text.split('\n').filter(l => l.trim());
            if (lines.length < 2) { addToast('CSV file is empty or invalid', 'error'); return; }

            const header = lines[0].toLowerCase();
            const hasHeader = header.includes('company') || header.includes('email') || header.includes('name');
            const dataLines = hasHeader ? lines.slice(1) : lines;

            const importedLeads = dataLines.map(line => {
                const cols = line.match(/(".*?"|[^",]+)(?=\s*,|\s*$)/g)?.map(c => c.replace(/^"|"$/g, '').replace(/""/g, '"')) || [];
                return {
                    company_name: cols[0] || '',
                    contact_name: cols[1] || '',
                    email: cols[2] || '',
                    phone: cols[3] || '',
                    website: cols[4] || '',
                    category_id: null,
                    status: 'new',
                    description: cols[7] || cols[5] || '',
                    source_url: cols[8] || cols[6] || 'CSV Import',
                };
            }).filter(l => l.company_name || l.email || l.phone);

            if (importedLeads.length > 0) {
                addLeads(importedLeads);
                addToast(`Imported ${importedLeads.length} leads from CSV`, 'success');
            } else {
                addToast('No valid leads found in CSV', 'error');
            }
        };
        reader.readAsText(file);
        e.target.value = '';
    };

    const handleDeleteConfirm = (id: string) => {
        deleteLead(id);
        setConfirmDelete(null);
    };

    const statusColors: Record<string, string> = {
        new: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
        contacted: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
        qualified: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
        closed: 'bg-slate-500/15 text-slate-400 border-slate-500/30',
    };

    const activeFilters = [selectedCategory, selectedStatus].filter(Boolean).length;

    return (
        <div className="space-y-5 animate-fade-in-up">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-white">Leads</h2>
                    <p className="text-slate-400 mt-1">{filteredLeads.length} of {leads.length} leads</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                    <label className="btn-secondary text-sm flex items-center gap-2 cursor-pointer">
                        <Upload className="w-4 h-4" />
                        Import
                        <input type="file" accept=".csv" onChange={handleImportCSV} className="hidden" />
                    </label>
                    {filteredLeads.length > 0 && (
                        <button onClick={handleExportCSV} className="btn-secondary text-sm flex items-center gap-2">
                            <Download className="w-4 h-4" /> Export
                        </button>
                    )}
                    <button onClick={() => setShowAddModal(true)} className="btn-primary text-sm flex items-center gap-2">
                        <Plus className="w-4 h-4" /> Add Lead
                    </button>
                </div>
            </div>

            {/* Search & Filter Bar */}
            <div className="glass-card p-4">
                <div className="flex flex-col sm:flex-row gap-3">
                    <div className="flex-1 relative">
                        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Search leads by name, email, phone..."
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            className="input-field pl-10"
                        />
                        {searchQuery && (
                            <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300" title="Clear search">
                                <X className="w-4 h-4" />
                            </button>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setShowFilters(!showFilters)}
                            className={`btn-secondary text-sm flex items-center gap-2 ${showFilters ? 'ring-2 ring-blue-500/40' : ''}`}
                            title="Toggle filters"
                        >
                            <Filter className="w-4 h-4" />
                            Filters
                            {activeFilters > 0 && (
                                <span className="bg-blue-500 text-white text-[10px] font-bold w-5 h-5 rounded-full flex items-center justify-center">{activeFilters}</span>
                            )}
                        </button>
                        <div className="flex bg-slate-800/60 rounded-xl border border-slate-700/50">
                            <button
                                onClick={() => setViewMode('grid')}
                                className={`p-2.5 rounded-l-xl transition-colors ${viewMode === 'grid' ? 'bg-slate-700/60 text-white' : 'text-slate-500 hover:text-slate-300'}`}
                                title="Grid view"
                            >
                                <Grid3X3 className="w-4 h-4" />
                            </button>
                            <button
                                onClick={() => setViewMode('list')}
                                className={`p-2.5 rounded-r-xl transition-colors ${viewMode === 'list' ? 'bg-slate-700/60 text-white' : 'text-slate-500 hover:text-slate-300'}`}
                                title="List view"
                            >
                                <List className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>

                {/* Filter Panel */}
                {showFilters && (
                    <div className="mt-4 pt-4 border-t border-slate-700/50 flex flex-wrap gap-3 animate-fade-in">
                        <div>
                            <label className="block text-xs text-slate-400 mb-1.5 font-medium" htmlFor="cat-filter">Category</label>
                            <select
                                id="cat-filter"
                                value={selectedCategory || ''}
                                onChange={e => setSelectedCategory(e.target.value || null)}
                                className="select-field text-sm"
                            >
                                <option value="">All Categories</option>
                                {categories.map(c => (
                                    <option key={c.id} value={c.id}>{c.name}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs text-slate-400 mb-1.5 font-medium" htmlFor="status-filter">Status</label>
                            <select
                                id="status-filter"
                                value={selectedStatus || ''}
                                onChange={e => setSelectedStatus(e.target.value || null)}
                                className="select-field text-sm"
                            >
                                <option value="">All Statuses</option>
                                <option value="new">New</option>
                                <option value="contacted">Contacted</option>
                                <option value="qualified">Qualified</option>
                                <option value="closed">Closed</option>
                            </select>
                        </div>
                        {activeFilters > 0 && (
                            <div className="flex items-end">
                                <button
                                    onClick={() => { setSelectedCategory(null); setSelectedStatus(null); }}
                                    className="text-sm text-red-400 hover:text-red-300 transition-colors"
                                >
                                    Clear Filters
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Lead Cards */}
            {filteredLeads.length === 0 ? (
                <div className="glass-card p-16 text-center">
                    <Users className="w-14 h-14 text-slate-600 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-white mb-2">
                        {leads.length === 0 ? 'No leads yet' : 'No matching leads'}
                    </h3>
                    <p className="text-slate-400 mb-6">
                        {leads.length === 0
                            ? 'Start by scraping a website or adding leads manually.'
                            : 'Try adjusting your filters or search query.'}
                    </p>
                    {leads.length === 0 && (
                        <button onClick={() => setShowAddModal(true)} className="btn-primary">
                            <Plus className="w-4 h-4 inline mr-2" /> Add Your First Lead
                        </button>
                    )}
                </div>
            ) : viewMode === 'grid' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {filteredLeads.map((lead, i) => {
                        const cat = categories.find(c => c.id === lead.category_id);
                        return (
                            <div
                                key={lead.id}
                                className="glass-card-hover p-5 animate-fade-in-up"
                                style={{ animationDelay: `${Math.min(i, 11) * 40}ms` }}
                            >
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-3 min-w-0">
                                        <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-slate-700 to-slate-600 flex items-center justify-center text-base font-bold text-white flex-shrink-0">
                                            {(lead.company_name || '?')[0].toUpperCase()}
                                        </div>
                                        <div className="min-w-0">
                                            <h3 className="font-semibold text-white truncate">{lead.company_name || 'Unknown'}</h3>
                                            {cat && (
                                                <span className="inline-block px-2 py-0.5 text-[10px] font-semibold rounded-full text-white mt-1" style={{ backgroundColor: cat.color }}>
                                                    {cat.name}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-1 flex-shrink-0">
                                        <button onClick={() => setEditingLead(lead)} className="p-1.5 rounded-lg text-slate-500 hover:text-blue-400 hover:bg-slate-700/60 transition-all" title="Edit lead">
                                            <Edit3 className="w-4 h-4" />
                                        </button>
                                        <button onClick={() => setConfirmDelete(lead.id)} className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-slate-700/60 transition-all" title="Delete lead">
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>

                                <div className="space-y-2 text-sm">
                                    {lead.contact_name && (
                                        <div className="flex items-center gap-2 text-slate-400">
                                            <User className="w-3.5 h-3.5 flex-shrink-0" />
                                            <span className="truncate">{lead.contact_name}</span>
                                        </div>
                                    )}
                                    {lead.email && (
                                        <div className="flex items-center gap-2 text-slate-400">
                                            <Mail className="w-3.5 h-3.5 flex-shrink-0" />
                                            <a href={`mailto:${lead.email}`} className="truncate hover:text-blue-400 transition-colors">{lead.email}</a>
                                        </div>
                                    )}
                                    {lead.phone && (
                                        <div className="flex items-center gap-2 text-slate-400">
                                            <Phone className="w-3.5 h-3.5 flex-shrink-0" />
                                            <a href={`tel:${lead.phone}`} className="hover:text-blue-400 transition-colors">{lead.phone}</a>
                                        </div>
                                    )}
                                    {lead.website && (
                                        <div className="flex items-center gap-2 text-slate-400">
                                            <Globe className="w-3.5 h-3.5 flex-shrink-0" />
                                            <a href={lead.website} target="_blank" rel="noopener noreferrer" className="truncate hover:text-blue-400 transition-colors flex items-center gap-1">
                                                {lead.website.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}
                                                <ExternalLink className="w-3 h-3 flex-shrink-0" />
                                            </a>
                                        </div>
                                    )}
                                </div>

                                {lead.description && (
                                    <p className="text-xs text-slate-500 mt-3 pt-3 border-t border-slate-700/50 line-clamp-2">{lead.description}</p>
                                )}

                                <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-700/50">
                                    <span className={`status-badge border ${statusColors[lead.status] || statusColors.new}`}>
                                        {lead.status}
                                    </span>
                                    <span className="text-[11px] text-slate-500">
                                        {new Date(lead.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            ) : (
                <div className="glass-card overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-slate-700/50">
                                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Company</th>
                                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Contact</th>
                                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Email</th>
                                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Category</th>
                                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredLeads.map(lead => {
                                    const cat = categories.find(c => c.id === lead.category_id);
                                    return (
                                        <tr key={lead.id} className="border-b border-slate-700/30 hover:bg-slate-800/30 transition-colors">
                                            <td className="px-4 py-3">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-lg bg-slate-700/60 flex items-center justify-center text-xs font-bold text-slate-300">
                                                        {(lead.company_name || '?')[0].toUpperCase()}
                                                    </div>
                                                    <span className="text-sm font-medium text-white">{lead.company_name || 'Unknown'}</span>
                                                </div>
                                            </td>
                                            <td className="px-4 py-3 text-sm text-slate-400">{lead.contact_name || '—'}</td>
                                            <td className="px-4 py-3 text-sm text-slate-400">{lead.email || '—'}</td>
                                            <td className="px-4 py-3">
                                                {cat ? (
                                                    <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full text-white" style={{ backgroundColor: cat.color }}>
                                                        {cat.name}
                                                    </span>
                                                ) : <span className="text-slate-500">—</span>}
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className={`status-badge border ${statusColors[lead.status] || statusColors.new}`}>
                                                    {lead.status}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-right">
                                                <div className="flex items-center justify-end gap-1">
                                                    <button onClick={() => setEditingLead(lead)} className="p-1.5 rounded-lg text-slate-500 hover:text-blue-400 hover:bg-slate-700/60 transition-all" title="Edit lead">
                                                        <Edit3 className="w-4 h-4" />
                                                    </button>
                                                    <button onClick={() => setConfirmDelete(lead.id)} className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-slate-700/60 transition-all" title="Delete lead">
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Add/Edit Modal */}
            {(showAddModal || editingLead) && (
                <LeadModal
                    lead={editingLead}
                    onClose={() => { setShowAddModal(false); setEditingLead(null); }}
                />
            )}

            {/* Delete Confirmation */}
            {confirmDelete && (
                <div className="modal-overlay" onClick={() => setConfirmDelete(null)}>
                    <div className="modal-content max-w-sm" onClick={e => e.stopPropagation()}>
                        <h3 className="text-lg font-semibold text-white mb-2">Delete Lead?</h3>
                        <p className="text-slate-400 text-sm mb-6">This action cannot be undone. The lead will be permanently removed.</p>
                        <div className="flex justify-end gap-3">
                            <button onClick={() => setConfirmDelete(null)} className="btn-secondary text-sm">Cancel</button>
                            <button onClick={() => handleDeleteConfirm(confirmDelete)} className="btn-danger text-sm">Delete</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
