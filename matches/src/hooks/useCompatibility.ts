import { Answer, CompatibilityScore, UserProfile } from "../types";
import { loadQuestions } from "../components/QuestionnaireEditor";

function scoreAnswers(a: Answer[], b: Answer[]): CompatibilityScore {
  if (!Array.isArray(a) || !Array.isArray(b)) {
    return { userId: "", score: 0, matchedCategories: [], sharedValues: [] };
  }

  const QUESTIONS = loadQuestions();
  const bMap = new Map(b.map((ans) => [ans.questionId, ans.value]));
  let totalWeight = 0;
  let matchedWeight = 0;
  const matchedCategories = new Set<string>();
  const sharedValues: string[] = [];

  for (const ansA of a) {
    const ansB = bMap.get(ansA.questionId);
    if (ansB === undefined || ansB === null) continue;

    const question = QUESTIONS.find((q) => q.id === ansA.questionId);
    if (!question) continue;

    const w = question.weight;
    totalWeight += w;

    if (question.type === "single") {
      if (ansA.value === ansB) {
        matchedWeight += w;
        matchedCategories.add(question.category);
        sharedValues.push(String(ansA.value));
      }
    } else if (question.type === "multi") {
      const setA = new Set(ansA.value as string[]);
      const setB = new Set(ansB as string[]);
      const intersection = [...setA].filter((x) => setB.has(x));
      const union = new Set([...setA, ...setB]);
      const ratio = union.size > 0 ? intersection.length / union.size : 0;
      matchedWeight += w * ratio;
      if (ratio > 0.3) {
        matchedCategories.add(question.category);
        sharedValues.push(...intersection.slice(0, 2));
      }
    } else if (question.type === "scale") {
      const diff = Math.abs(Number(ansA.value) - Number(ansB));
      const similarity = Math.max(0, 1 - diff / 10);
      matchedWeight += w * similarity;
      if (similarity > 0.7) matchedCategories.add(question.category);
    }
  }

  const score = totalWeight > 0 ? Math.round((matchedWeight / totalWeight) * 100) : 0;

  return {
    userId: "",
    score,
    matchedCategories: [...matchedCategories],
    sharedValues: [...new Set(sharedValues)].slice(0, 5),
  };
}

export function calculateCompatibility(userAnswers: Answer[], otherProfile: UserProfile): CompatibilityScore {
  if (!otherProfile || !Array.isArray(otherProfile.answers)) {
    return { userId: otherProfile?.id ?? "", score: 0, matchedCategories: [], sharedValues: [] };
  }
  const result = scoreAnswers(userAnswers, otherProfile.answers);
  result.userId = otherProfile.id;
  return result;
}

export function getCompatibilityLabel(score: number): { label: string; color: string } {
  if (score >= 85) return { label: "Blazing Match", color: "#FF4500" };
  if (score >= 70) return { label: "Strong Spark", color: "#FF6A33" };
  if (score >= 55) return { label: "Warm Flame", color: "#FB923C" };
  if (score >= 40) return { label: "Ember", color: "#FDBA74" };
  return { label: "Distant Spark", color: "#8888aa" };
}
