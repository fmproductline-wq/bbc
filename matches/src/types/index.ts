export type PrivacyLevel = "public" | "private" | "matches_only";

export interface Answer {
  questionId: string;
  value: string | string[] | number;
}

export interface UserProfile {
  id: string;
  qrCode: string; // unique identifier used as QR data
  displayName: string; // nickname only, no real name
  bio: string;
  answers: Answer[];
  privacy: {
    bio: PrivacyLevel;
    answers: PrivacyLevel;
    onlineStatus: PrivacyLevel;
    lastSeen: PrivacyLevel;
  };
  createdAt: number;
  isOnline: boolean;
  lastSeen: number;
}

export interface CompatibilityScore {
  userId: string;
  score: number; // 0-100
  matchedCategories: string[];
  sharedValues: string[];
}

export interface Message {
  id: string;
  senderId: string;
  content: string;
  type: "text" | "qr_reveal" | "system" | "compatibility_invite";
  timestamp: number;
  read: boolean;
}

export interface Conversation {
  id: string;
  participantIds: string[];
  messages: Message[];
  compatibilityScore: number;
  qrRevealed: { [userId: string]: boolean };
  status: "pending" | "active" | "revealed";
  createdAt: number;
  lastMessageAt: number;
}

export interface Notification {
  id: string;
  type: "new_match" | "message" | "qr_reveal" | "compatibility_update";
  title: string;
  body: string;
  timestamp: number;
  read: boolean;
  data?: Record<string, string>;
}

export type Screen =
  | "splash"
  | "onboarding"
  | "questionnaire"
  | "home"
  | "chat"
  | "profile"
  | "settings"
  | "notifications"
  | "match_detail";

export interface Question {
  id: string;
  category: string;
  text: string;
  type: "single" | "multi" | "scale" | "text";
  options?: string[];
  scaleMin?: string;
  scaleMax?: string;
  weight: number; // importance for matching 1-3
}
