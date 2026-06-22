import React from "react";

interface LogoProps {
  size?: number;
  animated?: boolean;
  showText?: boolean;
}

export const Logo: React.FC<LogoProps> = ({ size = 80, animated = false, showText = false }) => {
  return (
    <div className="flex flex-col items-center gap-2">
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={animated ? "animate-pulse" : ""}
      >
        <defs>
          <linearGradient id="fireL" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#FF4500" />
            <stop offset="50%" stopColor="#FF8C00" />
            <stop offset="100%" stopColor="#FFD700" />
          </linearGradient>
          <linearGradient id="fireR" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#FF4500" />
            <stop offset="50%" stopColor="#FF8C00" />
            <stop offset="100%" stopColor="#FFD700" />
          </linearGradient>
          <linearGradient id="stickL" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#8B4513" />
            <stop offset="100%" stopColor="#5C2D0A" />
          </linearGradient>
          <linearGradient id="stickR" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#8B4513" />
            <stop offset="100%" stopColor="#5C2D0A" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="fireGlow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Heart outline formed by 2 match sticks */}
        {/* Left match stick — curves left-down forming left lobe of heart */}
        {/* The sticks meet at the bottom point and flare up at top */}

        {/* Left stick body — diagonal left lobe */}
        <path
          d="M 50 85 L 22 52"
          stroke="url(#stickL)"
          strokeWidth="5"
          strokeLinecap="round"
        />
        {/* Left stick — upper curve to form heart lobe */}
        <path
          d="M 22 52 Q 16 36 26 28 Q 36 20 44 30 L 50 40"
          stroke="url(#stickL)"
          strokeWidth="5"
          strokeLinecap="round"
          fill="none"
        />

        {/* Right stick body — diagonal right lobe */}
        <path
          d="M 50 85 L 78 52"
          stroke="url(#stickR)"
          strokeWidth="5"
          strokeLinecap="round"
        />
        {/* Right stick — upper curve to form heart lobe */}
        <path
          d="M 78 52 Q 84 36 74 28 Q 64 20 56 30 L 50 40"
          stroke="url(#stickR)"
          strokeWidth="5"
          strokeLinecap="round"
          fill="none"
        />

        {/* Bottom point of heart — the two sticks meet here, match-tip style */}
        <ellipse cx="50" cy="86" rx="3" ry="2" fill="#333" />

        {/* Left flame tip at top of left lobe */}
        <g filter="url(#fireGlow)">
          {/* Outer flame */}
          <path
            d="M 26 28 Q 20 18 24 8 Q 28 2 32 8 Q 38 16 34 22 Q 30 28 26 28 Z"
            fill="url(#fireL)"
            opacity="0.9"
          />
          {/* Inner flame core */}
          <path
            d="M 26 28 Q 23 22 25 14 Q 27 8 29 14 Q 31 20 28 26 Z"
            fill="#FFD700"
            opacity="0.8"
          />
          {/* Spark dot */}
          <circle cx="24" cy="9" r="1.5" fill="#FFFFFF" opacity="0.9" />
        </g>

        {/* Right flame tip at top of right lobe */}
        <g filter="url(#fireGlow)">
          {/* Outer flame */}
          <path
            d="M 74 28 Q 80 18 76 8 Q 72 2 68 8 Q 62 16 66 22 Q 70 28 74 28 Z"
            fill="url(#fireR)"
            opacity="0.9"
          />
          {/* Inner flame core */}
          <path
            d="M 74 28 Q 77 22 75 14 Q 73 8 71 14 Q 69 20 72 26 Z"
            fill="#FFD700"
            opacity="0.8"
          />
          {/* Spark dot */}
          <circle cx="76" cy="9" r="1.5" fill="#FFFFFF" opacity="0.9" />
        </g>

        {/* Glow effect around heart */}
        <path
          d="M 50 40 Q 44 30 36 22 Q 22 10 20 28 Q 18 40 28 52 L 50 85 L 72 52 Q 82 40 80 28 Q 78 10 64 22 Q 56 30 50 40 Z"
          fill="none"
          stroke="#FF4500"
          strokeWidth="0.5"
          opacity="0.3"
          filter="url(#glow)"
        />
      </svg>

      {showText && (
        <div className="text-center">
          <span
            className="font-bold tracking-widest uppercase"
            style={{
              fontSize: size * 0.2,
              background: "linear-gradient(135deg, #FF4500, #FF8C00, #FFD700)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              letterSpacing: "0.2em",
            }}
          >
            matches
          </span>
          <p className="text-match-muted text-xs tracking-widest mt-0.5" style={{ fontSize: size * 0.09 }}>
            find your flame
          </p>
        </div>
      )}
    </div>
  );
};
