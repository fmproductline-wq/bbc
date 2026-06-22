import React from "react";
import { Notification } from "../types";

interface Props {
  notifications: Notification[];
  onBack: () => void;
  onMarkAllRead: () => void;
  onTapNotification: (notif: Notification) => void;
}

const ICONS: Record<Notification["type"], string> = {
  new_match: "🔥",
  message: "💬",
  qr_reveal: "🔓",
  compatibility_update: "⚡",
};

function timeAgo(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
}

export const NotificationsScreen: React.FC<Props> = ({
  notifications,
  onBack,
  onMarkAllRead,
  onTapNotification,
}) => {
  const sorted = [...notifications].sort((a, b) => b.timestamp - a.timestamp);

  return (
    <div className="flex flex-col h-full bg-match-bg">
      <div className="px-4 pt-12 pb-4 flex items-center justify-between" style={{ borderBottom: "1px solid #2a2a3e" }}>
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="text-match-muted text-2xl w-8">‹</button>
          <h2 className="text-match-text text-lg font-bold">Notifications</h2>
        </div>
        {notifications.some((n) => !n.read) && (
          <button onClick={onMarkAllRead} className="text-ember text-sm font-semibold">
            Mark all read
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {sorted.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 gap-3 text-center px-8">
            <span className="text-5xl">🔔</span>
            <p className="text-match-text font-semibold">Nothing yet</p>
            <p className="text-match-muted text-sm">When our bot finds a spark, you'll see it here.</p>
          </div>
        ) : (
          sorted.map((notif) => (
            <button
              key={notif.id}
              onClick={() => onTapNotification(notif)}
              className="w-full flex items-start gap-3 px-4 py-4 border-b border-match-border transition-colors active:bg-match-card"
              style={{ background: notif.read ? "transparent" : "#FF450008" }}
            >
              <div
                className="w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0 text-xl"
                style={{ background: notif.read ? "#1a1a26" : "#FF450022" }}
              >
                {ICONS[notif.type]}
              </div>
              <div className="flex-1 text-left min-w-0">
                <div className="flex items-center justify-between">
                  <p className={`text-sm font-semibold ${notif.read ? "text-match-muted" : "text-match-text"}`}>
                    {notif.title}
                  </p>
                  {!notif.read && (
                    <div className="w-2 h-2 rounded-full bg-ember flex-shrink-0 ml-2" />
                  )}
                </div>
                <p className="text-match-muted text-xs mt-0.5 leading-relaxed">{notif.body}</p>
                <p className="text-match-muted text-xs mt-1">{timeAgo(notif.timestamp)}</p>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
};
