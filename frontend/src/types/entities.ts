export interface EntityBase {
  id: string;
  created_at: string;
  updated_at: string;
}

export interface NovelProject extends EntityBase {
  title: string;
  summary: string;
  genre: string;
  theme_json: Record<string, unknown>;
  target_word_count: number | null;
  pov_type: string;
  tone: string;
  status: string;
  language: string;
  current_timeline_position: number;
}

export interface Character extends EntityBase {
  project_id: string;
  name: string;
  aliases_json: string[];
  role: string;
  age_text: string;
  appearance: string;
  background: string;
  public_identity: string;
  secret_identity: string;
  core_desire: string;
  core_fear: string;
  values_json: string[];
  decision_pattern: string;
  stress_response: string;
  speech_style: string;
  moral_boundaries_json: string[];
  ability_limits_json: Record<string, unknown>;
  forbidden_behaviors_json: string[];
  arc_plan: string;
  status: string;
  version: number;
}

export interface WorldEntry extends EntityBase {
  project_id: string;
  entry_type: string;
  name: string;
  summary: string;
  content: string;
  tags_json: string[];
  canon_status: string;
  version: number;
}

export interface Volume extends EntityBase {
  project_id: string;
  sequence_no: number;
  title: string;
  summary: string;
  goal: string;
  status: string;
}

export interface Chapter extends EntityBase {
  volume_id: string;
  sequence_no: number;
  title: string;
  summary: string;
  goal: string;
  status: string;
  approved_word_count: number;
}

export interface Scene extends EntityBase {
  chapter_id: string;
  sequence_no: number;
  title: string;
  pov_character_id: string | null;
  time_text: string;
  timeline_order: number;
  location_id: string | null;
  goal: string;
  conflict: string;
  turning_point: string;
  ending_hook: string;
  must_include_json: string[];
  must_not_reveal_json: string[];
  forbidden_actions_json: string[];
  status: string;
  approved_version_id: string | null;
}

export interface SceneVersion extends EntityBase {
  scene_id: string;
  version_no: number;
  parent_version_id: string | null;
  branch_name: string;
  content_markdown: string;
  summary: string;
  source_type: string;
  model_profile_id: string | null;
  prompt_snapshot_json: Record<string, unknown>;
  context_manifest_json: Record<string, unknown>;
  review_status: string;
  created_by: string;
}

export interface HealthStatus {
  status: string;
  database: string;
  version: string;
  models: Record<string, boolean>;
}

export interface ProviderStatus {
  models: Record<string, boolean>;
  default_provider: string;
}

export interface ModelTestResult {
  provider: string;
  connected: boolean;
  response: string;
  error: string;
}

export type ReviewIssueStatus = 'open' | 'accepted' | 'ignored' | 'false_positive';

export type ReviewRunStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface ReviewRun extends EntityBase {
  scene_version_id: string;
  model_profile_id: string | null;
  status: ReviewRunStatus;
  prompt_snapshot_json: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  summary: string;
}

export interface ReviewIssue extends EntityBase {
  review_run_id: string | null;
  scene_version_id: string;
  issue_type: string;
  severity: string;
  evidence_json: string;
  conflict_rule: string;
  suggestion: string;
  confidence: number;
  status: ReviewIssueStatus;
}

export interface ReviewResult {
  run: ReviewRun;
  issues: ReviewIssue[];
}

export type MemoryCandidateStatus = 'pending' | 'approved' | 'rejected' | 'conflicted';

export interface MemoryCandidate extends EntityBase {
  scene_version_id: string;
  candidate_type: string;
  target_entity_type: string;
  target_entity_id: string | null;
  content_json: Record<string, unknown>;
  evidence: string;
  confidence: number;
  status: MemoryCandidateStatus;
}

export interface SSEChunk {
  run_id: string;
  content_delta: string;
  finish_reason: string | null;
  version?: SceneVersion;
  error?: string;
}

// ── 访谈相关 ──

export interface InterviewMessage {
  role: string;
  content: string;
  timestamp?: string;
}

export interface InterviewSession {
  id: string;
  project_id: string;
  entry_type: string;
  title: string;
  status: string;
  messages: InterviewMessage[];
}

export type StoryCandidateType = 'project_setting' | 'character' | 'world_entry';
export type StoryCandidateStatus = 'pending' | 'approved' | 'rejected';

export interface StoryCandidateEntity {
  id: string;
  project_id: string;
  session_id: string;
  candidate_type: StoryCandidateType;
  title: string;
  content_json: Record<string, unknown>;
  proposal: string;
  confidence: number;
  status: StoryCandidateStatus;
  applied_entity_type: string | null;
  applied_entity_id: string | null;
  created_at: string;
  updated_at: string;
}

// ── 故事圣经 ──

// ── 模型配置 ──

export interface ModelProfile {
  id: string;
  name: string;
  provider: string;
  base_url: string;
  api_key_configured: boolean;
  model_name: string;
  temperature: number;
  max_output_tokens: number;
  timeout_seconds: number;
  is_default: boolean;
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface CharacterRelationship {
  id: string;
  project_id: string;
  character_a_id: string;
  character_b_id: string;
  relation_type: string;
  description: string;
  timeline_info: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
}
