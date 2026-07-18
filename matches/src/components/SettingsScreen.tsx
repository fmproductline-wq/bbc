import React, { useState } from "react";
import { UserProfile, PrivacyLevel } from "../types";
import { isAdminUnlocked } from "./AdminGate";

interface Props {
  profile: UserProfile;
  onBack: () => void;
  onUpdatePrivacy: (updated: UserProfile["privacy"]) => void;
  onDeleteAccount: () => void;
  onOpenEditor: () => void;
  onOpenMyQuestions: () => void;
  minCompatibility: number;
  onChangeMinCompat: (v: number) => void;
}

const LEVEL_LABELS: Record<PrivacyLevel, string> = {
  public: "Public",
  private: "Private",
  matches_only: "Matches only",
};

const LEVELS: PrivacyLevel[] = ["public", "matches_only", "private"];

function PrivacyToggle({
  label,
  description,
  value,
  onChange,
}: {
  label: string;
  description: string;
  value: PrivacyLevel;
  onChange: (v: PrivacyLevel) => void;
}) {
  const idx = LEVELS.indexOf(value);
  const colors: Record<PrivacyLevel, string> = {
    public: "#22c55e",
    matches_only: "#FF8C00",
    private: "#ef4444",
  };

  return (
    <div className="flex items-center justify-between py-3">
      <div className="flex-1 min-w-0 pr-4">
        <p className="text-match-text text-sm font-medium">{label}</p>
        <p className="text-match-muted text-xs mt-0.5">{description}</p>
      </div>
      <button
        onClick={() => onChange(LEVELS[(idx + 1) % LEVELS.length])}
        className="px-3 py-1.5 rounded-full text-xs font-semibold flex-shrink-0 transition-all active:scale-95"
        style={{ background: `${colors[value]}22`, color: colors[value], border: `1px solid ${colors[value]}55` }}
      >
        {LEVEL_LABELS[value]}
      </button>
    </div>
  );
}

