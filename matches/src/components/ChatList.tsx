import React from "react";
import { Conversation, UserProfile, Notification } from "../types";
import { QRAvatar, BlurredQRAvatar } from "./QRAvatar";
import { getCompatibilityLabel } from "../hooks/useCompatibility";
import { Logo } from "./Logo";

interface Props {
  conversations: Conversation[];
  profiles: Map<string, UserProfile>;
  currentUserId: string;
  notifications: Notification[];
  onOpenChat: (convId: string) => void;
  onOpenProfile: () => void;
  onOpenNotifications: () => void;
  onOpenSettings: () => void;
}

function timeAgo(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 60000) return "now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
  return `${Math.floor(diff / 86400000)}d`;
}

export const ChatList: React.FC<Props> = ({
  conversations,
  profiles,
  currentUserId,
  notifications,
  onOpenChat,
  onOpenProfile,
  onOpenNotifications,
  onOpenSettings,
}) => {
  const unreadNotifs = notifications.filter((n) => !n.read).length;
  const sorted = [...conversations].sort((a, b) => b.lastMessageAt - a.lastMessageAt);

  return (
    <div className="flex flex-col h-full bg-match-bg">
      {/* Header — WhatsApp-style */}
      <div
        className="px-4 pt-12 pb-3 flex items-center justify-between"
        style={{ borderBottom: "1px solid #2a2a3e" }}
      >
        <div className="flex items-center gap-2">
          <Logo size={28} />
          <h1
            className="font-bold text-lg tracking-wider"
            style={{
              background: "linear-gradient(135deg, #FF4500, #FF8C00)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            Matches
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenNotifications}
            className="relative w-9 h-9 flex items-center justify-center rounded-full text-match-muted hover:text-match-text"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            {unreadNotifs > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-ember text-white text-xs flex items-center justify-center font-bold" style={{ fontSize: 9 }}>
                {unreadNotifs > 9 ? "9+" : unreadNotifs}
              </span>
            )}
          </button>
          <button
            onClick={onOpenProfile}
            className="w-9 h-9 flex items-center justify-center rounded-full text-match-muted hover:text-match-text"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="8" r="4" />
              <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
            </svg>
          </button>
          <button
            onClick={onOpenSettings}
            className="w-9 h-9 flex items-center justify-center rounded-full text-match-muted hover:text-match-text"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Search bar */}
      <div className="px-4 py-2">
        <div className="flex items-center gap-2 bg-match-card rounded-xl px-3 py-2.5">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8888aa" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <span className="text-match-muted text-sm">Search chats…</span>
        </div>
      </div>

      {/* Conversations list */}
      <div className="flex-1 overflow-y-auto">
        {sorted.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 gap-4 px-8 text-center">
            <div className="text-5xl">🔥</div>
            <p className="text-match-text font-semibold">No matches yet</p>
            <p className="text-match-muted text-sm">
              Our bot is scanning for compatible profiles. You'll be notified when a spark is found.
            </p>
          </div>
        ) : (
          sorted.map((conv) => {
            const otherId = conv.participantIds.find((id) => id !== currentUserId) || "";
            const other = profiles.get(otherId);
            if (!other) return null;
            const lastMsg = conv.messages[conv.messages.length - 1];
            const unread = conv.messages.filter((m) => !m.read && m.senderId !== currentUserId).length;
            const { label, color } = getCompatibilityLabel(conv.compatibilityScore);
            const revealed = conv.qrRevealed[otherId];

            return (
              <button
                key={conv.id}
                onClick={() => onOpenChat(conv.id)}
                className="w-full flex items-center gap-3 px-4 py-3 active:bg-match-card transition-colors border-b border-match-border"
              >
                {revealed ? (
                  <QRAvatar value={other.qrCode} size={54} score={conv.compatibilityScore} />
                ) : (
                  <BlurredQRAvatar size={54} />
                )}

                <div className="flex-1 min-w-0 text-left">
                  <div className="flex items-center justify-between">
                    <span className="text-match-text font-semibold text-sm truncate">
                      {revealed ? other.displayName : `Match #${otherId.slice(0, 4).toUpperCase()}`}
                    </span>
                    <span className="text-match-muted text-xs flex-shrink-0 ml-2">
                      {lastMsg ? timeAgo(lastMsg.timestamp) : timeAgo(conv.createdAt)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-0.5">
                    <span className="text-match-muted text-xs truncate">
                      {lastMsg
                        ? lastMsg.type === "qr_reveal"
                          ? "🔓 QR revealed"
                          : lastMsg.type === "compatibility_invite"
                          ? "🔥 Compatibility match found"
                          : lastMsg.content
                        : "Say hello 👋"}
                    </span>
                    <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                      <span
                        className="text-xs font-bold px-1.5 py-0.5 rounded-full"
                        style={{ color, background: `${color}22`, fontSize: 10 }}
                      >
                        {conv.compatibilityScore}%
                      </span>
                      {unread > 0 && (
                        <span className="w-5 h-5 rounded-full bg-ember text-white text-xs flex items-center justify-center font-bold">
                          {unread}
                        </span>
                      )}
                    </div>
                  </div>
                  <span className="text-xs mt-0.5 block" style={{ color, opacity: 0.8 }}>
                    {label}
                  </span>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};
