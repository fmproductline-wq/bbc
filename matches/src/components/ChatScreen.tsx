import React, { useState, useRef, useEffect } from "react";
import { Conversation, UserProfile, Message } from "../types";
import { QRAvatar, BlurredQRAvatar } from "./QRAvatar";
import { getCompatibilityLabel } from "../hooks/useCompatibility";
import { v4 as uuidv4 } from "uuid";

interface Props {
  conversation: Conversation;
  currentUser: UserProfile;
  otherUser: UserProfile;
  onBack: () => void;
  onSendMessage: (convId: string, content: string, type?: Message["type"]) => void;
  onRevealQR: (convId: string) => void;
  onMarkRead: (convId: string) => void;
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export const ChatScreen: React.FC<Props> = ({
  conversation,
  currentUser,
  otherUser,
  onBack,
  onSendMessage,
  onRevealQR,
  onMarkRead,
}) => {
  const [input, setInput] = useState("");
  const [showRevealPrompt, setShowRevealPrompt] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { label, color } = getCompatibilityLabel(conversation.compatibilityScore);
  const myRevealed = conversation.qrRevealed[currentUser.id];
  const theirRevealed = conversation.qrRevealed[otherUser.id];
  const bothRevealed = myRevealed && theirRevealed;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    onMarkRead(conversation.id);
  }, [conversation.id, conversation.messages.length]);

  const send = () => {
    if (!input.trim()) return;
    onSendMessage(conversation.id, input.trim());
    setInput("");
  };

  const handleReveal = () => {
    onRevealQR(conversation.id);
    onSendMessage(conversation.id, `${currentUser.displayName} has shared their QR identity.`, "qr_reveal");
    setShowRevealPrompt(false);
  };

  return (
    <div className="flex flex-col h-full bg-match-bg">
      {/* Header */}
      <div
        className="flex items-center gap-3 px-4 pt-12 pb-3"
        style={{ borderBottom: "1px solid #2a2a3e", background: "#12121a" }}
      >
        <button onClick={onBack} className="text-match-muted text-2xl w-8">‹</button>

        {bothRevealed ? (
          <QRAvatar value={otherUser.qrCode} size={42} score={conversation.compatibilityScore} />
        ) : (
          <BlurredQRAvatar size={42} />
        )}

        <div className="flex-1 min-w-0">
          <p className="text-match-text font-semibold text-sm truncate">
            {bothRevealed ? otherUser.displayName : `Match #${otherUser.id.slice(0, 4).toUpperCase()}`}
          </p>
          <p className="text-xs" style={{ color }}>
            {label} · {conversation.compatibilityScore}% compatible
          </p>
        </div>

        {!myRevealed && (
          <button
            onClick={() => setShowRevealPrompt(true)}
            className="px-3 py-1.5 rounded-full text-xs font-semibold text-white flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #FF4500, #FF8C00)" }}
          >
            Share QR
          </button>
        )}
        {myRevealed && !theirRevealed && (
          <span className="px-3 py-1.5 rounded-full text-xs text-match-muted border border-match-border flex-shrink-0">
            Waiting…
          </span>
        )}
      </div>

      {/* Compatibility card */}
      <div
        className="mx-4 mt-3 rounded-2xl p-3 flex items-center gap-3"
        style={{ background: `${color}15`, border: `1px solid ${color}44` }}
      >
        <span className="text-2xl">🔥</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold" style={{ color }}>
            {label} — {conversation.compatibilityScore}% match
          </p>
          <p className="text-match-muted text-xs truncate">
            {conversation.messages.find((m) => m.type === "compatibility_invite")?.content || "Compatibility found by Matches bot"}
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {conversation.messages.map((msg) => {
          const isMe = msg.senderId === currentUser.id;
          const isSystem = msg.type === "system" || msg.type === "compatibility_invite" || msg.type === "qr_reveal";

          if (isSystem) {
            return (
              <div key={msg.id} className="flex justify-center">
                <div
                  className="px-4 py-2 rounded-full text-xs text-center max-w-xs"
                  style={{ background: "#1a1a26", color: "#8888aa", border: "1px solid #2a2a3e" }}
                >
                  {msg.type === "compatibility_invite" ? "🔥 " : msg.type === "qr_reveal" ? "🔓 " : ""}
                  {msg.content}
                </div>
              </div>
            );
          }

          return (
            <div key={msg.id} className={`flex ${isMe ? "justify-end" : "justify-start"} items-end gap-2`}>
              {!isMe && (
                bothRevealed
                  ? <QRAvatar value={otherUser.qrCode} size={28} />
                  : <BlurredQRAvatar size={28} />
              )}
              <div className="max-w-[72%]">
                <div
                  className="px-4 py-2.5 rounded-2xl text-sm leading-relaxed"
                  style={{
                    background: isMe
                      ? "linear-gradient(135deg, #FF4500, #FF6A33)"
                      : "#1a1a26",
                    color: isMe ? "#fff" : "#e8e8f0",
                    borderRadius: isMe ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                    border: isMe ? "none" : "1px solid #2a2a3e",
                  }}
                >
                  {msg.content}
                </div>
                <p className={`text-xs text-match-muted mt-1 ${isMe ? "text-right" : "text-left"}`}>
                  {formatTime(msg.timestamp)}
                  {isMe && (
                    <span className="ml-1">{msg.read ? " ✓✓" : " ✓"}</span>
                  )}
                </p>
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-4 pb-8 pt-2" style={{ borderTop: "1px solid #2a2a3e" }}>
        <div className="flex items-center gap-2">
          <div className="flex-1 flex items-center bg-match-card border border-match-border rounded-full px-4 py-2.5 gap-2">
            <input
              className="flex-1 bg-transparent text-match-text text-sm outline-none"
              placeholder="Message…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
            />
            {!myRevealed && (
              <button onClick={() => setShowRevealPrompt(true)} className="text-ember text-lg flex-shrink-0" title="Share QR">
                🔓
              </button>
            )}
          </div>
          <button
            onClick={send}
            disabled={!input.trim()}
            className="w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0 transition-all active:scale-90 disabled:opacity-40"
            style={{ background: "linear-gradient(135deg, #FF4500, #FF8C00)" }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
              <path d="M22 2L11 13M22 2L15 22 11 13 2 9l20-7z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
            </svg>
          </button>
        </div>
      </div>

      {/* Reveal QR modal */}
      {showRevealPrompt && (
        <div className="absolute inset-0 bg-black/70 flex items-end justify-center z-50">
          <div className="bg-match-surface rounded-t-3xl px-6 pt-6 pb-10 w-full max-w-lg space-y-4">
            <div className="w-10 h-1 bg-match-border rounded-full mx-auto mb-2" />
            <div className="flex flex-col items-center gap-3 text-center">
              <div className="text-5xl">🔓</div>
              <h3 className="text-match-text text-lg font-bold">Share your QR identity?</h3>
              <p className="text-match-muted text-sm">
                Once shared, your match can see your nickname and QR code. This can't be undone for this conversation.
              </p>
            </div>
            <button
              onClick={handleReveal}
              className="w-full py-4 rounded-2xl font-bold text-white"
              style={{ background: "linear-gradient(135deg, #FF4500, #FF8C00)" }}
            >
              Yes, share my QR
            </button>
            <button onClick={() => setShowRevealPrompt(false)} className="w-full py-3 text-match-muted text-sm">
              Not yet
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
