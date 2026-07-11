export interface QuickBrief {
  titleCandidates: string[];
  summary: string;
  protagonist: string;
  genre: string;
  conflict: string;
  tone: string;
  sceneTitle: string;
  goal: string;
  turningPoint: string;
  ending: string;
  targetLength: string;
}

export function buildQuickBrief(
  idea: string,
  targetLength: string,
): QuickBrief {
  return {
    titleCandidates: ["未命名故事"],
    summary: idea.trim().slice(0, 160),
    protagonist: "由点子中的核心人物担任主角",
    genre: "",
    conflict: idea.trim(),
    tone: "紧凑、有画面感",
    sceneTitle: "开篇场景",
    goal: "让主角面对这个点子中的核心麻烦。",
    turningPoint: "出现改变主角判断的新信息。",
    ending: "保留余味但完成核心冲突",
    targetLength,
  };
}
