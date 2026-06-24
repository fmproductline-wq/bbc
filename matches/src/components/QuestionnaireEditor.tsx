import React, { useState, useRef } from "react";
import { Question } from "../types";
import { QUESTIONS as DEFAULT_QUESTIONS } from "../data/questions";
import { v4 as uuidv4 } from "uuid";

const STORAGE_KEY = "matches_custom_questions";

export function loadQuestions(): Question[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch {}
  return DEFAULT_QUESTIONS;
}

export function saveQuestions(questions: Question[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(questions));
}

const QUESTION_TYPES: { value: Question["type"]; label: string; desc: string }[] = [
  { value: "single", label: "Single choice", desc: "Pick one option" },
  { value: "multi", label: "Multi choice", desc: "Pick multiple options" },
  { value: "scale", label: "Scale", desc: "Slider from 1–10" },
  { value: "text", label: "Free text", desc: "Open answer" },
];

const WEIGHT_LABELS: Record<number, string> = { 1: "Low", 2: "Medium", 3: "High" };
const DEFAULT_CATEGORIES = ["Lifestyle", "Values", "Personality", "Interests", "Relationship", "Communication"];

interface Props {
  onBack: () => void;
}

function blankQuestion(): Question {
  return {
    id: `q_${uuidv4().slice(0, 6)}`,
    category: "Lifestyle",
    text: "",
    type: "single",
    options: ["", ""],
    weight: 2,
  };
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// ── Media picker sheet ───────────────────────────────────────────────
interface MediaPickerProps {
  current?: Question["media"];
  onSelect: (media: Question["media"]) => void;
  onClose: () => void;
}

const MediaPicker: React.FC<MediaPickerProps> = ({ current, onSelect, onClose }) => {
  const imageRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);

  const handleFile = async (file: File, type: "image" | "audio") => {
    setLoading(true);
    try {
      const dataUrl = await readFileAsDataUrl(file);
      onSelect({ type, dataUrl, name: file.name });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="absolute inset-0 bg-black/70 flex items-end z-50" onClick={onClose}>
      <div
        className="bg-match-surface rounded-t-3xl px-6 pt-5 pb-10 w-full space-y-3"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="w-10 h-1 bg-match-border rounded-full mx-auto mb-3" />
        <p className="text-match-text font-bold text-base text-center mb-4">Add media to question</p>

        {/* Current media preview */}
        {current && (
          <div className="bg-match-card border border-match-border rounded-2xl p-3 flex items-center gap-3 mb-2">
            <span className="text-2xl">{current.type === "image" ? "🖼️" : "🎵"}</span>
            <div className="flex-1 min-w-0">
              <p className="text-match-text text-sm font-medium truncate">{current.name}</p>
              <p className="text-match-muted text-xs">{current.type === "image" ? "Image attached" : "Audio attached"}</p>
            </div>
            <button
              onClick={() => onSelect(undefined)}
              className="text-red-400 text-xs font-semibold px-3 py-1.5 rounded-xl border border-red-900"
              style={{ background: "#1a0808" }}
            >
              Remove
            </button>
          </div>
        )}

        {/* Image preview */}
        {current?.type === "image" && (
          <img
            src={current.dataUrl}
            alt="Question media"
            className="w-full rounded-2xl object-cover max-h-48"
          />
        )}

        {/* Audio preview */}
        {current?.type === "audio" && (
          <audio controls className="w-full" src={current.dataUrl} />
        )}

        {/* Pick buttons */}
        <button
          onClick={() => imageRef.current?.click()}
          disabled={loading}
          className="w-full flex items-center gap-4 px-4 py-4 rounded-2xl border border-match-border bg-match-card transition-all active:scale-95"
        >
          <div className="w-11 h-11 rounded-xl flex items-center justify-center text-2xl flex-shrink-0" style={{ background: "#FF450020" }}>
            🖼️
          </div>
          <div className="text-left">
            <p className="text-match-text text-sm font-semibold">Add image</p>
            <p className="text-match-muted text-xs">JPG, PNG, GIF, WebP</p>
          </div>
        </button>

        <button
          onClick={() => audioRef.current?.click()}
          disabled={loading}
          className="w-full flex items-center gap-4 px-4 py-4 rounded-2xl border border-match-border bg-match-card transition-all active:scale-95"
        >
          <div className="w-11 h-11 rounded-xl flex items-center justify-center text-2xl flex-shrink-0" style={{ background: "#FF450020" }}>
            🎵
          </div>
          <div className="text-left">
            <p className="text-match-text text-sm font-semibold">Add audio</p>
            <p className="text-match-muted text-xs">MP3, WAV, OGG, M4A</p>
          </div>
        </button>

        {loading && (
          <p className="text-ember text-sm text-center animate-pulse">Loading file…</p>
        )}

        <button onClick={onClose} className="w-full py-3 text-match-muted text-sm">
          Cancel
        </button>

        {/* Hidden file inputs */}
        <input
          ref={imageRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f, "image"); }}
        />
        <input
          ref={audioRef}
          type="file"
          accept="audio/*"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f, "audio"); }}
        />
      </div>
    </div>
  );
};

