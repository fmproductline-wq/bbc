import React, { useState, useEffect, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";
import {
  Screen,
  UserProfile,
  Conversation,
  Message,
  Notification,
  Answer,
} from "./types";
import { SplashScreen } from "./components/SplashScreen";
import { Onboarding } from "./components/Onboarding";
import { Questionnaire } from "./components/Questionnaire";
import { ChatList } from "./components/ChatList";
import { ChatScreen } from "./components/ChatScreen";
import { ProfileScreen } from "./components/ProfileScreen";
import { SettingsScreen } from "./components/SettingsScreen";
import { NotificationsScreen } from "./components/NotificationsScreen";
import { QuestionnaireEditor, loadQuestions } from "./components/QuestionnaireEditor";
import { AdminGate, isAdminUnlocked } from "./components/AdminGate";
import { MyQuestions } from "./components/MyQuestions";
import { calculateCompatibility } from "./hooks/useCompatibility";

// Simulated other users the bot will match against
const SIMULATED_PROFILES: Omit<UserProfile, "id" | "qrCode" | "createdAt">[] = [
  {
    displayName: "Ember",
    bio: "Lover of late nights and good conversations.",
    isOnline: true,
    lastSeen: Date.now(),
    personalQuestions: [],
    privacy: { bio: "public", answers: "matches_only", onlineStatus: "public", lastSeen: "public" },
    answers: [
      { questionId: "ls_1", value: "Cozy at home" },
      { questionId: "ls_2", value: "Night owl (after midnight)" },
      { questionId: "ls_3", value: 7 },
      { questionId: "ls_4", value: "Big city" },
      { questionId: "vb_1", value: ["Honesty", "Humor", "Kindness"] },
      { questionId: "vb_2", value: 3 },
      { questionId: "vb_3", value: "I'm open to it" },
      { questionId: "vb_4", value: "Balanced approach" },
      { questionId: "pn_1", value: "Observer who opens up slowly" },
      { questionId: "pn_2", value: "Reflect first then discuss" },
      { questionId: "pn_3", value: "Alone time — no people" },
      { questionId: "pn_4", value: "Gut feeling / intuition" },
      { questionId: "in_1", value: ["Music", "Reading", "Film / TV", "Cooking"] },
      { questionId: "in_2", value: 6 },
      { questionId: "rn_1", value: "Deep emotional bond" },
      { questionId: "rn_2", value: 7 },
      { questionId: "rn_3", value: "Quality time" },
      { questionId: "rn_4", value: "Prefer proximity" },
      { questionId: "cm_1", value: "Thoughtful and measured" },
      { questionId: "cm_2", value: "Check in morning and night" },
    ],
  },
  {
    displayName: "Blaze",
    bio: "Always chasing the next adventure.",
    isOnline: false,
    lastSeen: Date.now() - 3600000,
    personalQuestions: [],
    privacy: { bio: "public", answers: "public", onlineStatus: "public", lastSeen: "public" },
    answers: [
      { questionId: "ls_1", value: "Outdoors & adventure" },
      { questionId: "ls_2", value: "Early bird (before 10pm)" },
      { questionId: "ls_3", value: 9 },
      { questionId: "ls_4", value: "Rural / countryside" },
      { questionId: "vb_1", value: ["Ambition", "Freedom", "Loyalty"] },
      { questionId: "vb_2", value: 2 },
      { questionId: "vb_3", value: "I don't want children" },
      { questionId: "vb_4", value: "Investor mindset" },
      { questionId: "pn_1", value: "The life of the party" },
      { questionId: "pn_2", value: "Address it head-on immediately" },
      { questionId: "pn_3", value: "Physical activity" },
      { questionId: "pn_4", value: "Logic and data" },
      { questionId: "in_1", value: ["Sports", "Travel", "Tech"] },
      { questionId: "in_2", value: 4 },
      { questionId: "rn_1", value: "Long-term partnership" },
      { questionId: "rn_2", value: 5 },
      { questionId: "rn_3", value: "Acts of service" },
      { questionId: "rn_4", value: "Depends on the connection" },
      { questionId: "cm_1", value: "Direct and straightforward" },
      { questionId: "cm_2", value: "When something comes up" },
    ],
  },
  {
    displayName: "Spark",
    bio: "Art, coffee, and meaningful silences.",
    isOnline: true,
    lastSeen: Date.now(),
    personalQuestions: [],
    privacy: { bio: "public", answers: "matches_only", onlineStatus: "matches_only", lastSeen: "private" },
    answers: [
      { questionId: "ls_1", value: "Exploring the city" },
      { questionId: "ls_2", value: "Flexible" },
      { questionId: "ls_3", value: 5 },
      { questionId: "ls_4", value: "Big city" },
      { questionId: "vb_1", value: ["Kindness", "Honesty", "Loyalty", "Humor"] },
      { questionId: "vb_2", value: 4 },
      { questionId: "vb_3", value: "Undecided" },
      { questionId: "vb_4", value: "Balanced approach" },
      { questionId: "pn_1", value: "Comfortable in small groups" },
      { questionId: "pn_2", value: "Reflect first then discuss" },
      { questionId: "pn_3", value: "Creative projects" },
      { questionId: "pn_4", value: "Gut feeling / intuition" },
      { questionId: "in_1", value: ["Art / design", "Music", "Film / TV", "Writing", "Cooking"] },
      { questionId: "in_2", value: 7 },
      { questionId: "rn_1", value: "Deep emotional bond" },
      { questionId: "rn_2", value: 6 },
      { questionId: "rn_3", value: "Words of affirmation" },
      { questionId: "rn_4", value: "Prefer proximity" },
      { questionId: "cm_1", value: "Expressive and emotional" },
      { questionId: "cm_2", value: "Deep talks a few times a week" },
    ],
  },
];

function createProfile(data: Omit<UserProfile, "id" | "qrCode" | "createdAt">): UserProfile {
  const id = uuidv4();
  return { ...data, id, qrCode: `MATCHES:${id.slice(0, 6).toUpperCase()}`, createdAt: Date.now() };
}

const STORAGE_KEY = "matches_app_state";

interface AppState {
  currentUser: UserProfile | null;
  conversations: Conversation[];
  notifications: Notification[];
  otherProfiles: UserProfile[];
}

function loadState(): AppState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { currentUser: null, conversations: [], notifications: [], otherProfiles: [] };
}

