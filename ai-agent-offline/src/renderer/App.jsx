import React, { useState, useEffect, useRef } from 'react';
import TitleBar from './components/TitleBar';
import Sidebar from './components/Sidebar';
import ChatView from './components/ChatView';
import ModelManager from './components/ModelManager';
import Settings from './components/Settings';
import SetupScreen from './components/SetupScreen';
import { useStore } from './hooks/useStore';
import { useOllama } from './hooks/useOllama';

export default function App() {
  const [view, setView] = useState('chat'); // 'chat' | 'models' | 'settings'
  const [conversations, setConversations] = useStore('conversations', []);
  const [activeConvId, setActiveConvId] = useStore('activeConvId', null);
  const [selectedModel, setSelectedModel] = useStore('selectedModel', '');
  const { status, models, checkStatus } = useOllama();

  // Create initial conversation if none exist
  useEffect(() => {
    if (conversations.length === 0) {
      const id = crypto.randomUUID();
      const first = { id, title: 'New Chat', messages: [], createdAt: Date.now() };
      setConversations([first]);
      setActiveConvId(id);
    } else if (!activeConvId) {
      setActiveConvId(conversations[0].id);
    }
  }, []);

  // Auto-select first available model
  useEffect(() => {
    if (!selectedModel && models.length > 0) {
      setSelectedModel(models[0].name);
    }
  }, [models, selectedModel]);

  const activeConv = conversations.find(c => c.id === activeConvId) || null;

  function newConversation() {
    const id = crypto.randomUUID();
    const conv = { id, title: 'New Chat', messages: [], createdAt: Date.now() };
    setConversations(prev => [conv, ...prev]);
    setActiveConvId(id);
    setView('chat');
  }

  function deleteConversation(id) {
    setConversations(prev => {
      const next = prev.filter(c => c.id !== id);
      if (activeConvId === id) {
        setActiveConvId(next[0]?.id || null);
        if (next.length === 0) {
          const newId = crypto.randomUUID();
          const fresh = { id: newId, title: 'New Chat', messages: [], createdAt: Date.now() };
          setConversations([fresh]);
          setActiveConvId(newId);
          return [fresh];
        }
      }
      return next;
    });
  }

  function updateConversation(id, updater) {
    setConversations(prev => prev.map(c => c.id === id ? updater(c) : c));
  }

  const showSetup = status === 'offline' && models.length === 0;

  return (
    <div className="flex flex-col h-screen bg-surface-900 select-none">
      <TitleBar status={status} onCheckStatus={checkStatus} />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          conversations={conversations}
          activeConvId={activeConvId}
          onSelect={(id) => { setActiveConvId(id); setView('chat'); }}
          onNew={newConversation}
          onDelete={deleteConversation}
          view={view}
          onChangeView={setView}
        />

        <main className="flex-1 flex flex-col overflow-hidden">
          {showSetup ? (
            <SetupScreen onRetry={checkStatus} />
          ) : view === 'chat' ? (
            <ChatView
              conversation={activeConv}
              model={selectedModel}
              models={models}
              onModelChange={setSelectedModel}
              onUpdateConv={(updater) => activeConvId && updateConversation(activeConvId, updater)}
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
