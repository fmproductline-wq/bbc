import React from "react";
import { UserProfile } from "../types";
import { QRAvatar } from "./QRAvatar";
import { loadQuestions } from "./QuestionnaireEditor";
import { getCompatibilityLabel } from "../hooks/useCompatibility";

const QUESTIONS = loadQuestions();

interface Props {
  profile: UserProfile;
  onOpenMyQuestions: () => void;
  onBack: () => void;
  onEditQuestionnaire: () => void;
}

export const ProfileScreen: React.FC<Props> = ({ profile, onBack, onEditQuestionnaire, onOpenMyQuestions }) => {
  const answered = profile.answers.filter((a) => a.value !== "").length;
  const completionPct = Math.round((answered / QUESTIONS.length) * 100);

  return (
    <div className="flex flex-col h-full bg-match-bg">
      {/* Header */}
      <div className="px-4 pt-12 pb-4 flex items-center gap-3" style={{ borderBottom: "1px solid #2a2a3e" }}>
        <button onClick={onBack} className="text-match-muted text-2xl w-8">‹</button>
        <h2 className="text-match-text text-lg font-bold flex-1">My Profile</h2>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {/* QR card */}
        <div
          className="rounded-3xl p-6 flex flex-col items-center gap-4"
          style={{ background: "linear-gradient(135deg, #1a0800, #12121a)", border: "1px solid #2a2a3e" }}
        >
          <QRAvatar value={profile.qrCode} size={120} />
          <div className="text-center">
            <h2 className="text-match-text text-xl font-bold">{profile.displayName}</h2>
            <p className="text-match-muted text-xs mt-1 font-mono">{profile.qrCode}</p>
          </div>
          {profile.bio && (
            <p className="text-match-muted text-sm text-center leading-relaxed">{profile.bio}</p>
          )}
        </div>

        {/* Profile completion */}
        <div className="bg-match-card border border-match-border rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-match-text text-sm font-semibold">Profile completeness</p>
            <p className="text-ember font-bold">{completionPct}%</p>
          </div>
          <div className="h-2 bg-match-border rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${completionPct}%`, background: "linear-gradient(90deg, #FF4500, #FF8C00)" }}
            />
          </div>
          <p className="text-match-muted text-xs">
            More answers = better matches. {answered}/{QUESTIONS.length} questions answered.
          </p>
          <button
            onClick={onEditQuestionnaire}
            className="w-full py-3 rounded-xl text-sm font-semibold text-white transition-all active:scale-95"
            style={{ background: "linear-gradient(135deg, #FF4500, #FF8C00)" }}
          >
            {completionPct < 100 ? "Complete questionnaire 🔥" : "Update answers"}
          </button>
        </div>

        {/* Answers preview */}
        {profile.answers.length > 0 && (
          <div className="space-y-3">
            <p className="text-match-muted text-xs font-semibold uppercase tracking-wider">Your answers</p>
            {profile.answers.slice(0, 5).map((ans) => {
              const q = QUESTIONS.find((q) => q.id === ans.questionId);
              if (!q || !ans.value) return null;
              return (
                <div key={ans.questionId} className="bg-match-card border border-match-border rounded-xl px-4 py-3">
                  <p className="text-match-muted text-xs mb-1">{q.text}</p>
                  <p className="text-match-text text-sm font-medium">
                    {Array.isArray(ans.value) ? ans.value.join(", ") : String(ans.value)}
                  </p>
                </div>
              );
            })}
            {profile.answers.length > 5 && (
              <button onClick={onEditQuestionnaire} className="text-ember text-sm">
                View all {profile.answers.length} answers →
              </button>
            )}
          </div>
        )}

        {/* Personal questions */}
        <div className="space-y-3 pb-6">
          <div className="flex items-center justify-between">
            <p className="text-match-muted text-xs font-semibold uppercase tracking-wider">My questions</p>
            <button onClick={onOpenMyQuestions} className="text-ember text-xs font-semibold">
              {(profile.personalQuestions?.length ?? 0) > 0 ? "Edit" : "+ Add"} →
            </button>
          </div>
          {(profile.personalQuestions?.length ?? 0) === 0 ? (
            <button
              onClick={onOpenMyQuestions}
              className="w-full py-4 rounded-2xl border border-dashed text-sm text-match-muted transition-all hover:border-ember hover:text-ember"
              style={{ borderColor: "#2a2a3e" }}
            >
              + Add personal questions for matches to read
            </button>
          ) : (
            profile.personalQuestions.map((pq) => (
              <div key={pq.id} className="bg-match-card border border-match-border rounded-xl px-4 py-3 space-y-1">
                <div className="flex items-center gap-2">
                  <p className="text-match-muted text-xs flex-1">{pq.text}</p>
                  {!pq.isPublic && (
                    <span className="text-xs px-2 py-0.5 rounded-full flex-shrink-0" style={{ background: "#2a2a3e", color: "#8888aa" }}>
                      Hidden
                    </span>
                  )}
                </div>
                <p className="text-match-text text-sm font-medium leading-snug">{pq.answer}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
