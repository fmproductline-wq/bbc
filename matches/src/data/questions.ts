import { Question } from "../types";

export const QUESTIONS: Question[] = [
  // Lifestyle
  {
    id: "ls_1",
    category: "Lifestyle",
    text: "How would you describe your ideal weekend?",
    type: "single",
    options: ["Outdoors & adventure", "Cozy at home", "Social gatherings", "Exploring the city", "Mix of everything"],
    weight: 2,
  },
  {
    id: "ls_2",
    category: "Lifestyle",
    text: "What's your sleep schedule like?",
    type: "single",
    options: ["Early bird (before 10pm)", "Night owl (after midnight)", "Flexible", "Depends on the day"],
    weight: 1,
  },
  {
    id: "ls_3",
    category: "Lifestyle",
    text: "How important is physical fitness to you?",
    type: "scale",
    scaleMin: "Not at all",
    scaleMax: "Central to my life",
    weight: 2,
  },
  {
    id: "ls_4",
    category: "Lifestyle",
    text: "Where do you see yourself living long-term?",
    type: "single",
    options: ["Big city", "Suburbs", "Small town", "Rural / countryside", "Traveling / no fixed place"],
    weight: 3,
  },

  // Values & Beliefs
  {
    id: "vb_1",
    category: "Values",
    text: "What values matter most to you?",
    type: "multi",
    options: ["Honesty", "Loyalty", "Ambition", "Kindness", "Freedom", "Family", "Spirituality", "Humor"],
    weight: 3,
  },
  {
    id: "vb_2",
    category: "Values",
    text: "How important is spirituality or religion in your life?",
    type: "scale",
    scaleMin: "Not at all",
    scaleMax: "Very important",
    weight: 2,
  },
  {
    id: "vb_3",
    category: "Values",
    text: "How do you feel about having children?",
    type: "single",
    options: ["I want children", "I don't want children", "I'm open to it", "I already have children", "Undecided"],
    weight: 3,
  },
  {
    id: "vb_4",
    category: "Values",
    text: "How do you approach money and finances?",
    type: "single",
    options: ["Saver — security first", "Spender — enjoy life now", "Balanced approach", "Investor mindset", "Still figuring it out"],
    weight: 2,
  },

  // Personality
  {
    id: "pn_1",
    category: "Personality",
    text: "In social settings, you tend to be:",
    type: "single",
    options: ["The life of the party", "Observer who opens up slowly", "Comfortable in small groups", "One-on-one conversations only", "Varies entirely by mood"],
    weight: 2,
  },
  {
    id: "pn_2",
    category: "Personality",
    text: "When facing conflict, you typically:",
    type: "single",
    options: ["Address it head-on immediately", "Reflect first then discuss", "Avoid it and hope it passes", "Seek outside perspective", "Depends on the situation"],
    weight: 2,
  },
  {
    id: "pn_3",
    category: "Personality",
    text: "How do you recharge after a long week?",
    type: "single",
    options: ["Alone time — no people", "Low-key time with close friends", "Going out and being social", "Creative projects", "Physical activity"],
    weight: 2,
  },
  {
    id: "pn_4",
    category: "Personality",
    text: "Your decision-making style is:",
    type: "single",
    options: ["Logic and data", "Gut feeling / intuition", "Pros and cons list", "Ask everyone I trust", "Impulsive then reflect"],
    weight: 1,
  },

  // Interests
  {
    id: "in_1",
    category: "Interests",
    text: "Which of these interests do you have?",
    type: "multi",
    options: ["Music", "Art / design", "Sports", "Gaming", "Cooking", "Reading", "Film / TV", "Tech", "Nature", "Travel", "Fashion", "Writing"],
    weight: 2,
  },
  {
    id: "in_2",
    category: "Interests",
    text: "How important is it that a partner shares your interests?",
    type: "scale",
    scaleMin: "Not important",
    scaleMax: "Very important",
    weight: 2,
  },

  // Relationship Needs
  {
    id: "rn_1",
    category: "Relationship",
    text: "What kind of connection are you looking for?",
    type: "single",
    options: ["Deep emotional bond", "Casual friendship that could grow", "Long-term partnership", "Intellectual companionship", "I'm open to whatever develops"],
    weight: 3,
  },
  {
    id: "rn_2",
    category: "Relationship",
    text: "How much personal space do you need in a relationship?",
    type: "scale",
    scaleMin: "I love being together constantly",
    scaleMax: "I need a lot of alone time",
    weight: 3,
  },
  {
    id: "rn_3",
    category: "Relationship",
    text: "What's your primary love language?",
    type: "single",
    options: ["Words of affirmation", "Acts of service", "Receiving gifts", "Quality time", "Physical touch"],
    weight: 2,
  },
  {
    id: "rn_4",
    category: "Relationship",
    text: "How do you feel about long-distance?",
    type: "single",
    options: ["Open to it", "Only temporary", "Prefer proximity", "Depends on the connection", "Not for me"],
    weight: 2,
  },

  // Communication
  {
    id: "cm_1",
    category: "Communication",
    text: "Your communication style is best described as:",
    type: "single",
    options: ["Direct and straightforward", "Thoughtful and measured", "Expressive and emotional", "Humorous and light", "Listener more than talker"],
    weight: 2,
  },
  {
    id: "cm_2",
    category: "Communication",
    text: "How often do you prefer to communicate with someone you care about?",
    type: "single",
    options: ["Constantly throughout the day", "Check in morning and night", "When something comes up", "Deep talks a few times a week", "Minimal — value quality over quantity"],
    weight: 2,
  },
];

export const CATEGORIES = [...new Set(QUESTIONS.map((q) => q.category))];
