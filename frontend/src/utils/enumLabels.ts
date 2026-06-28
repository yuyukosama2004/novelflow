/**
 * 后端枚举值 → 中文显示映射。
 * 不修改后端 API/数据库枚举，仅在前端显示层做中文转换。
 */

// ── 项目状态 ──
export const PROJECT_STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  active: "进行中",
  archived: "已归档",
  completed: "已完成",
};

// ── 场景状态 ──
export const SCENE_STATUS_LABELS: Record<string, string> = {
  unplanned: "未规划",
  planned: "已规划",
  ready: "就绪",
  drafting: "撰写中",
  reviewing: "审查中",
  approved: "已批准",
  needs_revision: "需修订",
};

// ── 世界观正史状态 ──
export const CANON_STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  candidate: "候选",
  approved: "已确认",
  deprecated: "已废弃",
  conflicted: "冲突",
};

// ── 版本来源类型 ──
export const SOURCE_TYPE_LABELS: Record<string, string> = {
  human: "人工",
  ai_generated: "AI 生成",
  ai_revised: "AI 修订",
  human_revised: "人工修订",
  merged: "合并",
};

// ── 审查严重程度 ──
export const REVIEW_SEVERITY_LABELS: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
  blocking: "阻断",
};

// ── 审查问题状态 ──
export const ISSUE_STATUS_LABELS: Record<string, string> = {
  open: "未处理",
  accepted: "已接受",
  ignored: "已忽略",
  false_positive: "误报",
};

// ── 记忆候选状态 ──
export const MEMORY_CANDIDATE_STATUS_LABELS: Record<string, string> = {
  pending: "待确认",
  approved: "已批准",
  rejected: "已拒绝",
  conflicted: "冲突",
};

// ── 审查问题类型 ──
export const ISSUE_TYPE_LABELS: Record<string, string> = {
  knowledge_boundary: "知识边界",
  character_consistency: "人物一致性",
  injury_fact: "伤势事实",
  timeline: "时间线",
  deprecated_world: "已废弃世界观",
  forbidden_action: "禁止行为",
  must_not_reveal: "禁止泄露",
  missing_must_include: "缺少必须包含",
};

// ── 记忆候选类型 ──
export const CANDIDATE_TYPE_LABELS: Record<string, string> = {
  character_state: "人物状态",
  character_knowledge: "人物知识",
  timeline_event: "时间线事件",
  relationship_change: "关系变化",
  world_fact_update: "世界观更新",
};

// ── 辅助函数 ──

/** 安全取值，无映射时返回原值 */
export function label(
  map: Record<string, string>,
  key: string | undefined | null,
): string {
  if (!key) return "";
  return map[key] ?? key;
}
