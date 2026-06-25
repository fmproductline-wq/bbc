import React, { useState, useEffect } from 'react';
import TitleBar from './components/TitleBar';
import Sidebar from './components/Sidebar';
import ChatView from './components/ChatView';
import ModelManager from './components/ModelManager';
import Settings from './components/Settings';
import FirstRunWizard from './components/FirstRunWizard';
import { useStore } from './hooks/useStore';
import { useOllama } from './hooks/useOllama';

export default function App() {
  const [view, setView] = useState('chat');
  const [conversations, setConversations, convsHydrated] = useStore('conversations', []);
  const [activeConvId, setActiveConvId] = useStore('activeConvId', null);
  const [selectedModel, setSelectedModel] = useStore('selectedModel', '');
  const [setupDone, setSetupDone, setupHydrated] = useStore('setupDone', false);
  const { status, models, checkStatus } = useOllama();

  // Initialize first conversation once store is loaded
  useEffect(() => {
    if (!convsHydrated) return;
    if (conversations.length === 0) {
      const id = crypto.randomUUID();
      setConversations([{ id, title: 'New Chat', messages: [], createdAt: Date.now() }]);
      setActiveConvId(id);
    } else if (!activeConvId || !conversations.find(c => c.id === activeConvId)) {
      setActiveConvId(conversations[0].id);
    }
  }, [convsHydrated]);

  // Auto-select first available model
  useEffect(() => {
    if (!selectedModel && models.length > 0) setSelectedModel(models[0].name);
  }, [models]);

  const activeConv = conversations.find(c => c.id === activeConvId) || null;

  function newConversation() {
    const id = crypto.randomUUID();
    setConversations(prev => [{ id, title: 'New Chat', messages: [], createdAt: Date.now() }, ...prev]);
    setActiveConvId(id);
    setView('chat');
  }

  function deleteConversation(id) {
    setConversations(prev => {
      const next = prev.filter(c => c.id !== id);
      if (activeConvId === id) {
        if (next.length === 0) {
          const newId = crypto.randomUUID();
          const fresh = { id: newId, title: 'New Chat', messages: [], createdAt: Date.now() };
          setActiveConvId(newId);
          return [fresh];
        }
        setActiveConvId(next[0].id);
      }
      return next;
    });
  }

  function updateConversation(id, updater) {
    setConversations(prev => prev.map(c => c.id === id ? updater(c) : c));
  }

  // Don't render until we know whether setup has been done (avoid flash)
  if (!setupHydrated) {
    return (
      <div className="flex flex-col h-screen bg-[#212121]">
        <TitleBar minimal />
        <div className="flex-1 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  // Show first-run wizard if this is a fresh install
  if (!setupDone) {
    return (
      <div className="flex flex-col h-screen bg-[#212121]">
        <TitleBar minimal />
        <FirstRunWizard
          onComplete={() => { setSetupDone(true); checkStatus(); }}
          onSkip={() => setSetupDone(true)}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-[#212121] overflow-hidden">
      <TitleBar status={status} onCheckStatus={checkStatus} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          conversations={conversations}
          activeConvId={activeConvId}
          onSelect={id => { setActiveConvId(id); setView('chat'); }}
          onNew={newConversation}
          onDelete={deleteConversation}
          view={view}
          onChangeView={setView}
          selectedModel={selectedModel}
        />
        <main className="flex-1 flex flex-col overflow-hidden bg-[#212121]">
          {view === 'chat' ? (
            <ChatView
              conversation={activeConv}
              model={selectedModel}
              models={models}
              onModelChange={setSelectedModel}
              onUpdateConv={updater => activeConvId && updateConversation(activeConvId, updater)}
              onNewChat={newConversation}
            />
          ) : view === 'models' ? (
            <ModelManager models={models} onRefresh={checkStatus} selectedModel={selectedModel} onSelectModel={setSelectedModel} />
          ) : (
            <Settings selectedModel={selectedModel} onModelChange={setSelectedModel} models={models} />
          )}
        </main>
      </div>
    </div>
  );
}
