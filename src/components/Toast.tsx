import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';
import { useApp } from '../context/AppContext';

export function ToastContainer() {
    const { toasts, removeToast } = useApp();

    if (toasts.length === 0) return null;

    const icons = {
        success: CheckCircle2,
        error: AlertCircle,
        info: Info,
    };

    const colors = {
        success: 'border-emerald-500/30 bg-emerald-500/10',
        error: 'border-red-500/30 bg-red-500/10',
        info: 'border-blue-500/30 bg-blue-500/10',
    };

    const textColors = {
        success: 'text-emerald-400',
        error: 'text-red-400',
        info: 'text-blue-400',
    };

    return (
        <div className="fixed bottom-6 right-6 z-[100] space-y-2 max-w-sm">
            {toasts.map(toast => {
                const Icon = icons[toast.type];
                return (
                    <div
                        key={toast.id}
                        className={`flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-xl ${colors[toast.type]} animate-slide-in-right shadow-2xl`}
                    >
                        <Icon className={`w-5 h-5 flex-shrink-0 ${textColors[toast.type]}`} />
                        <p className="text-sm text-slate-200 flex-1">{toast.message}</p>
                        <button
                            onClick={() => removeToast(toast.id)}
                            className="text-slate-500 hover:text-slate-300 transition-colors flex-shrink-0"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                );
            })}
        </div>
    );
}
