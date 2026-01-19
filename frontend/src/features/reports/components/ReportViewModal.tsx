import { X, Download, FileText, Code } from "lucide-react";

interface ReportViewModalProps {
    report: {
        id: string;
        title: string;
        description?: string;
        content?: string;
        format: string;
        created_at: string;
    };
    onClose: () => void;
    onDownload: () => void;
}

const ReportViewModal = ({ report, onClose, onDownload }: ReportViewModalProps) => {
    const getFormatIcon = () => {
        switch (report.format) {
            case "PDF": return <FileText className="h-5 w-5" />;
            case "JSON": return <Code className="h-5 w-5" />;
            default: return <FileText className="h-5 w-5" />;
        }
    };

    const renderContent = () => {
        if (!report.content) {
            return (
                <div className="flex h-64 flex-col items-center justify-center text-slate-400">
                    <p>No content available to preview.</p>
                </div>
            );
        }

        switch (report.format) {
            case "HTML":
                return (
                    <div className="h-full w-full overflow-hidden rounded-lg border border-slate-700 bg-white">
                        <iframe
                            title="Report Content"
                            srcDoc={report.content}
                            className="h-full w-full border-none"
                            sandbox="allow-same-origin"
                        />
                    </div>
                );

            case "JSON":
                let formattedJson = report.content;
                try {
                    const jsonObj = JSON.parse(report.content);
                    formattedJson = JSON.stringify(jsonObj, null, 2);
                } catch (e) {
                    // Keep as is if parsing fails
                }
                return (
                    <div className="h-full w-full overflow-auto rounded-lg border border-slate-700 bg-slate-950 p-4">
                        <pre className="font-mono text-xs text-green-400">
                            <code>{formattedJson}</code>
                        </pre>
                    </div>
                );

            case "PDF":
                // For PDF, we'll try to display it using an object tag with data URI
                // Report content is base64 encoded for PDF
                return (
                    <div className="h-full w-full overflow-hidden rounded-lg border border-slate-700 bg-slate-800">
                        <object
                            data={`data:application/pdf;base64,${report.content}`}
                            type="application/pdf"
                            className="h-full w-full"
                        >
                            <div className="flex h-full flex-col items-center justify-center p-8 text-center text-slate-400">
                                <FileText className="mb-4 h-12 w-12 opacity-50" />
                                <p className="mb-4">This browser does not support inline PDF viewing.</p>
                                <button
                                    onClick={onDownload}
                                    className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
                                >
                                    Download PDF
                                </button>
                            </div>
                        </object>
                    </div>
                );

            default:
                return (
                    <div className="h-full w-full overflow-auto rounded-lg border border-slate-700 bg-slate-950 p-4">
                        <pre className="font-mono text-sm text-slate-300">
                            {report.content}
                        </pre>
                    </div>
                );
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="flex h-[85vh] w-full max-w-5xl flex-col rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between border-b border-slate-800 p-4">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-800 text-brand-400">
                            {getFormatIcon()}
                        </div>
                        <div>
                            <h3 className="font-semibold text-white">{report.title}</h3>
                            <div className="flex items-center gap-2 text-xs text-slate-400">
                                <span>{new Date(report.created_at).toLocaleString()}</span>
                                <span>•</span>
                                <span className="font-medium uppercase">{report.format}</span>
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={onDownload}
                            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white"
                        >
                            <Download className="h-4 w-4" />
                            Download
                        </button>
                        <button
                            onClick={onClose}
                            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
                        >
                            <X className="h-5 w-5" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-hidden p-4">
                    {renderContent()}
                </div>
            </div>
        </div>
    );
};

export default ReportViewModal;
