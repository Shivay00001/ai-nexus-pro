import { useState } from 'react';
import { Tag, Plus, Edit3, Trash2, X, Check } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Category } from '../types';

export function CategoriesView() {
    const { categories, addCategory, updateCategory, deleteCategory, leads } = useApp();
    const [showAdd, setShowAdd] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [color, setColor] = useState('#3B82F6');
    const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

    const presetColors = [
        '#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444',
        '#06B6D4', '#EC4899', '#6366F1', '#F97316', '#14B8A6',
        '#A855F7', '#6B7280',
    ];

    const handleStartAdd = () => {
        setShowAdd(true);
        setEditingId(null);
        setName('');
        setDescription('');
        setColor('#3B82F6');
    };

    const handleStartEdit = (cat: Category) => {
        setEditingId(cat.id);
        setShowAdd(false);
        setName(cat.name);
        setDescription(cat.description);
        setColor(cat.color);
    };

    const handleSave = () => {
        if (!name.trim()) return;
        if (editingId) {
            updateCategory(editingId, { name: name.trim(), description: description.trim(), color });
            setEditingId(null);
        } else {
            addCategory({ name: name.trim(), description: description.trim(), color });
            setShowAdd(false);
        }
        setName('');
        setDescription('');
        setColor('#3B82F6');
    };

    const handleCancel = () => {
        setShowAdd(false);
        setEditingId(null);
        setName('');
        setDescription('');
    };

    const handleDeleteConfirm = (id: string) => {
        deleteCategory(id);
        setConfirmDelete(null);
    };

    return (
        <div className="space-y-6 animate-fade-in-up">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-white">Categories</h2>
                    <p className="text-slate-400 mt-1">Organize your leads into meaningful categories</p>
                </div>
                <button onClick={handleStartAdd} className="btn-primary text-sm flex items-center gap-2">
                    <Plus className="w-4 h-4" /> Add Category
                </button>
            </div>

            {/* Add Form */}
            {showAdd && (
                <div className="glass-card p-5 animate-fade-in-up border-blue-500/20">
                    <h3 className="font-semibold text-white mb-4">New Category</h3>
                    <div className="space-y-3">
                        <input
                            type="text"
                            value={name}
                            onChange={e => setName(e.target.value)}
                            placeholder="Category name"
                            className="input-field"
                            autoFocus
                        />
                        <input
                            type="text"
                            value={description}
                            onChange={e => setDescription(e.target.value)}
                            placeholder="Description (optional)"
                            className="input-field"
                        />
                        <div>
                            <label className="block text-xs text-slate-400 mb-2 font-medium">Color</label>
                            <div className="flex flex-wrap gap-2">
                                {presetColors.map(c => (
                                    <button
                                        key={c}
                                        onClick={() => setColor(c)}
                                        className={`w-8 h-8 rounded-lg transition-all ${color === c ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800 scale-110' : 'hover:scale-110'}`}
                                        style={{ backgroundColor: c }}
                                    />
                                ))}
                            </div>
                        </div>
                        <div className="flex justify-end gap-2 pt-2">
                            <button onClick={handleCancel} className="btn-secondary text-sm">Cancel</button>
                            <button onClick={handleSave} disabled={!name.trim()} className="btn-primary text-sm disabled:opacity-50">Create Category</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Categories List */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {categories.map((cat, i) => {
                    const leadCount = leads.filter(l => l.category_id === cat.id).length;
                    const isEditing = editingId === cat.id;

                    return (
                        <div
                            key={cat.id}
                            className="glass-card-hover p-5 animate-fade-in-up"
                            style={{ animationDelay: `${Math.min(i, 8) * 50}ms` }}
                        >
                            {isEditing ? (
                                <div className="space-y-3">
                                    <input type="text" value={name} onChange={e => setName(e.target.value)} className="input-field text-sm" autoFocus />
                                    <input type="text" value={description} onChange={e => setDescription(e.target.value)} className="input-field text-sm" placeholder="Description" />
                                    <div className="flex flex-wrap gap-1.5">
                                        {presetColors.map(c => (
                                            <button
                                                key={c}
                                                onClick={() => setColor(c)}
                                                className={`w-6 h-6 rounded-md transition-all ${color === c ? 'ring-2 ring-white scale-110' : 'hover:scale-110'}`}
                                                style={{ backgroundColor: c }}
                                            />
                                        ))}
                                    </div>
                                    <div className="flex justify-end gap-2">
                                        <button onClick={handleCancel} className="p-1.5 rounded-lg text-slate-500 hover:text-white hover:bg-slate-700/60 transition-all">
                                            <X className="w-4 h-4" />
                                        </button>
                                        <button onClick={handleSave} className="p-1.5 rounded-lg text-emerald-400 hover:text-white hover:bg-emerald-500/20 transition-all">
                                            <Check className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <>
                                    <div className="flex items-start justify-between mb-3">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: cat.color + '25' }}>
                                                <Tag className="w-5 h-5" style={{ color: cat.color }} />
                                            </div>
                                            <div>
                                                <h3 className="font-semibold text-white">{cat.name}</h3>
                                                <p className="text-xs text-slate-500">{leadCount} lead{leadCount !== 1 ? 's' : ''}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <button onClick={() => handleStartEdit(cat)} className="p-1.5 rounded-lg text-slate-500 hover:text-blue-400 hover:bg-slate-700/60 transition-all">
                                                <Edit3 className="w-4 h-4" />
                                            </button>
                                            <button onClick={() => setConfirmDelete(cat.id)} className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-slate-700/60 transition-all">
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                    {cat.description && (
                                        <p className="text-sm text-slate-400">{cat.description}</p>
                                    )}
                                    <div className="mt-3 pt-3 border-t border-slate-700/50">
                                        <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
                                            <div
                                                className="h-full rounded-full transition-all duration-500"
                                                style={{
                                                    width: leads.length > 0 ? `${Math.max((leadCount / leads.length) * 100, 2)}%` : '0%',
                                                    backgroundColor: cat.color,
                                                }}
                                            />
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Delete Confirmation */}
            {confirmDelete && (
                <div className="modal-overlay" onClick={() => setConfirmDelete(null)}>
                    <div className="modal-content max-w-sm" onClick={e => e.stopPropagation()}>
                        <h3 className="text-lg font-semibold text-white mb-2">Delete Category?</h3>
                        <p className="text-slate-400 text-sm mb-6">
                            Leads in this category will become uncategorized. This cannot be undone.
                        </p>
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
