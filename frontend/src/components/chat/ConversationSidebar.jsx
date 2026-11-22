import React from 'react';
import {
  X,
  Plus,
  MessageSquare,
  Landmark,
} from 'lucide-react';

export const ConversationSidebar = ({
  isOpen,
  onClose,
  conversations = [],
  currentId,
  onNewChat,
  onLoadConversation,
}) => {
  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed lg:relative inset-y-0 left-0 z-50 w-72 bg-navy-900 border-r border-slate-800/60 flex flex-col transition-transform duration-300 ease-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:-translate-x-full'
        }`}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800/60">
          <div className="flex items-center gap-2">
            <Landmark className="w-5 h-5 text-teal-400" />
            <span className="text-sm font-semibold text-white">NitiSetu</span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <button
            onClick={onNewChat}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg bg-slate-800/40 hover:bg-slate-700/40 border border-slate-700/30 text-sm text-slate-200 hover:text-white transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>New conversation</span>
          </button>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto px-3 pb-3">
          {conversations.length === 0 ? (
            <div className="text-center py-10">
              <MessageSquare className="w-8 h-8 text-slate-700 mx-auto mb-2" />
              <p className="text-xs text-slate-600">No previous conversations</p>
            </div>
          ) : (
            <div className="space-y-1">
              <p className="text-[10px] uppercase font-semibold text-slate-600 tracking-wider px-2 py-1.5">
                Recent
              </p>
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => onLoadConversation(conv)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors truncate ${
                    conv.id === currentId
                      ? 'bg-slate-800/60 text-white'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/30'
                  }`}
                >
                  <span className="block truncate">{conv.title}</span>
                  <span className="text-[10px] text-slate-600 mt-0.5 block">
                    {new Date(conv.updatedAt).toLocaleDateString()}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-slate-800/60">
          <p className="text-[10px] text-slate-600 text-center">
            NitiSetu — Bridging Citizens with Knowledge
          </p>
        </div>
      </div>
    </>
  );
};
