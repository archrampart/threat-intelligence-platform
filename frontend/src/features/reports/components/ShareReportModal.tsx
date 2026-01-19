import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Search, Check, Users, Shield } from "lucide-react";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

interface User {
    id: string;
    email: string;
    full_name: string;
    role: string;
    is_active: boolean;
}

interface ShareReportModalProps {
    reportId: string;
    reportTitle: string;
    currentSharedIds: string[]; // IDs of users currently shared with
    onClose: () => void;
}

const ShareReportModal = ({ reportId, reportTitle, currentSharedIds, onClose }: ShareReportModalProps) => {
    const { user: currentUser } = useAuth();
    const [search, setSearch] = useState("");
    const [selectedUserIds, setSelectedUserIds] = useState<string[]>(currentSharedIds || []);
    const queryClient = useQueryClient();

    // Fetch users list
    const { data: usersData, isLoading } = useQuery({
        queryKey: ["users-for-share", search],
        queryFn: async () => {
            const response = await apiClient.get<{ items: User[] }>("/users/", {
                params: { page: 1, page_size: 100 } // Fetch enough users
            });
            return response.data;
        }
    });

    const shareMutation = useMutation({
        mutationFn: async (userIds: string[]) => {
            await apiClient.put(`/reports/${reportId}/share`, {
                user_ids: userIds
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["reports"] });
            onClose();
        },
        onError: (error: any) => {
            alert(`Failed to share report: ${error?.response?.data?.detail || error.message}`);
        }
    });

    const toggleUser = (userId: string) => {
        if (selectedUserIds.includes(userId)) {
            setSelectedUserIds(selectedUserIds.filter(id => id !== userId));
        } else {
            setSelectedUserIds([...selectedUserIds, userId]);
        }
    };

    const filteredUsers = usersData?.items
        .filter(u => u.id !== currentUser?.id) // Exclude current user
        .filter(u =>
            (u.full_name || "").toLowerCase().includes(search.toLowerCase()) ||
            (u.email || "").toLowerCase().includes(search.toLowerCase())
        ) || [];

    const handleSave = () => {
        shareMutation.mutate(selectedUserIds);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-800 p-4">
                    <div>
                        <h3 className="text-lg font-semibold text-white">Share Report</h3>
                        <p className="text-xs text-slate-400 truncate max-w-[250px]">{reportTitle}</p>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-white">
                        <X className="h-5 w-5" />
                    </button>
                </div>

                <div className="p-4 space-y-4">
                    <div className="relative">
                        <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Search users..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full rounded-lg border border-slate-700 bg-slate-950 py-2 pl-9 pr-4 text-sm text-white placeholder:text-slate-500 focus:border-brand-500 focus:outline-none"
                        />
                    </div>

                    <div className="h-60 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/50 p-2">
                        {isLoading ? (
                            <div className="flex h-full items-center justify-center text-slate-500">Loading...</div>
                        ) : filteredUsers.length > 0 ? (
                            <div className="space-y-1">
                                {filteredUsers.map((user) => (
                                    <button
                                        key={user.id}
                                        onClick={() => toggleUser(user.id)}
                                        className={`flex w-full items-center justify-between rounded-lg p-2 transition ${selectedUserIds.includes(user.id)
                                            ? "bg-brand-900/20 border border-brand-800/50"
                                            : "hover:bg-slate-900 border border-transparent"
                                            }`}
                                    >
                                        <div className="flex items-center gap-3 text-left">
                                            <div className={`flex h-8 w-8 items-center justify-center rounded-full ${selectedUserIds.includes(user.id) ? "bg-brand-900 text-brand-300" : "bg-slate-800 text-slate-400"
                                                }`}>
                                                <Users className="h-4 w-4" />
                                            </div>
                                            <div>
                                                <div className={`text-sm font-medium ${selectedUserIds.includes(user.id) ? "text-brand-200" : "text-slate-200"}`}>
                                                    {user.full_name}
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-slate-500">
                                                    <span>{user.email}</span>
                                                    <span className="flex items-center gap-1 rounded bg-slate-900 px-1.5 py-0.5 text-[10px] uppercase">
                                                        <Shield className="h-2 w-2" />
                                                        {user.role}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                        {selectedUserIds.includes(user.id) && (
                                            <Check className="h-4 w-4 text-brand-400" />
                                        )}
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <div className="flex h-full items-center justify-center text-slate-500">No users found</div>
                        )}
                    </div>

                    <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>{selectedUserIds.length} user(s) selected</span>
                        {selectedUserIds.length > 0 && (
                            <button onClick={() => setSelectedUserIds([])} className="text-brand-400 hover:underline">
                                Clear all
                            </button>
                        )}
                    </div>
                </div>

                <div className="flex justify-end gap-3 border-t border-slate-800 p-4">
                    <button
                        onClick={onClose}
                        className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={shareMutation.isPending}
                        className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
                    >
                        {shareMutation.isPending ? "Saving..." : "Save Changes"}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ShareReportModal;
