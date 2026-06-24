import React, { useState } from "react";
import { Logo } from "./Logo";
import { v4 as uuidv4 } from "uuid";
import { UserProfile } from "../types";

interface Props {
  onComplete: (profile: UserProfile) => void;
}

export const Onboarding: React.FC<Props> = ({ onComplete }) => {
  const [step, setStep] = useState<"welcome" | "create">("welcome");
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [error, setError] = useState("");

  const handleCreate = () => {
    if (!displayName.trim() || displayName.trim().length < 2) {
      setError("Enter a nickname (at least 2 characters)");
      return;
    }
    const id = uuidv4();
    const profile: UserProfile = {
      id,
      qrCode: `MATCHES:${id.split("-")[0].toUpperCase()}`,
      displayName: displayName.trim(),
      bio: bio.trim(),
      answers: [],
      personalQuestions: [],
      privacy: {
        bio: "public",
        answers: "matches_only",
        onlineStatus: "public",
        lastSeen: "matches_only",
      },
      createdAt: Date.now(),
      isOnline: true,
      lastSeen: Date.now(),
    };
    onComplete(profile);
  };

  if (step === "welcome") {
    return (
      <div
        className="flex flex-col h-full"
        style={{ background: "radial-gradient(ellipse at top, #1a0800 0%, #0a0a0f 60%)" }}
      >
        <div className="flex-1 flex flex-col items-center justify-center px-8 text-center gap-6">
          <Logo size={100} showText />
          <div className="space-y-3 mt-4">
            <h1 className="text-2xl font-bold text-match-text">Privacy-first connections</h1>
            <p className="text-match-muted text-sm leading-relaxed">
              No photos. No algorithms deciding for you. Just honest answers and genuine compatibility — revealed only when
              you're ready.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 w-full mt-4">
            {[
              ["🔥", "QR code identity", "Your face is your choice"],
              ["💬", "Faceless first", "Talk before you reveal"],
              ["🎯", "Compatibility matched", "By what truly matters"],
            ].map(([icon, title, desc]) => (
              <div key={title} className="flex items-center gap-3 bg-match-card border border-match-border rounded-2xl p-3">
                <span className="text-2xl">{icon}</span>
                <div className="text-left">
                  <p className="text-match-text text-sm font-semibold">{title}</p>
                  <p className="text-match-muted text-xs">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="px-6 pb-10 space-y-3">
          <button
            onClick={() => setStep("create")}
            className="w-full py-4 rounded-2xl font-bold text-white text-base transition-all active:scale-95"
            style={{ background: "linear-gradient(135deg, #FF4500, #FF8C00)" }}
          >
            Create my profile
          </button>
          <p className="text-center text-match-muted text-xs">
            Your real identity is never required or stored.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-match-bg">
      <div className="flex items-center gap-3 px-4 pt-12 pb-6">
        <button onClick={() => setStep("welcome")} className="text-match-muted text-2xl">‹</button>
        <h2 className="text-match-text text-lg font-bold">Create your profile</h2>
      </div>

      <div className="flex-1 overflow-y-auto px-6 space-y-6">
        <div className="flex flex-col items-center gap-3">
          <div
            className="w-20 h-20 rounded-2xl border-2 border-dashed border-ember flex items-center justify-center"
            style={{ background: "#1a0800" }}
          >
            <span className="text-3xl">🔥</span>
          </div>
          <p className="text-match-muted text-xs text-center">
            Your QR code will be generated automatically.<br />No photo needed.
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-match-muted text-xs font-semibold uppercase tracking-wider">Nickname *</label>
          <input
            className="w-full bg-match-card border border-match-border rounded-xl px-4 py-3 text-match-text text-base outline-none focus:border-ember transition-colors"
            placeholder="What should people call you?"
            value={displayName}
            onChange={(e) => { setDisplayName(e.target.value); setError(""); }}
            maxLength={30}
          />
          {error && <p className="text-red-400 text-xs">{error}</p>}
        </div>

        <div className="space-y-2">
          <label className="text-match-muted text-xs font-semibold uppercase tracking-wider">Bio (optional)</label>
          <textarea
            className="w-full bg-match-card border border-match-border rounded-xl px-4 py-3 text-match-text text-sm outline-none focus:border-ember transition-colors resize-none"
            placeholder="A little about yourself — no personal details needed..."
            rows={3}
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            maxLength={200}
          />
          <p className="text-match-muted text-xs text-right">{bio.length}/200</p>
        </div>

        <div className="bg-match-card border border-match-border rounded-xl p-4 space-y-2">
          <p className="text-ember text-xs font-semibold uppercase tracking-wider">Next step</p>
          <p className="text-match-text text-sm">
            After creating your profile, you'll complete a short questionnaire. This is what our compatibility engine uses to find your matches.
          </p>
        </div>
      </div>

      <div className="px-6 pb-10 pt-4">
        <button
          onClick={handleCreate}
          className="w-full py-4 rounded-2xl font-bold text-white text-base transition-all active:scale-95"
          style={{ background: "linear-gradient(135deg, #FF4500, #FF8C00)" }}
        >
          Continue to questionnaire →
        </button>
      </div>
    </div>
  );
};
