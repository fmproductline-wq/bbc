import React, { useState } from "react";

const ADMIN_PIN_KEY = "matches_admin_pin";
const ADMIN_SESSION_KEY = "matches_admin_session";

export function isAdminUnlocked(): boolean {
  return sessionStorage.getItem(ADMIN_SESSION_KEY) === "true";
}

function getStoredPin(): string | null {
  return localStorage.getItem(ADMIN_PIN_KEY);
}

interface Props {
  onUnlocked: () => void;
  onBack: () => void;
}

export const AdminGate: React.FC<Props> = ({ onUnlocked, onBack }) => {
  const hasPin = !!getStoredPin();
  const [mode, setMode] = useState<"enter" | "set">(hasPin ? "enter" : "set");
  const [pin, setPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [error, setError] = useState("");
  const [digits, setDigits] = useState<string[]>([]);

  const MAX = 4;

  const addDigit = (d: string) => {
    if (digits.length >= MAX) return;
    const next = [...digits, d];
    setDigits(next);
    setError("");

    if (next.length === MAX) {
      const entered = next.join("");
      setTimeout(() => {
        if (mode === "enter") {
          if (entered === getStoredPin()) {
            sessionStorage.setItem(ADMIN_SESSION_KEY, "true");
            onUnlocked();
          } else {
            setError("Wrong PIN. Try again.");
            setDigits([]);
          }
        } else {
          // setting new PIN — first entry
          if (!pin) {
            setPin(entered);
            setDigits([]);
          } else {
            // confirm
            if (entered === pin) {
              localStorage.setItem(ADMIN_PIN_KEY, pin);
              sessionStorage.setItem(ADMIN_SESSION_KEY, "true");
              onUnlocked();
            } else {
              setError("PINs don't match. Start over.");
              setPin("");
              setDigits([]);
            }
          }
        }
      }, 120);
    }
  };

  const removeDigit = () => {
    setDigits((prev) => prev.slice(0, -1));
    setError("");
  };

  const step = mode === "set" && !pin ? "create" : mode === "set" && pin ? "confirm" : "enter";
  const titles: Record<string, string> = {
    enter: "Admin access",
    create: "Create admin PIN",
    confirm: "Confirm PIN",
  };
  const subtitles: Record<string, string> = {
    enter: "Enter your 4-digit admin PIN",
    create: "Choose a 4-digit PIN to protect the editor",
    confirm: "Re-enter your PIN to confirm",
  };

  return (
    <div className="flex flex-col h-full bg-match-bg">
      <div className="px-4 pt-12 pb-4 flex items-center gap-3" style={{ borderBottom: "1px solid #2a2a3e" }}>
        <button onClick={onBack} className="text-match-muted text-2xl w-8">‹</button>
        <h2 className="text-match-text text-lg font-bold">{titles[step]}</h2>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center px-8 gap-10">
        {/* Lock icon */}
        <div
          className="w-20 h-20 rounded-3xl flex items-center justify-center"
          style={{ background: "linear-gradient(135deg, #FF4500, #FF8C00)" }}
        >
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>

        <div className="text-center space-y-1">
          <p className="text-match-text font-bold text-xl">{titles[step]}</p>
          <p className="text-match-muted text-sm">{subtitles[step]}</p>
          {mode === "set" && pin && (
            <p className="text-ember text-xs mt-2">Now confirm your PIN</p>
          )}
        </div>

        {/* PIN dots */}
        <div className="flex gap-4">
          {Array.from({ length: MAX }).map((_, i) => (
            <div
              key={i}
              className="w-4 h-4 rounded-full transition-all"
              style={{
                background: i < digits.length ? "#FF4500" : "#2a2a3e",
                transform: i < digits.length ? "scale(1.2)" : "scale(1)",
                boxShadow: i < digits.length ? "0 0 8px #FF450066" : "none",
              }}
            />
          ))}
        </div>

        {error && (
          <p className="text-red-400 text-sm text-center -mt-4 bg-red-950/30 px-4 py-2 rounded-xl border border-red-900">
            {error}
          </p>
        )}

        {/* Numpad */}
        <div className="grid grid-cols-3 gap-3 w-full max-w-xs">
          {["1","2","3","4","5","6","7","8","9","","0","⌫"].map((key) => (
            <button
              key={key}
              onClick={() => {
                if (key === "⌫") removeDigit();
                else if (key) addDigit(key);
              }}
              disabled={!key}
              className="h-16 rounded-2xl text-xl font-semibold transition-all active:scale-90 disabled:opacity-0"
              style={{
                background: key === "⌫" ? "#1a1a26" : "#12121a",
                color: key === "⌫" ? "#8888aa" : "#e8e8f0",
                border: "1px solid #2a2a3e",
              }}
            >
              {key}
            </button>
          ))}
        </div>

        {mode === "enter" && (
          <button
            onClick={() => {
              localStorage.removeItem(ADMIN_PIN_KEY);
              setMode("set");
              setPin("");
              setDigits([]);
              setError("");
            }}
            className="text-match-muted text-xs"
          >
            Forgot PIN? Reset it
          </button>
        )}
      </div>
    </div>
  );
};