// ── Main editor ─────────────────────────────────────────────────────
export const QuestionnaireEditor: React.FC<Props> = ({ onBack }) => {
  const [questions, setQuestions] = useState<Question[]>(loadQuestions);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Question | null>(null);
  const [saved, setSaved] = useState(false);
  const [filterCategory, setFilterCategory] = useState<string>("All");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [customCategory, setCustomCategory] = useState("");
  const [showMediaPicker, setShowMediaPicker] = useState(false);

  const allCategories = ["All", ...Array.from(new Set([...DEFAULT_CATEGORIES, ...questions.map((q) => q.category)]))];
  const filtered = filterCategory === "All" ? questions : questions.filter((q) => q.category === filterCategory);

  const startEdit = (q: Question, isNewQ = false) => {
    setDraft({ ...q, options: q.options ? [...q.options] : [] });
    setEditingId(q.id);
    setIsNew(isNewQ);
  };

  const startNew = () => { startEdit(blankQuestion(), true); };

  const cancelEdit = () => {
    setDraft(null);
    setEditingId(null);
    setIsNew(false);
    setShowMediaPicker(false);
  };

  const saveDraft = () => {
    if (!draft) return;
    if (!draft.text.trim()) return;
    if ((draft.type === "single" || draft.type === "multi") && draft.options!.filter((o) => o.trim()).length < 2) return;
    const cleanDraft = {
      ...draft,
      text: draft.text.trim(),
      options: draft.options?.filter((o) => o.trim()).map((o) => o.trim()),
    };
    if (isNew) setQuestions((prev) => [...prev, cleanDraft]);
    else setQuestions((prev) => prev.map((q) => (q.id === cleanDraft.id ? cleanDraft : q)));
    cancelEdit();
  };

  const deleteQuestion = (id: string) => {
    setQuestions((prev) => prev.filter((q) => q.id !== id));
    setConfirmDeleteId(null);
  };

  const moveQuestion = (id: string, dir: -1 | 1) => {
    setQuestions((prev) => {
      const idx = prev.findIndex((q) => q.id === id);
      if (idx < 0) return prev;
      const next = [...prev];
      const swap = idx + dir;
      if (swap < 0 || swap >= next.length) return prev;
      [next[idx], next[swap]] = [next[swap], next[idx]];
      return next;
    });
  };

  const persist = () => {
    saveQuestions(questions);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const resetToDefaults = () => {
    setQuestions(DEFAULT_QUESTIONS);
    saveQuestions(DEFAULT_QUESTIONS);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const updateOption = (idx: number, val: string) => {
    setDraft((prev) => {
      if (!prev) return prev;
      const opts = [...(prev.options || [])];
      opts[idx] = val;
      return { ...prev, options: opts };
    });
  };

  const addOption = () => setDraft((prev) => prev ? { ...prev, options: [...(prev.options || []), ""] } : prev);

  const removeOption = (idx: number) => {
    setDraft((prev) => {
      if (!prev) return prev;
      const opts = [...(prev.options || [])];
      opts.splice(idx, 1);
      return { ...prev, options: opts };
    });
  };

  // ── Edit / New form ──────────────────────────────────────────────
  if (draft) {
    const needsOptions = draft.type === "single" || draft.type === "multi";
    const needsScale = draft.type === "scale";
    const validOptions = needsOptions ? (draft.options || []).filter((o) => o.trim()).length >= 2 : true;
    const canSave = draft.text.trim().length > 0 && validOptions;
    const categoryOptions = [...new Set([...DEFAULT_CATEGORIES, draft.category])].filter(Boolean);

    return (
      <div className="flex flex-col h-full bg-match-bg relative">
        {/* Header */}
        <div className="px-4 pt-12 pb-4 flex items-center gap-3" style={{ borderBottom: "1px solid #2a2a3e" }}>
          <button onClick={cancelEdit} className="text-match-muted text-2xl w-8">✕</button>
          <h2 className="text-match-text text-lg font-bold flex-1">{isNew ? "New question" : "Edit question"}</h2>
          <button
            onClick={saveDraft}
            disabled={!canSave}
            className="px-4 py-2 rounded-xl text-sm font-bold text-white disabled:opacity-40 transition-all"
            style={{ background: "linear-gradient(135deg, #FF4500, #FF8C00)" }}
          >
            {isNew ? "Add" : "Save"}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
          {/* Question text */}
          <div className="space-y-2">
            <label className="text-match-muted text-xs font-semibold uppercase tracking-wider">Question *</label>
            <textarea
              className="w-full bg-match-card border border-match-border rounded-xl px-4 py-3 text-match-text text-sm outline-none focus:border-ember resize-none transition-colors"
              rows={3}
              placeholder="e.g. What matters most to you in a relationship?"
              value={draft.text}
              onChange={(e) => setDraft((p) => p ? { ...p, text: e.target.value } : p)}
              maxLength={200}
            />
            <p className="text-match-muted text-xs text-right">{draft.text.length}/200</p>
          </div>

          {/* ── Media attachment ── */}
          <div className="space-y-2">
            <label className="text-match-muted text-xs font-semibold uppercase tracking-wider">
              Media (optional)
            </label>

            {/* Preview if media already attached */}
            {draft.media ? (
              <div className="space-y-2">
                {draft.media.type === "image" && (
                  <img
                    src={draft.media.dataUrl}
                    alt="Question media"
                    className="w-full rounded-2xl object-cover max-h-48"
                  />
                )}
                {draft.media.type === "audio" && (
                  <audio controls className="w-full" src={draft.media.dataUrl} />
                )}
                <div className="flex gap-2">
                  <div className="flex-1 flex items-center gap-2 bg-match-card border border-match-border rounded-xl px-3 py-2.5">
                    <span className="text-base">{draft.media.type === "image" ? "🖼️" : "🎵"}</span>
                    <span className="text-match-text text-xs truncate">{draft.media.name}</span>
                  </div>
                  <button
                    onClick={() => setShowMediaPicker(true)}
                    className="px-3 py-2 rounded-xl text-xs font-semibold border border-match-border text-match-muted"
                  >
                    Change
                  </button>
                  <button
                    onClick={() => setDraft((p) => p ? { ...p, media: undefined } : p)}
                    className="px-3 py-2 rounded-xl text-xs font-semibold text-red-400 border border-red-900"
                    style={{ background: "#1a0808" }}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ) : (
              /* + Add media button */
              <button
                onClick={() => setShowMediaPicker(true)}
                className="w-full flex items-center gap-3 px-4 py-4 rounded-2xl border-2 border-dashed transition-all active:scale-95 group"
                style={{ borderColor: "#2a2a3e" }}
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center text-xl flex-shrink-0 transition-colors"
                  style={{ background: "#FF450022" }}
                >
                  <span
                    className="font-bold leading-none"
                    style={{ color: "#FF4500", fontSize: 22 }}
                  >
                    +
                  </span>
                </div>
                <div className="text-left">
                  <p className="text-match-text text-sm font-semibold">Add image or audio</p>
                  <p className="text-match-muted text-xs">Attach a photo or sound clip to this question</p>
                </div>
              </button>
            )}
          </div>

          {/* Category */}
          <div className="space-y-2">
            <label className="text-match-muted text-xs font-semibold uppercase tracking-wider">Category</label>
            <div className="flex flex-wrap gap-2">
              {categoryOptions.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setDraft((p) => p ? { ...p, category: cat } : p)}
                  className="px-3 py-1.5 rounded-full text-xs font-medium border transition-all"
                  style={{
                    background: draft.category === cat ? "#FF450022" : "#12121a",
                    borderColor: draft.category === cat ? "#FF4500" : "#2a2a3e",
                    color: draft.category === cat ? "#FF4500" : "#8888aa",
                  }}
                >
                  {cat}
                </button>
              ))}
            </div>
            <div className="flex gap-2 mt-1">
              <input
                className="flex-1 bg-match-card border border-match-border rounded-xl px-3 py-2 text-match-text text-sm outline-none focus:border-ember transition-colors"
                placeholder="Or add new category…"
                value={customCategory}
                onChange={(e) => setCustomCategory(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && customCategory.trim()) {
                    setDraft((p) => p ? { ...p, category: customCategory.trim() } : p);
                    setCustomCategory("");
                  }
                }}
              />
              <button
                onClick={() => {
                  if (customCategory.trim()) {
                    setDraft((p) => p ? { ...p, category: customCategory.trim() } : p);
                    setCustomCategory("");
                  }
                }}
                className="px-3 py-2 rounded-xl text-sm font-semibold"
                style={{ background: "#FF450033", color: "#FF4500" }}
              >
                Add
              </button>
            </div>
          </div>

          {/* Question type */}
          <div className="space-y-2">
            <label className="text-match-muted text-xs font-semibold uppercase tracking-wider">Answer type</label>
            <div className="grid grid-cols-2 gap-2">
              {QUESTION_TYPES.map((t) => (
                <button
                  key={t.value}
                  onClick={() => {
                    setDraft((p) => {
                      if (!p) return p;
                      const updated: Question = { ...p, type: t.value };
                      if (t.value === "single" || t.value === "multi") {
                        updated.options = p.options?.length ? p.options : ["", ""];
                        delete updated.scaleMin;
                        delete updated.scaleMax;
                      } else if (t.value === "scale") {
                        updated.scaleMin = p.scaleMin || "Low";
                        updated.scaleMax = p.scaleMax || "High";
                        delete updated.options;
                      } else {
                        delete updated.options;
                        delete updated.scaleMin;
                        delete updated.scaleMax;
                      }
                      return updated;
                    });
                  }}
                  className="flex flex-col items-start px-3 py-3 rounded-xl border transition-all text-left"
                  style={{
                    background: draft.type === t.value ? "#FF450015" : "#12121a",
                    borderColor: draft.type === t.value ? "#FF4500" : "#2a2a3e",
                  }}
                >
                  <span className="text-sm font-semibold" style={{ color: draft.type === t.value ? "#FF4500" : "#e8e8f0" }}>
                    {t.label}
                  </span>
                  <span className="text-xs text-match-muted mt-0.5">{t.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Options — single / multi */}
          {needsOptions && (
            <div className="space-y-2">
              <label className="text-match-muted text-xs font-semibold uppercase tracking-wider">
                Answer options * (min 2)
              </label>
              <div className="space-y-2">
                {(draft.options || []).map((opt, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="text-match-muted text-xs w-5 text-right flex-shrink-0">{i + 1}.</span>
                    <input
                      className="flex-1 bg-match-card border border-match-border rounded-xl px-3 py-2.5 text-match-text text-sm outline-none focus:border-ember transition-colors"
                      placeholder={`Option ${i + 1}`}
                      value={opt}
                      onChange={(e) => updateOption(i, e.target.value)}
                    />
                    {(draft.options || []).length > 2 && (
                      <button
                        onClick={() => removeOption(i)}
                        className="w-8 h-8 flex items-center justify-center rounded-lg text-match-muted hover:text-red-400 flex-shrink-0"
                        style={{ background: "#1a1a26" }}
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}
              </div>
              {(draft.options || []).length < 8 && (
                <button
                  onClick={addOption}
                  className="w-full py-2.5 rounded-xl border border-dashed text-sm text-match-muted transition-all hover:border-ember hover:text-ember"
                  style={{ borderColor: "#2a2a3e" }}
                >
                  + Add option
                </button>
              )}
            </div>
          )}

          {/* Scale labels */}
          {needsScale && (
            <div className="space-y-3">
              <label className="text-match-muted text-xs font-semibold uppercase tracking-wider">Scale labels</label>
              <div className="flex gap-3 items-center">
                <div className="flex-1 space-y-1">
                  <p className="text-match-muted text-xs">Left label (low end)</p>
                  <input
                    className="w-full bg-match-card border border-match-border rounded-xl px-3 py-2.5 text-match-text text-sm outline-none focus:border-ember transition-colors"
                    placeholder="e.g. Not at all"
                    value={draft.scaleMin || ""}
                    onChange={(e) => setDraft((p) => p ? { ...p, scaleMin: e.target.value } : p)}
                  />
                </div>
                <div className="text-match-muted text-lg mt-5">→</div>
                <div className="flex-1 space-y-1">
                  <p className="text-match-muted text-xs">Right label (high end)</p>
                  <input
                    className="w-full bg-match-card border border-match-border rounded-xl px-3 py-2.5 text-match-text text-sm outline-none focus:border-ember transition-colors"
                    placeholder="e.g. Very much"
                    value={draft.scaleMax || ""}
                    onChange={(e) => setDraft((p) => p ? { ...p, scaleMax: e.target.value } : p)}
                  />
                </div>
              </div>
              <div className="bg-match-card rounded-xl p-3 flex items-center gap-2">
                <span className="text-match-muted text-xs">{draft.scaleMin || "Low"}</span>
                <input type="range" min="1" max="10" defaultValue="5" className="flex-1 accent-ember" disabled />
                <span className="text-match-muted text-xs">{draft.scaleMax || "High"}</span>
              </div>
            </div>
          )}

          {/* Matching weight */}
          <div className="space-y-2">
            <label className="text-match-muted text-xs font-semibold uppercase tracking-wider">
              Matching weight
            </label>
            <div className="grid grid-cols-3 gap-2">
              {([1, 2, 3] as const).map((w) => (
                <button
                  key={w}
                  onClick={() => setDraft((p) => p ? { ...p, weight: w } : p)}
                  className="py-3 rounded-xl border text-sm font-semibold transition-all"
                  style={{
                    background: draft.weight === w ? "#FF450020" : "#12121a",
                    borderColor: draft.weight === w ? "#FF4500" : "#2a2a3e",
                    color: draft.weight === w ? "#FF4500" : "#8888aa",
                  }}
                >
                  {WEIGHT_LABELS[w]}
                </button>
              ))}
            </div>
          </div>

          {!canSave && draft.text.trim() && needsOptions && !validOptions && (
            <p className="text-red-400 text-xs bg-red-950/30 border border-red-900 rounded-xl px-3 py-2">
              Add at least 2 answer options to save.
            </p>
          )}
        </div>

        {/* Media picker sheet */}
        {showMediaPicker && (
          <MediaPicker
            current={draft.media}
            onSelect={(media) => {
              setDraft((p) => p ? { ...p, media } : p);
              setShowMediaPicker(false);
            }}
            onClose={() => setShowMediaPicker(false)}
          />
        )}
      </div>
    );
  }

  // ── Question list ────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full bg-match-bg relative">
      <div className="px-4 pt-12 pb-3 flex items-center gap-3" style={{ borderBottom: "1px solid #2a2a3e" }}>
        <button onClick={onBack} className="text-match-muted text-2xl w-8">‹</button>
        <div className="flex-1 min-w-0">
          <h2 className="text-match-text text-lg font-bold">Questionnaire editor</h2>
          <p className="text-match-muted text-xs">{questions.length} questions</p>
        </div>
        <button
          onClick={persist}
          className="px-4 py-2 rounded-xl text-sm font-bold text-white transition-all active:scale-95 flex-shrink-0"
          style={{ background: saved ? "#22c55e" : "linear-gradient(135deg, #FF4500, #FF8C00)" }}
        >
          {saved ? "Saved ✓" : "Save all"}
        </button>
      </div>

      <div className="px-4 py-3 overflow-x-auto flex gap-2 no-scrollbar" style={{ borderBottom: "1px solid #2a2a3e" }}>
        {allCategories.map((cat) => (
          <button
            key={cat}
            onClick={() => setFilterCategory(cat)}
            className="px-3 py-1.5 rounded-full text-xs font-semibold flex-shrink-0 transition-all"
            style={{
              background: filterCategory === cat ? "#FF450022" : "#1a1a26",
              color: filterCategory === cat ? "#FF4500" : "#8888aa",
              border: `1px solid ${filterCategory === cat ? "#FF4500" : "#2a2a3e"}`,
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="mx-4 mt-3 px-4 py-3 rounded-2xl flex items-start gap-2" style={{ background: "#FF450012", border: "1px solid #FF450033" }}>
        <span className="text-base flex-shrink-0 mt-0.5">ℹ️</span>
        <p className="text-match-muted text-xs leading-relaxed">
          Every new user answers these questions. You can attach an image or audio to any question to give it more context.
          Click <strong className="text-match-text">Save all</strong> to apply changes.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {filtered.map((q) => {
          const globalIdx = questions.findIndex((x) => x.id === q.id);
          return (
            <div key={q.id} className="bg-match-card border border-match-border rounded-2xl overflow-hidden">
              {/* Media preview on card */}
              {q.media?.type === "image" && (
                <img src={q.media.dataUrl} alt="" className="w-full object-cover max-h-32" />
              )}
              {q.media?.type === "audio" && (
                <div className="px-4 pt-3">
                  <audio controls className="w-full" src={q.media.dataUrl} />
                </div>
              )}

              <div className="flex items-start gap-3 px-4 py-3">
                <div className="flex flex-col items-center gap-1 pt-1 flex-shrink-0">
                  <button onClick={() => moveQuestion(q.id, -1)} disabled={globalIdx === 0} className="text-match-muted disabled:opacity-20 text-xs leading-none">▲</button>
                  <span className="text-match-muted text-xs font-mono">{globalIdx + 1}</span>
                  <button onClick={() => moveQuestion(q.id, 1)} disabled={globalIdx === questions.length - 1} className="text-match-muted disabled:opacity-20 text-xs leading-none">▼</button>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ background: "#FF450020", color: "#FF6A33" }}>
                      {q.category}
                    </span>
                    <span className="text-xs text-match-muted border border-match-border rounded-full px-2 py-0.5">
                      {QUESTION_TYPES.find((t) => t.value === q.type)?.label}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full" style={{
                      background: q.weight === 3 ? "#FF450022" : q.weight === 2 ? "#FF8C0022" : "#2a2a3e",
                      color: q.weight === 3 ? "#FF4500" : q.weight === 2 ? "#FF8C00" : "#8888aa",
                    }}>
                      {WEIGHT_LABELS[q.weight]} weight
                    </span>
                    {q.media && (
                      <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "#8B5CF622", color: "#a78bfa" }}>
                        {q.media.type === "image" ? "🖼️ image" : "🎵 audio"}
                      </span>
                    )}
                  </div>
                  <p className="text-match-text text-sm font-medium leading-snug">{q.text}</p>
                  {q.options && q.options.length > 0 && (
                    <p className="text-match-muted text-xs mt-1 truncate">{q.options.join(" · ")}</p>
                  )}
                  {q.type === "scale" && (
                    <p className="text-match-muted text-xs mt-1">{q.scaleMin || "Low"} → {q.scaleMax || "High"}</p>
                  )}
                </div>
              </div>

              <div className="flex border-t border-match-border divide-x divide-match-border">
                <button onClick={() => startEdit(q)} className="flex-1 py-2.5 text-xs font-semibold text-match-muted hover:text-ember transition-colors">
                  Edit
                </button>
                <button onClick={() => setConfirmDeleteId(q.id)} className="flex-1 py-2.5 text-xs font-semibold text-match-muted hover:text-red-400 transition-colors">
                  Delete
                </button>
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="text-center py-12 text-match-muted text-sm">No questions in this category.</div>
        )}
        <div className="h-20" />
      </div>

      <div className="absolute bottom-6 right-6 left-6 flex gap-3">
        <button onClick={resetToDefaults} className="px-4 py-3.5 rounded-2xl text-sm font-semibold text-match-muted border border-match-border bg-match-card">
          Reset defaults
        </button>
        <button
          onClick={startNew}
          className="flex-1 py-3.5 rounded-2xl text-sm font-bold text-white shadow-lg transition-all active:scale-95"
          style={{ background: "linear-gradient(135deg, #FF4500, #FF8C00)", boxShadow: "0 4px 20px #FF450044" }}
        >
          + Add question
        </button>
      </div>

      {confirmDeleteId && (
        <div className="absolute inset-0 bg-black/70 flex items-end z-50">
          <div className="bg-match-surface rounded-t-3xl px-6 pt-5 pb-10 w-full space-y-4">
            <div className="w-10 h-1 bg-match-border rounded-full mx-auto mb-2" />
            <div className="text-center space-y-2">
              <p className="text-2xl">🗑️</p>
              <h3 className="text-match-text font-bold">Delete this question?</h3>
              <p className="text-match-muted text-sm">Existing answers for this question won't be matched anymore.</p>
            </div>
            <button onClick={() => deleteQuestion(confirmDeleteId)} className="w-full py-4 rounded-2xl font-bold text-white bg-red-600">Delete</button>
            <button onClick={() => setConfirmDeleteId(null)} className="w-full py-3 text-match-muted text-sm">Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
};
