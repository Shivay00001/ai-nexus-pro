import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Lead } from '../types';

type Props = {
    lead: Lead | null;
    onClose: () => void;
};

export function LeadModal({ lead, onClose }: Props) {
    const { addLead, updateLead, categories } = useApp();
    const isEditing = !!lead;

    const [form, setForm] = useState({
        company_name: '',
        contact_name: '',
        email: '',
        phone: '',
        website: '',
        description: '',
        source_url: '',
        category_id: '' as string | null,
        status: 'new',
    });

    useEffect(() => {
        if (lead) {
            setForm({
                company_name: lead.company_name,
                contact_name: lead.contact_name,
                email: lead.email,
                phone: lead.phone,
                website: lead.website,
                description: lead.description,
                source_url: lead.source_url,
                category_id: lead.category_id,
                status: lead.status,
            });
        }
    }, [lead]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const data = {
            ...form,
            category_id: form.category_id || null,
        };

        if (isEditing) {
            updateLead(lead.id, data);
        } else {
            addLead(data);
        }
        onClose();
    };

    const updateField = (field: string, value: string) => {
        setForm(prev => ({ ...prev, [field]: value }));
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content max-w-xl" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-white">
                        {isEditing ? 'Edit Lead' : 'Add New Lead'}
                    </h2>
                    <button onClick={onClose} className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-700/60 transition-all">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">Company Name *</label>
                            <input
                                type="text"
                                value={form.company_name}
                                onChange={e => updateField('company_name', e.target.value)}
                                className="input-field"
                                placeholder="Acme Inc."
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">Contact Name</label>
                            <input
                                type="text"
                                value={form.contact_name}
                                onChange={e => updateField('contact_name', e.target.value)}
                                className="input-field"
                                placeholder="John Doe"
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
                            <input
                                type="email"
                                value={form.email}
                                onChange={e => updateField('email', e.target.value)}
                                className="input-field"
                                placeholder="john@acme.com"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">Phone</label>
                            <input
                                type="tel"
                                value={form.phone}
                                onChange={e => updateField('phone', e.target.value)}
                                className="input-field"
                                placeholder="+1 (555) 123-4567"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1.5">Website</label>
                        <input
                            type="url"
                            value={form.website}
                            onChange={e => updateField('website', e.target.value)}
                            className="input-field"
                            placeholder="https://acme.com"
                        />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">Category</label>
                            <select
                                value={form.category_id || ''}
                                onChange={e => updateField('category_id', e.target.value)}
                                className="select-field w-full"
                            >
                                <option value="">Uncategorized</option>
                                {categories.map(c => (
                                    <option key={c.id} value={c.id}>{c.name}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">Status</label>
                            <select
                                value={form.status}
                                onChange={e => updateField('status', e.target.value)}
                                className="select-field w-full"
                            >
                                <option value="new">New</option>
                                <option value="contacted">Contacted</option>
                                <option value="qualified">Qualified</option>
                                <option value="closed">Closed</option>
                            </select>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1.5">Description</label>
                        <textarea
                            value={form.description}
                            onChange={e => updateField('description', e.target.value)}
                            className="input-field resize-none"
                            rows={3}
                            placeholder="Additional notes about this lead..."
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1.5">Source URL</label>
                        <input
                            type="url"
                            value={form.source_url}
                            onChange={e => updateField('source_url', e.target.value)}
                            className="input-field"
                            placeholder="Where was this lead found?"
                        />
                    </div>

                    <div className="flex justify-end gap-3 pt-4 border-t border-slate-700/50">
                        <button type="button" onClick={onClose} className="btn-secondary">
                            Cancel
                        </button>
                        <button type="submit" className="btn-primary">
                            {isEditing ? 'Save Changes' : 'Add Lead'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
