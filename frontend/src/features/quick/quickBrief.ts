export interface QuickBrief {
  protagonist: string;
  conflict: string;
  tone: string;
  ending: string;
  targetLength: string;
}

export function buildQuickBrief(idea: string, targetLength: string): QuickBrief {
  return {
    protagonist: '由点子中的核心人物担任主角',
    conflict: idea.trim(),
    tone: '紧凑、有画面感',
    ending: '保留余味但完成核心冲突',
    targetLength,
  };
}