function saveState(state: AppState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {}
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("splash");
  const [state, setState] = useState<AppState>(loadState);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [editingAnswers, setEditingAnswers] = useState(false);

  const { currentUser, conversations, notifications, otherProfiles } = state;

  const updateState = useCallback((patch: Partial<AppState>) => {
    setState((prev) => {
      const next = { ...prev, ...patch };
      saveState(next);
      return next;
    });
  }, []);

  // Init simulated profiles once
  useEffect(() => {
    if (state.otherProfiles.length === 0) {
      updateState({ otherProfiles: SIMULATED_PROFILES.map(createProfile) });
    }
  }, []);

  // After splash, decide where to go
  const handleSplashComplete = () => {
    if (currentUser && currentUser.answers.length > 0) {
      setScreen("home");
    } else if (currentUser) {
      setScreen("questionnaire");
    } else {
      setScreen("onboarding");
    }
  };

  const handleOnboardingComplete = (profile: UserProfile) => {
    updateState({ currentUser: profile });
    setScreen("questionnaire");
  };

  const handleQuestionnaireComplete = (answers: Answer[]) => {
    if (!currentUser) return;
    const updated = { ...currentUser, answers };
    updateState({ currentUser: updated });

    // Trigger bot matching after a short delay
    setTimeout(() => runBotMatching(updated), 1500);
    setScreen("home");
  };

  const runBotMatching = (user: UserProfile) => {
    const profiles = state.otherProfiles.length > 0 ? state.otherProfiles : SIMULATED_PROFILES.map(createProfile);
    const existingPartners = new Set(
      conversations.flatMap((c) => c.participantIds.filter((id) => id !== user.id))
    );

    const newConvs: Conversation[] = [];
    const newNotifs: Notification[] = [];

    for (const other of profiles) {
      if (existingPartners.has(other.id)) continue;
      const compat = calculateCompatibility(user.answers, other);
      if (compat.score < 50) continue;

      const convId = uuidv4();
      const systemMsg: Message = {
        id: uuidv4(),
        senderId: "bot",
        content: `🔥 Matches bot found a ${compat.score}% compatibility! You both share: ${compat.sharedValues.slice(0, 3).join(", ") || compat.matchedCategories.join(", ")}. Start a conversation!`,
        type: "compatibility_invite",
        timestamp: Date.now(),
        read: false,
      };

      newConvs.push({
        id: convId,
        participantIds: [user.id, other.id],
        messages: [systemMsg],
        compatibilityScore: compat.score,
        qrRevealed: {},
        status: "active",
        createdAt: Date.now(),
        lastMessageAt: Date.now(),
      });

      newNotifs.push({
        id: uuidv4(),
        type: "new_match",
        title: "New compatibility match! 🔥",
        body: `You have a ${compat.score}% match. Shared values: ${compat.sharedValues.slice(0, 2).join(", ") || "multiple categories"}.`,
        timestamp: Date.now(),
        read: false,
        data: { conversationId: convId },
      });
    }

    if (newConvs.length > 0) {
      setState((prev) => {
        const next = {
          ...prev,
          conversations: [...prev.conversations, ...newConvs],
          notifications: [...prev.notifications, ...newNotifs],
          otherProfiles: profiles,
        };
        saveState(next);
        return next;
      });
    }
  };

  const handleSendMessage = (convId: string, content: string, type: Message["type"] = "text") => {
    const msg: Message = {
      id: uuidv4(),
      senderId: currentUser!.id,
      content,
      type,
      timestamp: Date.now(),
      read: false,
    };

    setState((prev) => {
      const next = {
        ...prev,
        conversations: prev.conversations.map((c) =>
          c.id === convId
            ? { ...c, messages: [...c.messages, msg], lastMessageAt: Date.now() }
            : c
        ),
      };
      saveState(next);
      return next;
    });

    // Simulate reply after 2-4 seconds
    if (type === "text") {
      const conv = conversations.find((c) => c.id === convId);
      if (!conv) return;
      const otherId = conv.participantIds.find((id) => id !== currentUser!.id);
      const other = otherProfiles.find((p) => p.id === otherId);
      if (!other) return;

      const replies = [
        "That's really interesting to me too!",
        "I feel the same way honestly.",
        "Ha, I wasn't expecting that answer but I like it.",
        "Tell me more about that?",
        "I've been thinking about something similar lately.",
        "Glad the bot connected us — this feels promising 🔥",
        "What made you choose that answer in the questionnaire?",
      ];

      setTimeout(() => {
        const reply: Message = {
          id: uuidv4(),
          senderId: other.id,
          content: replies[Math.floor(Math.random() * replies.length)],
          type: "text",
          timestamp: Date.now(),
          read: false,
        };
        setState((prev) => {
          const next = {
            ...prev,
            conversations: prev.conversations.map((c) =>
              c.id === convId
                ? { ...c, messages: [...c.messages, reply], lastMessageAt: Date.now() }
                : c
            ),
            notifications: [
              ...prev.notifications,
              {
                id: uuidv4(),
                type: "message" as const,
                title: `New message`,
                body: reply.content,
                timestamp: Date.now(),
                read: false,
                data: { conversationId: convId },
              },
            ],
          };
          saveState(next);
          return next;
        });
      }, 1500 + Math.random() * 2000);
    }
  };

  const handleRevealQR = (convId: string) => {
    if (!currentUser) return;
    setState((prev) => {
      const next = {
        ...prev,
        conversations: prev.conversations.map((c) =>
          c.id === convId
            ? { ...c, qrRevealed: { ...c.qrRevealed, [currentUser.id]: true }, status: "revealed" as const }
            : c
        ),
      };
      saveState(next);
      return next;
    });

    // Other user reveals after a moment too
    setTimeout(() => {
      const conv = conversations.find((c) => c.id === convId);
      if (!conv) return;
      const otherId = conv.participantIds.find((id) => id !== currentUser.id)!;
      setState((prev) => {
        const next = {
          ...prev,
          conversations: prev.conversations.map((c) =>
            c.id === convId
              ? { ...c, qrRevealed: { ...c.qrRevealed, [otherId]: true } }
              : c
          ),
          notifications: [
            ...prev.notifications,
            {
              id: uuidv4(),
              type: "qr_reveal" as const,
              title: "They revealed their QR! 🔓",
              body: "Your match shared their QR identity back.",
              timestamp: Date.now(),
              read: false,
              data: { conversationId: convId },
            },
          ],
        };
        saveState(next);
        return next;
      });
    }, 3000 + Math.random() * 5000);
  };

  const handleMarkRead = (convId: string) => {
    setState((prev) => {
      const next = {
        ...prev,
        conversations: prev.conversations.map((c) =>
          c.id === convId
            ? { ...c, messages: c.messages.map((m) => ({ ...m, read: true })) }
            : c
        ),
      };
      saveState(next);
      return next;
    });
  };

  const profilesMap = new Map(otherProfiles.map((p) => [p.id, p]));

  const activeConv = activeChatId ? conversations.find((c) => c.id === activeChatId) : null;
  const activeOther = activeConv
    ? profilesMap.get(activeConv.participantIds.find((id) => id !== currentUser?.id) || "")
    : null;

  if (screen === "splash") return <SplashScreen onComplete={handleSplashComplete} />;
  if (screen === "onboarding") return <Onboarding onComplete={handleOnboardingComplete} />;
  if (screen === "questionnaire" || editingAnswers) {
    return (
      <Questionnaire
        existingAnswers={currentUser?.answers}
        onComplete={(answers) => {
          setEditingAnswers(false);
          handleQuestionnaireComplete(answers);
        }}
      />
    );
  }

  if (screen === "profile") {
    return (
      <ProfileScreen
        profile={currentUser!}
        onBack={() => setScreen("home")}
        onEditQuestionnaire={() => setEditingAnswers(true)}
        onOpenMyQuestions={() => setScreen("my_questions")}
      />
    );
  }

  if (screen === "settings") {
    return (
      <SettingsScreen
        profile={currentUser!}
        onBack={() => setScreen("home")}
        onUpdatePrivacy={(privacy) => {
          updateState({ currentUser: { ...currentUser!, privacy } });
        }}
        onDeleteAccount={() => {
          localStorage.removeItem(STORAGE_KEY);
          setState({ currentUser: null, conversations: [], notifications: [], otherProfiles: [] });
          setScreen("onboarding");
        }}
        onOpenEditor={() => setScreen("admin_gate")}
        onOpenMyQuestions={() => setScreen("my_questions")}
      />
    );
  }

  if (screen === "admin_gate") {
    if (isAdminUnlocked()) {
      return <QuestionnaireEditor onBack={() => setScreen("settings")} />;
    }
    return (
      <AdminGate
        onUnlocked={() => setScreen("questionnaire_editor")}
        onBack={() => setScreen("settings")}
      />
    );
  }

  if (screen === "questionnaire_editor") {
    return <QuestionnaireEditor onBack={() => setScreen("settings")} />;
  }

  if (screen === "my_questions") {
    return (
      <MyQuestions
        questions={currentUser?.personalQuestions || []}
        onSave={(personalQuestions) => {
          updateState({ currentUser: { ...currentUser!, personalQuestions } });
        }}
        onBack={() => setScreen("settings")}
      />
    );
  }

  if (screen === "notifications") {
    return (
      <NotificationsScreen
        notifications={notifications}
        onBack={() => setScreen("home")}
        onMarkAllRead={() =>
          updateState({ notifications: notifications.map((n) => ({ ...n, read: true })) })
        }
        onTapNotification={(notif) => {
          updateState({ notifications: notifications.map((n) => n.id === notif.id ? { ...n, read: true } : n) });
          if (notif.data?.conversationId) {
            setActiveChatId(notif.data.conversationId);
            setScreen("chat");
          }
        }}
      />
    );
  }

  if (screen === "chat" && activeConv && activeOther && currentUser) {
    return (
      <ChatScreen
        conversation={activeConv}
        currentUser={currentUser}
        otherUser={activeOther}
        onBack={() => setScreen("home")}
        onSendMessage={handleSendMessage}
        onRevealQR={handleRevealQR}
        onMarkRead={handleMarkRead}
      />
    );
  }

  return (
    <ChatList
      conversations={conversations}
      profiles={profilesMap}
      currentUserId={currentUser?.id || ""}
      notifications={notifications}
      onOpenChat={(id) => { setActiveChatId(id); setScreen("chat"); }}
      onOpenProfile={() => setScreen("profile")}
      onOpenNotifications={() => setScreen("notifications")}
      onOpenSettings={() => setScreen("settings")}
    />
  );
}
