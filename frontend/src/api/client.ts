import axios from "axios";

import type {
  Chapter,
  Character,
  CharacterRelationship,
  HealthStatus,
  ImpactReport,
  InterviewSession,
  MemoryCandidate,
  MemoryExtractionResult,
  MemoryExtractionRun,
  ModelProfile,
  MemoryCandidateStatus,
  ModelTestResult,
  NovelProject,
  ProviderStatus,
  ReviewIssue,
  ReviewIssueStatus,
  ReviewResult,
  ReviewRun,
  Scene,
  SceneContextLinks,
  SceneVersion,
  SceneWorkingDraft,
  StoryCandidateEntity,
  Volume,
  WorldEntry,
  WorkflowRun,
} from "../types/entities";

interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
  request_id: string;
}

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 12000,
});

async function unwrap<T>(
  promise: Promise<{ data: ApiEnvelope<T> }>,
): Promise<T> {
  const response = await promise;
  return response.data.data;
}

export const apiClient = {
  health: () => unwrap<HealthStatus>(api.get("/health")),

  listProjects: () => unwrap<NovelProject[]>(api.get("/projects")),
  createProject: (payload: Partial<NovelProject> & { title: string }) =>
    unwrap<NovelProject>(api.post("/projects", payload)),
  planQuickCreation: (payload: {
    idea: string;
    target_length: string;
    draft_kind: "opening" | "short";
    model_profile_id?: string;
  }) =>
    unwrap<{
      title_candidates: string[];
      summary: string;
      protagonist: string;
      genre: string;
      tone: string;
      scene: {
        title: string;
        goal: string;
        conflict: string;
        turning_point: string;
        ending_hook: string;
      };
    }>(api.post("/quick-creation/plan", payload)),
  getProject: (projectId: string) =>
    unwrap<NovelProject>(api.get(`/projects/${projectId}`)),
  patchProject: (
    projectId: string,
    payload: {
      title?: string;
      summary?: string;
      genre?: string;
      tone?: string;
      pov_type?: string;
      writing_style_preset?: string;
      writing_style_custom?: string;
      default_scene_word_count?: number;
      default_model_profile_id?: string | null;
    },
  ) => unwrap<NovelProject>(api.patch(`/projects/${projectId}`, payload)),
  archiveProject: (projectId: string) =>
    unwrap<NovelProject>(api.delete(`/projects/${projectId}`)),

  listCharacters: (projectId: string) =>
    unwrap<Character[]>(api.get(`/projects/${projectId}/characters`)),
  createCharacter: (
    projectId: string,
    payload: { name: string; role?: string },
  ) =>
    unwrap<Character>(api.post(`/projects/${projectId}/characters`, payload)),
  patchCharacter: (characterId: string, payload: Record<string, unknown>) =>
    unwrap<Character>(api.patch(`/characters/${characterId}`, payload)),
  deleteCharacter: (characterId: string) =>
    unwrap<{ deleted: boolean }>(api.delete(`/characters/${characterId}`)),

  listWorldEntries: (projectId: string) =>
    unwrap<WorldEntry[]>(api.get(`/projects/${projectId}/world-entries`)),
  createWorldEntry: (
    projectId: string,
    payload: {
      name: string;
      entry_type?: string;
      canon_status?: string;
      summary?: string;
    },
  ) =>
    unwrap<WorldEntry>(
      api.post(`/projects/${projectId}/world-entries`, payload),
    ),
  approveWorldEntry: (entryId: string) =>
    unwrap<WorldEntry>(api.post(`/world-entries/${entryId}/approve`)),
  patchWorldEntry: (
    entryId: string,
    payload: {
      name?: string;
      summary?: string;
      entry_type?: string;
      content?: string;
    },
  ) => unwrap<WorldEntry>(api.patch(`/world-entries/${entryId}`, payload)),
  deleteWorldEntry: (entryId: string) =>
    unwrap<{ deleted: boolean }>(api.delete(`/world-entries/${entryId}`)),

  listVolumes: (projectId: string) =>
    unwrap<Volume[]>(api.get(`/projects/${projectId}/volumes`)),
  createVolume: (
    projectId: string,
    payload: { sequence_no: number; title: string },
  ) => unwrap<Volume>(api.post(`/projects/${projectId}/volumes`, payload)),
  patchVolume: (
    volumeId: string,
    payload: { title?: string; summary?: string; goal?: string },
  ) => unwrap<Volume>(api.patch(`/volumes/${volumeId}`, payload)),
  listChapters: (volumeId: string) =>
    unwrap<Chapter[]>(api.get(`/volumes/${volumeId}/chapters`)),
  createChapter: (
    volumeId: string,
    payload: { sequence_no: number; title: string },
  ) => unwrap<Chapter>(api.post(`/volumes/${volumeId}/chapters`, payload)),
  patchChapter: (
    chapterId: string,
    payload: { title?: string; summary?: string; goal?: string },
  ) => unwrap<Chapter>(api.patch(`/chapters/${chapterId}`, payload)),
  listScenes: (chapterId: string) =>
    unwrap<Scene[]>(api.get(`/chapters/${chapterId}/scenes`)),
  createScene: (
    chapterId: string,
    payload: {
      sequence_no: number;
      title: string;
      pov_character_id?: string | null;
      time_text?: string;
      goal?: string;
      conflict?: string;
      turning_point?: string;
      ending_hook?: string;
    },
  ) => unwrap<Scene>(api.post(`/chapters/${chapterId}/scenes`, payload)),
  getScene: (sceneId: string) => unwrap<Scene>(api.get(`/scenes/${sceneId}`)),
  patchScene: (
    sceneId: string,
    payload: {
      title?: string;
      goal?: string;
      conflict?: string;
      turning_point?: string;
      ending_hook?: string;
      time_text?: string;
      story_time_order?: number;
    },
  ) => unwrap<Scene>(api.patch(`/scenes/${sceneId}`, payload)),
  deleteScene: (sceneId: string) =>
    unwrap<{ deleted: boolean }>(api.delete(`/scenes/${sceneId}`)),
  getSceneContext: (sceneId: string) =>
    unwrap<Record<string, unknown>>(api.get(`/scenes/${sceneId}/context`)),
  getSceneContextLinks: (sceneId: string) =>
    unwrap<SceneContextLinks>(api.get(`/scenes/${sceneId}/context-links`)),
  replaceSceneContextLinks: (sceneId: string, payload: SceneContextLinks) =>
    unwrap<SceneContextLinks>(
      api.put(`/scenes/${sceneId}/context-links`, payload),
    ),
  completeScene: (sceneId: string) =>
    unwrap<Scene>(api.post(`/scenes/${sceneId}/complete`)),
  clearSceneStale: (sceneId: string) =>
    unwrap<Scene>(api.post(`/scenes/${sceneId}/clear-stale`)),
  listImpactReports: (projectId: string) =>
    unwrap<ImpactReport[]>(api.get(`/projects/${projectId}/impact-reports`)),
  updateImpactReport: (reportId: string, status: "acknowledged" | "resolved") =>
    unwrap<ImpactReport>(api.patch(`/impact-reports/${reportId}`, { status })),
  listWorkflowRuns: (sceneId: string) =>
    unwrap<WorkflowRun[]>(api.get(`/scenes/${sceneId}/workflow-runs`)),
  cancelWorkflowRun: (runId: string) =>
    unwrap<WorkflowRun>(api.post(`/workflows/runs/${runId}/cancel`)),

  listVersions: (sceneId: string) =>
    unwrap<SceneVersion[]>(api.get(`/scenes/${sceneId}/versions`)),
  generateVersionSummary: (versionId: string) =>
    unwrap<SceneVersion>(
      api.post(`/scene-versions/${versionId}/generate-summary`),
    ),
  createVersion: (
    sceneId: string,
    payload: {
      content_markdown: string;
      content_json?: Record<string, unknown>;
      summary?: string;
      source_type?: string;
      branch_name?: string;
      parent_version_id?: string | null;
    },
  ) => unwrap<SceneVersion>(api.post(`/scenes/${sceneId}/versions`, payload)),
  getWorkingDraft: (sceneId: string) =>
    unwrap<SceneWorkingDraft>(api.get(`/scenes/${sceneId}/working-draft`)),
  updateWorkingDraft: (
    sceneId: string,
    payload: {
      revision: number;
      content_json: Record<string, unknown>;
      content_markdown: string;
    },
  ) =>
    unwrap<SceneWorkingDraft>(
      api.put(`/scenes/${sceneId}/working-draft`, payload),
    ),
  approveVersion: (
    sceneId: string,
    versionId: string,
    overrideReason?: string,
  ) =>
    unwrap<Scene>(
      api.post(`/scenes/${sceneId}/approve-version`, {
        version_id: versionId,
        override_reason: overrideReason,
      }),
    ),

  // Model APIs
  getProviders: () => unwrap<ProviderStatus>(api.get("/model/providers")),
  testModel: (payload: { provider?: string; message?: string }) =>
    unwrap<ModelTestResult>(api.post("/model/test", payload)),
  // Review APIs
  runReview: (versionId: string, modelProfileId?: string) =>
    unwrap<ReviewResult>(
      api.post(`/scene-versions/${versionId}/review`, {
        model_profile_id: modelProfileId || null,
      }),
    ),
  listReviewRuns: (versionId: string) =>
    unwrap<ReviewRun[]>(api.get(`/scene-versions/${versionId}/review-runs`)),
  getReviewRun: (runId: string) =>
    unwrap<ReviewResult>(api.get(`/review-runs/${runId}`)),
  listIssues: (versionId: string) =>
    unwrap<ReviewIssue[]>(api.get(`/scene-versions/${versionId}/issues`)),
  updateIssue: (issueId: string, status: Exclude<ReviewIssueStatus, "open">) =>
    unwrap<ReviewIssue>(api.patch(`/issues/${issueId}`, { status })),

  // Memory APIs
  extractMemories: (versionId: string, modelProfileId?: string) =>
    unwrap<MemoryExtractionResult>(
      api.post(`/scene-versions/${versionId}/extract-memories`, {
        model_profile_id: modelProfileId || null,
      }),
    ),
  listMemoryExtractionRuns: (versionId: string) =>
    unwrap<MemoryExtractionRun[]>(
      api.get(`/scene-versions/${versionId}/memory-extraction-runs`),
    ),
  listCandidates: (versionId: string) =>
    unwrap<MemoryCandidate[]>(
      api.get(`/scene-versions/${versionId}/candidates`),
    ),
  updateCandidate: (
    candidateId: string,
    status: Extract<MemoryCandidateStatus, "approved" | "rejected">,
    contentJson?: Record<string, unknown>,
  ) =>
    unwrap<MemoryCandidate>(
      api.patch(`/candidates/${candidateId}`, {
        status,
        content_json: contentJson ?? null,
      }),
    ),

  generateText: (payload: {
    provider?: string;
    model?: string;
    messages: { role: string; content: string }[];
    max_tokens?: number;
    temperature?: number;
  }) =>
    unwrap<{
      content: string;
      model: string;
      prompt_tokens: number;
      completion_tokens: number;
      finish_reason: string;
    }>(api.post("/model/generate", payload)),

  // Interview APIs
  startInterview: (
    projectId: string,
    entryType: string,
    title?: string,
    modelProfileId?: string,
  ) =>
    unwrap<InterviewSession>(
      api.post(`/projects/${projectId}/interview/start`, {
        entry_type: entryType,
        title: title ?? "",
        model_profile_id: modelProfileId || null,
      }),
    ),
  sendInterviewMessage: (sessionId: string, content: string) =>
    unwrap<InterviewSession>(
      api.post(`/sessions/${sessionId}/message`, { content }),
    ),
  getInterviewSession: (sessionId: string) =>
    unwrap<InterviewSession>(api.get(`/sessions/${sessionId}`)),
  extractStoryCandidates: (sessionId: string) =>
    unwrap<StoryCandidateEntity[]>(
      api.post(`/sessions/${sessionId}/extract-candidates`),
    ),
  listStoryCandidates: (sessionId: string) =>
    unwrap<StoryCandidateEntity[]>(
      api.get(`/sessions/${sessionId}/candidates`),
    ),
  updateStoryCandidate: (
    candidateId: string,
    payload: { status?: string; content_json?: Record<string, unknown> },
  ) =>
    unwrap<StoryCandidateEntity>(
      api.patch(`/story-candidates/${candidateId}`, payload),
    ),
  applyCandidate: (candidateId: string) =>
    unwrap<StoryCandidateEntity>(
      api.post(`/story-candidates/${candidateId}/apply`),
    ),

  // Persistent project / scene discussion. Suggestions remain candidates until applied.
  listCreativeDiscussions: (projectId: string, sceneId?: string) =>
    unwrap<InterviewSession[]>(
      api.get(`/projects/${projectId}/creative-discussions`, {
        params: sceneId ? { scene_id: sceneId } : {},
      }),
    ),
  startCreativeDiscussion: (
    projectId: string,
    payload: { scene_id?: string; model_profile_id?: string },
  ) =>
    unwrap<InterviewSession>(
      api.post(`/projects/${projectId}/creative-discussions/start`, payload),
    ),

  // Bible / Relationship APIs
  createRelationship: (
    projectId: string,
    payload: {
      character_a_id: string;
      character_b_id: string;
      relation_type?: string;
      description?: string;
      timeline_info?: string;
    },
  ) =>
    unwrap<CharacterRelationship>(
      api.post(`/projects/${projectId}/relationships`, payload),
    ),
  listRelationships: (projectId: string) =>
    unwrap<CharacterRelationship[]>(
      api.get(`/projects/${projectId}/relationships`),
    ),
  patchRelationship: (
    relationshipId: string,
    payload: {
      relation_type?: string;
      description?: string;
      timeline_info?: string;
    },
  ) =>
    unwrap<CharacterRelationship>(
      api.patch(`/relationships/${relationshipId}`, payload),
    ),
  deleteRelationship: (relationshipId: string) =>
    unwrap<{ deleted: boolean }>(
      api.delete(`/relationships/${relationshipId}`),
    ),

  // Existing list/get endpoints exposed clearly
  getCharacter: (characterId: string) =>
    unwrap<Character>(api.get(`/characters/${characterId}`)),
  getWorldEntry: (entryId: string) =>
    unwrap<WorldEntry>(api.get(`/world-entries/${entryId}`)),

  // Model Profile APIs
  listModelProfiles: () => unwrap<ModelProfile[]>(api.get("/model/profiles")),
  createModelProfile: (payload: Record<string, unknown>) =>
    unwrap<ModelProfile>(api.post("/model/profiles", payload)),
  patchModelProfile: (id: string, payload: Record<string, unknown>) =>
    unwrap<ModelProfile>(api.patch(`/model/profiles/${id}`, payload)),
  deleteModelProfile: (id: string) =>
    unwrap<{ deleted: boolean }>(api.delete(`/model/profiles/${id}`)),
  clearModelProfileApiKey: (id: string) =>
    unwrap<ModelProfile>(api.delete(`/model/profiles/${id}/api-key`)),
  testModelProfile: (id: string) =>
    unwrap<{
      connected: boolean;
      provider: string;
      model: string;
      error?: string;
    }>(api.post(`/model/profiles/${id}/test`)),
  listProviderModels: (provider: string) =>
    unwrap<{ provider: string; models: string[] }>(
      api.get(`/model/providers/${provider}/models`),
    ),

  // Outline APIs
  generateOutline: (projectId: string, modelProfileId?: string) =>
    unwrap<
      {
        sequence_no: number;
        title: string;
        summary: string;
        goal: string;
        chapters: {
          sequence_no: number;
          title: string;
          summary: string;
          goal: string;
          scenes: {
            sequence_no: number;
            title: string;
            goal: string;
            conflict: string;
            turning_point: string;
            ending_hook: string;
          }[];
        }[];
      }[]
    >(
      api.post(`/projects/${projectId}/generate-outline`, {
        model_profile_id: modelProfileId || null,
      }),
    ),
  applyOutline: (projectId: string, outline: Record<string, unknown>[]) =>
    unwrap<Record<string, number>>(
      api.post(`/projects/${projectId}/apply-outline`, { outline }),
    ),
};

export function createSSEStream(
  sceneId: string,
  payload: {
    modelProfileId?: string;
    generationMode: "new" | "rewrite" | "polish";
    instruction: string;
    baseContent: string;
    targetWordCount: number;
  },
  onChunk: (data: {
    run_id: string;
    content_delta: string;
    finish_reason: string | null;
    version?: SceneVersion;
    error?: string;
    perspective_warning?: string;
  }) => void,
  onDone: () => void,
  onError: (error: string) => void,
): AbortController {
  const controller = new AbortController();
  fetch(`${API_BASE_URL}/scenes/${sceneId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model_profile_id: payload.modelProfileId || null,
      generation_mode: payload.generationMode,
      instruction: payload.instruction,
      base_content: payload.baseContent,
      target_word_count: payload.targetWordCount,
    }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        onError(`HTTP ${response.status}`);
        return;
      }
      const reader = response.body?.getReader();
      if (!reader) {
        onError("No readable stream");
        return;
      }
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            if (dataStr === "[DONE]") {
              onDone();
              return;
            }
            try {
              const data = JSON.parse(dataStr);
              onChunk(data);
            } catch {
              // skip unparseable lines
            }
          }
        }
      }
      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message);
      }
    });

  return controller;
}
