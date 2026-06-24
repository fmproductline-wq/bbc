import React, { useState } from "react";

export interface PersonalQuestion {
  id: string;
  text: string;
  answer: string;
  isPublic: boolean; // visible to matches or only after QR reveal
}

interface Props {
  questions: PersonalQuestion[];
  onSave: (questions: PersonalQuestion[]) => void;
  onBack: () => void;
}

function blankQ(): PersonalQuestion {
  return { id: `pq_${Date.now()}`, text: "", answer: "", isPublic: true };
}

export const MyQuestions: React.FC<Props> = ({ questions, onSave, onBack }) => {
  const [items, setItems] = useState<PersonalQuestion[]>(questions);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<PersonalQuestion | null>(null);
  const [saved, setSaved] = useState(false);

  const startEdit = (q: PersonalQuestion) => {
    setDraft({ ...q });
    setEditingId(q.id);
  };

  const startNew = () => {
    const q = blankQ();
    setItems((prev) => [...prev, q]);
    setDraft({ ...q });
    setEditingId(q.id);
  };

  const saveDraft = () => {
    if (!draft || !draft.text.trim() || !draft.answer.trim()) return;
    setItems((prev) => prev.map((q) => (q.id === draft.id ? { ...draft, text: draft.text.trim(), answer: draft.answer.trim() } : q)));
    setDraft(null);
    setEditingId(null);
  };

  const cancelEdit = () => {
    // If the item was brand new and never saved, remove it
    if (draft && !questions.find((q) => q.id === draft.id) && !items.find((q) => q.id === draft.id && q.text.trim())) {
      setItems((prev) => prev.filter((q) => q.id !== draft.id));
    }
    setDraft(null);
    setEditingId(null);
  };

  const deleteItem = (id: string) => {
    setItems((prev) => prev.filter((q) => q.id !== id));
    if (editingId === id) { setDraft(null); setEditingId(null); }
  };

  const togglePublic = (id: string) => {
    setItems((prev) => prev.map((q) => q.id === id ? { ...q, isPublic: !q.isPublic } : q));
  };

  const persist = () => {
    const valid = items.filter((q) => q.text.trim() && q.answer.trim());
    onSave(valid);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  // ── Edit form ──────────────────────────────────────────────────────
  if (draft) {
    const canSave = draft.text.trim().length > 0 && draft.answer.trim().length > 0;

    return (
      <div className="flex flex-col h-full bg-match-bg">
        <div className="px-4 pt-12 pb-4 flex items-center gap-3" style={{ borderBottom: "1px solid #2a2a3e" }}>
          <button onClick={cancelEdit} className="text-match-muted text-2xl w-8">✕</button>
          <h2 className="text-match-text text-lg font-bold flex-1">
            {questions.find((q) => q.id === draft.id) ? "Edit question" : "New question"}
          </h2>
          <button
            onClick={saveDraft}
            disabled={!canSave}
            className="px-4 py-2 rounded-xl text-sm font-bold text-white disabled:opacity-40"
            style={{ background: "linear-gradient(135deg, #FF4500, #FF8C00)" }}
          >
            Done
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
          <div className="bg-match-card border border-match-border rounded-2xl p-4 space-y-1">
            <p className="text-ember text-xs font-semibold uppercase tracking-wider">What this does</p>
            <p className="text-match-muted text-sm leading-relaxed">
              Your personal questions appear on your profile and let matches learn more about you in your own words — beyond the standard questionnaire.
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-match-muted text-xs font-semibold uppercase tracking-wider">Your question *</label>
            <input
              className="w-full bg-match-card border border-match-border rounded-xl px-4 py-3 text-match-text text-sm outline-none focus:border-ember transition-colors"
              placeholder="e.g. What's something you could talk about for hours?"
              value={draft.text}
              onChange={(e) => setDraft((p) => p ? { ...p, text: e.target.value } : p)}
              maxLength={120}
            />
            <p className="text-match-muted text-xs text-right">{draft.text.length}/120</p>
          </div>

          <div className="space-y-2">
            <label className="text-match-muted text-xs font-semibold uppercase tracking-wider">Your answer *</label>
            <textarea
              className="w-full bg-match-card border border-match-border rounded-xl px-4 py-3 text-match-text text-sm outline-none focus:border-ember resize-none transition-colors"
              rows={4}
              placeholder="Write your honest answer…"
              value={draft.answer}
              onChange={(e) => setDraft((p) => p ? { ...p, answer: e.target.value } : p)}
              maxLength={300}
            />
            <p className="text-match-muted text-xs text-right">{draft.answer.length}/300</p>
          </div>

          <div className="flex items-center justify-between bg-match-card border border-match-border rounded-xl px-4 py-3">
            <div>
              <p className="text-match-text text-sm font-medium">
                {draft.isPublic ? "Visible to matches" : "Only after QR reveal"}
              </p>
              <p className="text-match-muted text-xs">
                {draft.isPublic
                  ? "Any match can read this on your profile"
                  : "Hidden until you share your QR code"}
              </p>
            </div>
            <button
              onClick={() => setDraft((p) => p ? { ...p, isPublic: !p.isPublic } : p)}
              className="relative w-12 h-6 rounded-full transition-colors flex-shrink-0 ml-3"
              style={{ background: draft.isPublic ? "#FF4500" : "#2a2a3e" }}
            >
              <span
                className="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform"
                style={{ transform: draft.isPublic ? "translateX(26px)" : "translateX(2px)" }}
              />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── List view ──────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full bg-match-bg">
      <div className="px-4 pt-12 pb-4 flex items-center gap-3" style={{ borderBottom: "1px solid #2a2a3e" }}>
        <button onClick={onBack} className="text-match-muted text-2xl w-8">‹</button>
        <div className="flex-1 min-w-0">
          <h2 className="text-match-text text-lg font-bold">My questions</h2>
          <p className="text-match-muted text-xs">{items.filter((q) => q.text.trim()).length} added</p>
        </div>
        <button
          onClick={persist}
          className="px-4 py-2 rounded-xl text-sm font-bold text-white flex-shrink-0 transition-all"
          style={{ background: saved ? "#22c55e" : "linear-gradient(135deg, #FF4500, #FF8C00)" }}
        >
          {saved ? "Saved ✓" : "Save"}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {/* Explainer */}
        <div
          className="rounded-2xl p-4 space-y-1"
          style={{ background: "#FF450010", border: "1px solid #FF450030" }}
        >
          <p className="text-ember text-xs font-semibold uppercase tracking-wider">About personal questions</p>
          <p className="text-match-muted text-sm leading-relaxed">
            Unlike the compatibility questionnaire, these are <strong className="text-match-text">written by you</strong> to tell your story your way. Matches can read them on your profile — or you can hide them until after QR reveal.
          </p>
        </div>

        {items.filter((q) => q.text.trim() || q.id === editingId).length === 0 && (
          <div className="text-center py-16 space-y-3">
            <p className="text-4xl">✍️</p>
            <p className="text-match-text font-semibold">No personal questions yet</p>
            <p className="text-match-muted text-sm">Add questions that let matches learn more about the real you.</p>
          </div>
        )}

        {items.map((q) => {
          if (!q.text.trim()) return null;
          return (
            <div key={q.id} className="bg-match-card border border-match-border rounded-2xl overflow-hidden">
              <div className="px-4 py-3 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-match-text text-sm font-semibold leading-snug flex-1">{q.text}</p>
                  <button
                    onClick={() => togglePublic(q.id)}
                    className="text-xs px-2 py-1 rounded-full flex-shrink-0"
                    style={{
                      background: q.isPublic ? "#22c55e22" : "#2a2a3e",
                      color: q.isPublic ? "#22c55e" : "#8888aa",
                      border: `1px solid ${q.isPublic ? "#22c55e55" : "#3a3a4e"}`,
                    }}
                  >
                    {q.isPublic ? "Public" : "Hidden"}
                  </button>
                </div>
                <p className="text-match-muted text-xs leading-relaxed line-clamp-2">{q.answer}</p>
              </div>
              <div className="flex border-t border-match-border divide-x divide-match-border">
                <button
                  onClick={() => startEdit(q)}
                  className="flex-1 py-2.5 text-xs font-semibold text-match-muted hover:text-ember transition-colors"
                >
                  Edit
                </button>
                <button
                  onClick={() => deleteItem(q.id)}
                  className="flex-1 py-2.5 text-xs font-semibold text-match-muted hover:text-red-400 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          );
        })}

        <div className="h-20" />
      </div>

      {/* FAB */}
      <div className="absolute bottom-6 left-6 right-6">
        <button
          onClick={startNew}
          disabled={items.filter((q) => q.text.trim()).length >= 10}
          className="w-full py-4 rounded-2xl font-bold text-white text-sm disabled:opacity-40 active:scale-95 transition-all"
          style={{ background: "linear-gradient(135deg, #FF4500, #FF8C00)", boxShadow: "0 4px 20px #FF450044" }}
        >
          + Add my own question
        </button>
        {items.filter((q) => q.text.trim()).length >= 10 && (
          <p className="text-match-muted text-xs text-center mt-2">Maximum 10 personal questions</p>
        )}
      </div>
    </div>
  );
};
