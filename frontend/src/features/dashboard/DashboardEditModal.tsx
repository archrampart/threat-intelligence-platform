import { useState, useEffect } from "react";
import { X, Eye, EyeOff, Check } from "lucide-react";
import { WIDGET_CONFIGS, getWidgetVisibility, saveWidgetVisibility, type WidgetConfig } from "./widgetConfig";

interface DashboardEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (visibility: Record<string, boolean>) => void;
}

const DashboardEditModal = ({ isOpen, onClose, onSave }: DashboardEditModalProps) => {
  const [visibility, setVisibility] = useState<Record<string, boolean>>(() => getWidgetVisibility());

  useEffect(() => {
    if (isOpen) {
      setVisibility(getWidgetVisibility());
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const toggleWidget = (widgetId: string) => {
    setVisibility(prev => ({
      ...prev,
      [widgetId]: !prev[widgetId]
    }));
  };

  const handleSave = () => {
    saveWidgetVisibility(visibility);
    onSave(visibility);
    onClose();
  };

  const handleReset = () => {
    const defaultVisibility: Record<string, boolean> = {};
    WIDGET_CONFIGS.forEach(widget => {
      defaultVisibility[widget.id] = widget.defaultVisible;
    });
    setVisibility(defaultVisibility);
  };

  const getCategoryWidgets = (category: WidgetConfig['category']) => {
    return WIDGET_CONFIGS.filter(w => w.category === category);
  };

  const categories: Array<{ key: WidgetConfig['category']; label: string }> = [
    { key: 'stats', label: 'Statistics Cards' },
    { key: 'charts', label: 'Charts' },
    { key: 'widgets', label: 'Widgets' },
    { key: 'cve_charts', label: 'CVE Charts' },
  ];

  return (
    <div 
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 dark:bg-black/70 light:bg-black/30 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div 
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white px-6 py-4">
          <h3 className="text-xl font-semibold text-white dark:text-white light:text-slate-900">Customize Dashboard</h3>
          <button 
            onClick={onClose} 
            className="text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-white dark:hover:text-white light:hover:text-slate-900 text-2xl leading-none w-8 h-8 flex items-center justify-center rounded hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 transition"
            type="button"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {categories.map(({ key: category, label }) => {
            const widgets = getCategoryWidgets(category);
            if (widgets.length === 0) return null;

            return (
              <div key={category} className="space-y-3">
                <h4 className="text-sm font-semibold text-slate-400 dark:text-slate-400 light:text-slate-600 uppercase tracking-wider">
                  {label}
                </h4>
                <div className="space-y-2">
                  {widgets.map((widget) => (
                    <div
                      key={widget.id}
                      className="flex items-center justify-between rounded-lg border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-950/60 dark:bg-slate-950/60 light:bg-slate-50 px-4 py-3 hover:bg-slate-900 dark:hover:bg-slate-900 light:hover:bg-slate-100 transition cursor-pointer"
                      onClick={() => toggleWidget(widget.id)}
                    >
                      <span className="text-sm text-white dark:text-white light:text-slate-900">{widget.title}</span>
                      <div className="flex items-center gap-2">
                        {visibility[widget.id] ? (
                          <Eye className="h-4 w-4 text-green-400 dark:text-green-400 light:text-green-600" />
                        ) : (
                          <EyeOff className="h-4 w-4 text-slate-500 dark:text-slate-500 light:text-slate-400" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <div className="sticky bottom-0 flex items-center justify-between border-t border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900 dark:bg-slate-900 light:bg-white px-6 py-4">
          <button
            onClick={handleReset}
            className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
          >
            Reset to Default
          </button>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="rounded-lg border border-slate-700 dark:border-slate-700 light:border-slate-300 bg-slate-900 dark:bg-slate-900 light:bg-white px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="rounded-lg bg-brand-600 dark:bg-brand-600 light:bg-brand-500 px-4 py-2 text-sm font-medium text-white dark:text-white light:text-slate-900 transition hover:bg-brand-700 dark:hover:bg-brand-700 light:hover:bg-brand-600 flex items-center gap-2"
            >
              <Check className="h-4 w-4" />
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardEditModal;










