import React from "react";
import { QRCodeSVG } from "qrcode.react";

interface Props {
  value: string;
  size?: number;
  className?: string;
  label?: string;
  score?: number;
}

export const QRAvatar: React.FC<Props> = ({ value, size = 56, className = "", label, score }) => {
  return (
    <div className={`relative flex-shrink-0 ${className}`}>
      <div
        className="rounded-2xl overflow-hidden"
        style={{
          width: size,
          height: size,
          padding: 4,
          background: score && score >= 70
            ? "linear-gradient(135deg, #FF4500, #FF8C00, #FFD700)"
            : "#2a2a3e",
        }}
      >
        <div className="rounded-xl overflow-hidden w-full h-full bg-white">
          <QRCodeSVG
            value={value}
            size={size - 10}
            bgColor="#ffffff"
            fgColor="#0a0a0f"
            level="M"
          />
        </div>
      </div>
      {label && (
        <div
          className="absolute -bottom-1 -right-1 text-white text-xs font-bold rounded-full px-1.5 py-0.5"
          style={{ background: "#FF4500", fontSize: 9 }}
        >
          {label}
        </div>
      )}
    </div>
  );
};

export const BlurredQRAvatar: React.FC<{ size?: number }> = ({ size = 56 }) => (
  <div
    className="rounded-2xl overflow-hidden flex items-center justify-center relative flex-shrink-0"
    style={{ width: size, height: size, background: "#2a2a3e" }}
  >
    <div className="w-full h-full opacity-20 blur-sm">
      <QRCodeSVG value="HIDDEN" size={size} bgColor="#ffffff" fgColor="#0a0a0f" level="L" />
    </div>
    <div className="absolute inset-0 flex items-center justify-center">
      <span style={{ fontSize: size * 0.4 }}>🔒</span>
    </div>
  </div>
);