export const SettingsScreen: React.FC<Props> = ({
  profile,
  onBack,
  onUpdatePrivacy,
  onDeleteAccount,
  onOpenEditor,
  onOpenMyQuestions,
  minCompatibility,
  onChangeMinCompat,
}) => {
  const [privacy, setPrivacy] = useState({ ...profile.privacy });
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [notifications, setNotifications] = useState({
    newMatches: true,
    messages: true,
    qrReveals: true,
    weeklyDigest: false,
  });

  const updateField = (key: keyof UserProfile["privacy"], val: PrivacyLevel) => {
    const updated = { ...privacy, [key]: val };
    setPrivacy(updated);
    onUpdatePrivacy(updated);
  };

  return (
    <div className="flex flex-col h-full bg-match-bg">
      <div className="px-4 pt-12 pb-4 flex items-center gap-3" style={{ borderBottom: "1px solid #2a2a3e" }}>
        <button onClick={onBack} className="text-match-muted text-2xl w-8">‹</button>
        <h2 className="text-match-text text-lg font-bold">Settings</h2>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {/* Privacy */}
        <section>
          <p className="text-match-muted text-xs font-semibold uppercase tracking-wider mb-3">Privacy controls</p>
          <div className="bg-match-card border border-match-border rounded-2xl px-4 divide-y divide-match-border">
            <PrivacyToggle
              label="Bio"
              description="Who can see your bio text"
              value={privacy.bio}
              onChange={(v) => updateField("bio", v)}
            />
            <PrivacyToggle
              label="Questionnaire answers"
              description="Who can see what you answered"
              value={privacy.answers}
              onChange={(v) => updateField("answers", v)}
            />
            <PrivacyToggle
              label="Online status"
              description="Who can see when you're online"
              value={privacy.onlineStatus}
              onChange={(v) => updateField("onlineStatus", v)}
            />
            <PrivacyToggle
              label="Last seen"
              description="Who can see when you were last active"
              value={privacy.lastSeen}
              onChange={(v) => updateField("lastSeen", v)}
            />
          </div>
          <p className="text-match-muted text-xs mt-2 px-1">
            Tap any toggle to cycle: Public → Matches only → Private
          </p>
        </section>

        {/* Notifications */}
        <section>
          <p className="text-match-muted text-xs font-semibold uppercase tracking-wider mb-3">Notifications</p>
          <div className="bg-match-card border border-match-border rounded-2xl px-4 divide-y divide-match-border">
            {(
              [
                ["newMatches", "New compatibility matches", "Alert when bot finds a match"],
                ["messages", "New messages", "Alert on unread messages"],
                ["qrReveals", "QR reveals", "When a match shares their QR"],
                ["weeklyDigest", "Weekly digest", "Summary of your match activity"],
              ] as [keyof typeof notifications, string, string][]
            ).map(([key, label, desc]) => (
              <div key={key} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-match-text text-sm font-medium">{label}</p>
                  <p className="text-match-muted text-xs">{desc}</p>
                </div>
                <button
                  onClick={() => setNotifications((prev) => ({ ...prev, [key]: !prev[key] }))}
                  className="relative w-12 h-6 rounded-full transition-colors flex-shrink-0"
                  style={{ background: notifications[key] ? "#FF4500" : "#2a2a3e" }}
                >
                  <span
                    className="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform"
                    style={{ transform: notifications[key] ? "translateX(26px)" : "translateX(2px)" }}
                  />
                </button>
              </div>
            ))}
          </div>
        </section>

        {/* Matching */}
        <section>
          <p className="text-match-muted text-xs font-semibold uppercase tracking-wider mb-3">Matching preferences</p>
          <div className="bg-match-card border border-match-border rounded-2xl px-4 py-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-match-text text-sm font-medium">Minimum compatibility</p>
                <p className="text-match-muted text-xs">Only notify when score is above this</p>
              </div>
              <span className="text-ember font-bold text-lg">{minCompatibility}%</span>
            </div>
            <input
              type="range"
              min="50"
              max="95"
              value={minCompatibility}
              onChange={(e) => onChangeMinCompat(Number(e.target.value))}
              className="w-full accent-ember"
            />
          </div>
        </section>

        {/* User — My questions */}
        <section>
          <p className="text-match-muted text-xs font-semibold uppercase tracking-wider mb-3">My questions</p>
          <button
            onClick={onOpenMyQuestions}
            className="w-full flex items-center justify-between px-4 py-4 bg-match-card border border-match-border rounded-2xl transition-all active:scale-95"
          >
            <div className="text-left">
              <p className="text-match-text text-sm font-semibold">Add personal questions</p>
              <p className="text-match-muted text-xs mt-0.5">
                Write your own Q&amp;As that matches can read on your profile
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0 ml-3">
              {profile.personalQuestions?.length > 0 && (
                <span
                  className="text-xs font-bold px-2 py-0.5 rounded-full"
                  style={{ background: "#FF450022", color: "#FF6A33" }}
                >
                  {profile.personalQuestions.length}
                </span>
              )}
              <span className="text-match-muted text-lg">›</span>
            </div>
          </button>
        </section>

        {/* Admin — Questionnaire editor */}
        <section>
          <p className="text-match-muted text-xs font-semibold uppercase tracking-wider mb-3">Admin</p>
          <button
            onClick={onOpenEditor}
            className="w-full flex items-center justify-between px-4 py-4 bg-match-card border border-match-border rounded-2xl transition-all active:scale-95"
            style={{ borderColor: "#FF450055" }}
          >
            <div className="text-left">
              <div className="flex items-center gap-2 mb-0.5">
                <p className="text-ember text-sm font-semibold">Questionnaire editor</p>
                <span
                  className="text-xs px-2 py-0.5 rounded-full font-bold"
                  style={{ background: "#FF450022", color: "#FF4500" }}
                >
                  {isAdminUnlocked() ? "Unlocked" : "PIN required"}
                </span>
              </div>
              <p className="text-match-muted text-xs">Add, remove, or reorder the questions every user must answer</p>
            </div>
            <span className="text-match-muted text-lg ml-3">›</span>
          </button>
        </section>

        {/* About */}
        <section>
          <p className="text-match-muted text-xs font-semibold uppercase tracking-wider mb-3">About</p>
          <div className="bg-match-card border border-match-border rounded-2xl px-4 divide-y divide-match-border">
            {[
              ["Version", "1.0.0"],
              ["Your ID", profile.id.slice(0, 8).toUpperCase()],
              ["QR Code", profile.qrCode],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center justify-between py-3">
                <p className="text-match-text text-sm">{k}</p>
                <p className="text-match-muted text-xs font-mono">{v}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Danger zone */}
        <section className="pb-6">
          <p className="text-red-400 text-xs font-semibold uppercase tracking-wider mb-3">Danger zone</p>
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="w-full py-3 rounded-2xl text-sm font-semibold text-red-400 border border-red-900"
            style={{ background: "#1a0808" }}
          >
            Delete my account
          </button>
        </section>
      </div>

      {showDeleteConfirm && (
        <div className="absolute inset-0 bg-black/70 flex items-end z-50">
          <div className="bg-match-surface rounded-t-3xl px-6 pt-6 pb-10 w-full space-y-4">
            <div className="w-10 h-1 bg-match-border rounded-full mx-auto mb-2" />
            <div className="text-center space-y-2">
              <p className="text-2xl">⚠️</p>
              <h3 className="text-match-text font-bold text-lg">Delete account?</h3>
              <p className="text-match-muted text-sm">All your data, conversations, and matches will be permanently removed.</p>
            </div>
            <button
              onClick={onDeleteAccount}
              className="w-full py-4 rounded-2xl font-bold text-white bg-red-600"
            >
              Yes, delete everything
            </button>
            <button onClick={() => setShowDeleteConfirm(false)} className="w-full py-3 text-match-muted text-sm">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
