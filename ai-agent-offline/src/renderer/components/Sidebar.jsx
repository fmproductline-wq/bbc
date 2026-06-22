import React, { useState } from 'react';

export default function Sidebar({ conversations, activeConvId, onSelect, onNew, onDelete, view, onChangeView, selectedModel }) {
  const [hoverId, setHoverId] = useState(null);

  const today = [];
  const yesterday = [];
  const older = [];
  const now = Date.now();

  conversations.forEach(c => {
    const age = now - c.createdAt;
    if (age < 86400000) today.push(c);
    else if (age < 172800000) yesterday.push(c);
    else older.push(c);
  });

  function ConvItem({ conv }) {
    const isActive = conv.id === activeConvId;
    const isHovered = hoverId === conv.id;
    return (
      <div
        className={`group relative flex items-center gap-2 px-3 py-2 rounded-xl cursor-pointer transition-all mb-0.5 ${
          isActive ? 'bg-white/10 text-white' : 'text-[#999] hover:bg-white/6 hover:text-[#ddd]'
        }`}
        onClick={() => onSelect(conv.id)}
        onMouseEnter={() => setHoverId(conv.id)}
        onMouseLeave={() => setHoverId(null)}
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" className="flex-shrink-0 opacity-50">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        <span className="text-xs truncate flex-1">{conv.title}</span>
        {(isActive || isHovered) && (
          <button
            onClick={e => { e.stopPropagation(); onDelete(conv.id); }}
            className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-[#555] hover:text-red-400 transition-all flex-shrink-0"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <polyline points="3,6 5,6 21,6"/><path d="M19,6l-1,14H6L5,6"/>
            </svg>
          </button>
        )}
      </div>
    );
  }

  function Group({ label, items }) {
    if (!items.length) return null;
    return (
      <div className="mb-3">
        <p className="text-[10px] font-semibold text-[#444] uppercase tracking-widest px-3 mb-1">{label}</p>
        {items.map(c => <ConvItem key={c.id} conv={c} />)}
      </div>
    );
  }

  return (
    <aside className="w-64 flex flex-col bg-[#171717] border-r border-white/5 flex-shrink-0">
      {/* New chat */}
      <div className="p-3">
        <button
          onClick={onNew}
          className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/8 text-[#aaa] hover:text-white transition-all text-sm font-medium group"
        >
          <span className="flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="opacity-70">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            BestBrand AI
          </span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" className="opacity-0 group-hover:opacity-100 transition-opacity">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
      </div>

      {/* Conversations */}
      <div className="flex-1 overflow-y-auto px-2 py-1">
        <Group label="Today" items={today} />
        <Group label="Yesterday" items={yesterday} />
        <Group label="Older" items={older} />
        {conversations.length === 0 && (
          <p className="text-xs text-[#444] text-center py-8">No conversations yet</p>
        )}
      </div>

      {/* Bottom nav */}
      <div className="p-3 border-t border-white/5 space-y-0.5">
        {[
          { id: 'models', label: 'Models', icon: ModelsIcon },
          { id: 'settings', label: 'Settings', icon: SettingsIcon },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onChangeView(view === id ? 'chat' : id)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all ${
              view === id
                ? 'bg-white/10 text-white'
                : 'text-[#666] hover:bg-white/6 hover:text-[#bbb]'
            }`}
          >
            <Icon />
            {label}
          </button>
        ))}

        {selectedModel && (
          <div className="px-3 pt-2 pb-1">
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />
              <span className="text-[10px] text-[#555] truncate">{selectedModel}</span>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

function ModelsIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>
  );
}
