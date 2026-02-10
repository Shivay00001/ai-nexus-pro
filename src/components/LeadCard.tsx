import { Building2, User, Mail, Phone, Globe, ExternalLink, Trash2, Edit } from 'lucide-react';
import { Lead, Category } from '../lib/supabase';

type LeadCardProps = {
  lead: Lead;
  category: Category | undefined;
  onDelete: (id: string) => void;
  onStatusChange: (id: string, status: string) => void;
};

export function LeadCard({ lead, category, onDelete, onStatusChange }: LeadCardProps) {
  const statusOptions = ['new', 'contacted', 'qualified', 'closed'];

  const statusColors: Record<string, string> = {
    new: 'bg-green-100 text-green-800',
    contacted: 'bg-blue-100 text-blue-800',
    qualified: 'bg-amber-100 text-amber-800',
    closed: 'bg-gray-100 text-gray-800',
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            {lead.company_name && (
              <h3 className="text-lg font-semibold text-gray-900">{lead.company_name}</h3>
            )}
            {category && (
              <span
                className="px-2 py-1 text-xs font-medium rounded-full text-white"
                style={{ backgroundColor: category.color }}
              >
                {category.name}
              </span>
            )}
          </div>
          <select
            value={lead.status}
            onChange={(e) => onStatusChange(lead.id, e.target.value)}
            className={`px-3 py-1 rounded-full text-xs font-medium ${
              statusColors[lead.status] || statusColors.new
            } border-0 cursor-pointer`}
          >
            {statusOptions.map((status) => (
              <option key={status} value={status}>
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={() => onDelete(lead.id)}
          className="text-red-500 hover:text-red-700 transition-colors"
          title="Delete lead"
        >
          <Trash2 className="w-5 h-5" />
        </button>
      </div>

      <div className="space-y-2 text-sm">
        {lead.contact_name && (
          <div className="flex items-center gap-2 text-gray-700">
            <User className="w-4 h-4 text-gray-400" />
            <span>{lead.contact_name}</span>
          </div>
        )}
        {lead.email && (
          <div className="flex items-center gap-2 text-gray-700">
            <Mail className="w-4 h-4 text-gray-400" />
            <a href={`mailto:${lead.email}`} className="hover:text-blue-600 transition-colors">
              {lead.email}
            </a>
          </div>
        )}
        {lead.phone && (
          <div className="flex items-center gap-2 text-gray-700">
            <Phone className="w-4 h-4 text-gray-400" />
            <a href={`tel:${lead.phone}`} className="hover:text-blue-600 transition-colors">
              {lead.phone}
            </a>
          </div>
        )}
        {lead.website && (
          <div className="flex items-center gap-2 text-gray-700">
            <Globe className="w-4 h-4 text-gray-400" />
            <a
              href={lead.website}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-600 transition-colors flex items-center gap-1"
            >
              {lead.website}
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}
        {lead.description && (
          <p className="text-gray-600 mt-3 pt-3 border-t border-gray-100">{lead.description}</p>
        )}
        {lead.source_url && (
          <div className="flex items-center gap-2 text-xs text-gray-500 mt-3 pt-3 border-t border-gray-100">
            <span>Source:</span>
            <a
              href={lead.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-600 transition-colors truncate flex items-center gap-1"
            >
              {lead.source_url}
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
