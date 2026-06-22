import React, { useState } from "react";
import { QUESTIONS, CATEGORIES } from "../data/questions";
import { Answer, Question } from "../types";
import { Logo } from "./Logo";

interface Props {
  existingAnswers?: Answer[];
  onComplete: (answers: Answer[]) => void;
}

export const Questionnaire: React.FC<Props> = ({ existingAnswers = [], onComplete }) => {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [answers, setAnswers] = useState<Map<string, Answer["value"]>>(
    new Map(existingAnswers.map((a) => [a.questionId, a.value]))
  );
  const [scaleValue, setScaleValue] = useState<number>(5);

  const q = QUESTIONS[currentIdx];
  const progress = ((currentIdx) / QUESTIONS.length) * 100;
  const currentAnswer = answers.get(q.id);

  const setAnswer = (val: Answer["value"]) => {
    setAnswers((prev) => new Map(prev).set(q.id, val));
  };

  const handleNext = () => {
    if (!currentAnswer && q.type !== "scale") return;
    if (q.type === "scale" && currentAnswer === undefined) {
      setAnswer(scaleValue);
    }
    if (currentIdx < QUESTIONS.length - 1) {
      setCurrentIdx((i) => i + 1);
      const nextQ = QUESTIONS[currentIdx + 1];
      const existing = answers.get(nextQ.id);
      if (nextQ.type === "scale") {
        setScaleValue(existing !== undefined ? Number(existing) : 5);
      }
    } else {
      const result: Answer[] = QUESTIONS.map((q) => ({
        questionId: q.id,
        value: answers.get(q.id) ?? (q.type === "scale" ? 5 : ""),
      }));
      onComplete(result);
    }
  };

  const handleSkip = () => {
    if (currentIdx < QUESTIONS.length - 1) {
      setCurrentIdx((i) => i + 1);
    } else {
      const result: Answer[] = QUESTIONS.map((q) => ({
        questionId: q.id,
        value: answers.get(q.id) ?? (q.type === "scale" ? 5 : ""),
      }));
      onComplete(result);
    }
  };

  const toggleMulti = (opt: string) => {
    const current = (currentAnswer as string[]) || [];
    if (current.includes(opt)) {
      setAnswer(current.filter((x) => x !== opt));
    } else {
      setAnswer([...current, opt]);
    }
  };

  const categoryColor: Record<string, string> = {
    Lifestyle: "#FB923C",
    Values: "#F97316",
    Personality: "#EF4444",
    Interests: "#EC4899",
    Relationship: "#FF4500",
    Communication: "#FF8C00",
  };

  const catColor = categoryColor[q.category] || "#FF4500";

  return (
    <div className="flex flex-col h-full bg-match-bg">
      {/* Header */}
      <div className="px-4 pt-12 pb-4">
        <div className="flex items-center justify-between mb-4">
          <Logo size={32} />
          <div className="text-right">
            <p className="text-match-muted text-xs">{currentIdx + 1} of {QUESTIONS.length}</p>
            <p className="text-xs font-semibold" style={{ color: catColor }}>{q.category}</p>
          </div>
        </div>
        {/* Progress bar */}
        <div className="h-1 bg-match-border rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${progress}%`, background: `linear-gradient(90deg, #FF4500, #FF8C00)` }}
          />
        </div>
      </div>

      {/* Question */}
      <div className="flex-1 overflow-y-auto px-6 pb-4">
        <div className="mb-6">
          <div
            className="inline-block px-3 py-1 rounded-full text-xs font-semibold mb-3"
            style={{ background: `${catColor}22`, color: catColor }}
          >
            {q.category}
          </div>
          <h2 className="text-match-text text-xl font-bold leading-tight">{q.text}</h2>
        </div>

        {/* Single choice */}
        {q.type === "single" && (
          <div className="space-y-2.5">
            {q.options!.map((opt) => (
              <button
                key={opt}
                onClick={() => setAnswer(opt)}
                className="w-full text-left px-4 py-3.5 rounded-2xl border text-sm font-medium transition-all active:scale-95"
                style={{
                  background: currentAnswer === opt ? `${catColor}22` : "#12121a",
                  borderColor: currentAnswer === opt ? catColor : "#2a2a3e",
                  color: currentAnswer === opt ? catColor : "#e8e8f0",
                }}
              >
                {opt}
              </button>
            ))}
          </div>
        )}

        {/* Multi choice */}
        {q.type === "multi" && (
          <div className="flex flex-wrap gap-2">
            {q.options!.map((opt) => {
              const sel = ((currentAnswer as string[]) || []).includes(opt);
              return (
                <button
                  key={opt}
                  onClick={() => toggleMulti(opt)}
                  className="px-4 py-2 rounded-full border text-sm font-medium transition-all active:scale-95"
                  style={{
                    background: sel ? `${catColor}22` : "#12121a",
                    borderColor: sel ? catColor : "#2a2a3e",
                    color: sel ? catColor : "#e8e8f0",
                  }}
                >
                  {opt}
                </button>
              );
            })}
          </div>
        )}

        {/* Scale */}
        {q.type === "scale" && (
          <div className="space-y-6">
            <div className="relative pt-2">
              <input
                type="range"
                min="1"
                max="10"
                value={currentAnswer !== undefined ? Number(currentAnswer) : scaleValue}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setScaleValue(v);
                  setAnswer(v);
                }}
                className="w-full accent-ember"
              />
              <div className="flex justify-between mt-2">
                <span className="text-match-muted text-xs">{q.scaleMin}</span>
                <span className="text-ember font-bold text-lg">
                  {currentAnswer !== undefined ? Number(currentAnswer) : scaleValue}/10
                </span>
                <span className="text-match-muted text-xs text-right">{q.scaleMax}</span>
              </div>
            </div>
          </div>
        )}

        {/* Text */}
        {q.type === "text" && (
          <textarea
            className="w-full bg-match-card border border-match-border rounded-xl px-4 py-3 text-match-text text-sm outline-none focus:border-ember resize-none"
            rows={4}
            placeholder="Your answer..."
            value={(currentAnswer as string) || ""}
            onChange={(e) => setAnswer(e.target.value)}
          />
        )}
      </div>

      {/* Actions */}
      <div className="px-6 pb-10 pt-2 space-y-2">
        <button
          onClick={handleNext}
          disabled={!currentAnswer && q.type !== "scale"}
          className="w-full py-4 rounded-2xl font-bold text-white text-base transition-all active:scale-95 disabled:opacity-40"
          style={{ background: "linear-gradient(135deg, #FF4500, #FF8C00)" }}
        >
          {currentIdx < QUESTIONS.length - 1 ? "Next →" : "Complete profile 🔥"}
        </button>
        <button onClick={handleSkip} className="w-full py-2 text-match-muted text-sm">
          Skip this question
        </button>
      </div>
    </div>
  );
};
