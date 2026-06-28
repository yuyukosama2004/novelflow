import axios from "axios";

import type {
  Chapter,
  Character,
  HealthStatus,
  InterviewSession,
  MemoryCandidate,
  MemoryCandidateStatus,
  ModelTestResult,
  NovelProject,
  ProviderStatus,
  ReviewIssue,
  ReviewIssueStatus,
  Scene,
  SceneVersion,
  StoryCandidateEntity,
  Volume,
  WorldEntry,
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
  createProject: (
    payload: Partial<NovelProject> & { title: string },
  ) => unwrap<NovelProject>(api.post("/projects", payload)),
  getProject: (projectId: string) =>
    unwrap<NovelProject>(api.get(`/projects/${projectId}`)),
  patchProject: (
    projectId: string,
    payload: { title?: string; summary?: string; genre?: string; tone?: string },
  ) => unwrap<NovelProject>(api.patch(`/projects/${projectId}`, payload)),
  archiveProject: (projectId: string) =>
    unwrap<NovelProject>(api.delete(`/projects/${projectId}`)),

  listCharacters: (projectId: string) =>
    unwrap<Character[]>(
      api.get(`/projects/${projectId}/characters`),
    ),
  createCharacter: (
    projectId: string,
    payload: { name: string; role?: string },
  ) =>
    unwrap<Character>(
      api.post(`/projects/${projectId}/characters`, payload),
    ),
  patchCharacter: (
    characterId: string,
    payload: { name?: string; role?: string },
  ) =>
    unwrap<Character>(api.patch(`/characters/${characterId}`, payload)),
  deleteCharacter: (characterId: string) =>
    unwrap<{ deleted: boolean }>(
      api.delete(`/characters/${characterId}`),
    ),

  listWorldEntries: (projectId: string) =>
    unwrap<WorldEntry[]>(
      api.get(`/projects/${projectId}/world-entries`),
    ),
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
    payload: { name?: string; summary?: string; entry_type?: string },
  ) =>
    unwrap<WorldEntry>(api.patch(`/world-entries/${entryId}`, payload)),
  deleteWorldEntry: (entryId: string) =>
    unwrap<{ deleted: boolean }>(
      api.delete(`/world-entries/${entryId}`),
    ),

  listVolumes: (projectId: string) =>
    unwrap<Volume[]>(
      api.get(`/projects/${projectId}/volumes`),
    ),
  createVolume: (
    projectId: string,
    payload: { sequence_no: number; title: string },
  ) =>
    unwrap<Volume>(
      api.post(`/projects/${projectId}/volumes`, payload),
    ),
  patchVolume: (
    volumeId: string,
    payload: { title?: string; summary?: string; goal?: string },
  ) => unwrap<Volume>(api.patch(`/volumes/${volumeId}`, payload)),
  listChapters: (volumeId: string) =>
    unwrap<Chapter[]>(
      api.get(`/volumes/${volumeId}/chapters`),
    ),
  createChapter: (
    volumeId: string,
    payload: { sequence_no: number; title: string },
  ) =>
    unwrap<Chapter>(
      api.post(`/volumes/${volumeId}/chapters`, payload),
    ),
  patchChapter: (
    chapterId: string,
    payload: { title?: string; summary?: string; goal?: string },
  ) => unwrap<Chapter>(api.patch(`/chapters/${chapterId}`, payload)),
  listScenes: (chapterId: string) =>
    unwrap<Scene[]>(
      api.get(`/chapters/${chapterId}/scenes`),
    ),
  createScene: (
    chapterId: string,
    payload: { sequence_no: number; title: string },
  ) =>
    unwrap<Scene>(
      api.post(`/chapters/${chapterId}/scenes`, payload),
    ),
  getScene: (sceneId: string) =>
    unwrap<Scene>(api.get(`/scenes/${sceneId}`)),
  patchScene: (
    sceneId: string,
    payload: { title?: string; goal?: string; conflict?: string; time_text?: string },
  ) => unwrap<Scene>(api.patch(`/scenes/${sceneId}`, payload)),
  deleteScene: (sceneId: string) =>
    unwrap<{ deleted: boolean }>(api.delete(`/scenes/${sceneId}`)),
  getSceneContext: (sceneId: string) =>
    unwrap<Record<string, unknown>>(api.get(`/scenes/${sceneId}/context`)),

  listVersions: (sceneId: string) =>
    unwrap<SceneVersion[]>(
      api.get(`/scenes/${sceneId}/versions`),
    ),
  createVersion: (
    sceneId: string,
    payload: {
      content_markdown: string;
      summary?: string;
      source_type?: string;
      branch_name?: string;
      parent_version_id?: string | null;
    },
  ) =>
    unwrap<SceneVersion>(
      api.post(`/scenes/${sceneId}/versions`, payload),
    ),
  approveVersion: (sceneId: string, versionId: string) =>
    unwrap<Scene>(
      api.post(`/scenes/${sceneId}/approve-version`, {
        version_id: versionId,
      }),
    ),

  // Model APIs
  getProviders: () =>
    unwrap<ProviderStatus>(api.get("/model/providers")),
  testModel: (payload: { provider?: string; message?: string }) =>
    unwrap<ModelTestResult>(api.post("/model/test", payload)),
  // Review APIs
  runReview: (versionId: string) =>
    unwrap<ReviewIssue[]>(
      api.post(`/scene-versions/${versionId}/review`),
    ),
  listIssues: (versionId: string) =>
    unwrap<ReviewIssue[]>(
      api.get(`/scene-versions/${versionId}/issues`),
    ),
  updateIssue: (issueId: string, status: Exclude<ReviewIssueStatus, 'open'>) =>
    unwrap<ReviewIssue>(
      api.patch(`/issues/${issueId}`, { status }),
    ),

  // Memory APIs
  extractMemories: (versionId: string) =>
    unwrap<MemoryCandidate[]>(
      api.post(`/scene-versions/${versionId}/extract-memories`),
    ),
  listCandidates: (versionId: string) =>
    unwrap<MemoryCandidate[]>(
      api.get(`/scene-versions/${versionId}/candidates`),
    ),
  updateCandidate: (
    candidateId: string,
    status: Extract<MemoryCandidateStatus, 'approved' | 'rejected'>,
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
    unwrap<{ content: string; model: string; prompt_tokens: number; completion_tokens: number; finish_reason: string }>(
      api.post("/model/generate", payload),
    ),

  // Interview APIs
  startInterview: (projectId: string, entryType: string, title?: string) =>
    unwrap<InterviewSession>(
      api.post(`/projects/${projectId}/interview/start`, {
        entry_type: entryType,
        title: title ?? "",
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
      api.patch(`/candidates/${candidateId}`, payload),
    ),
  applyCandidate: (candidateId: string) =>
    unwrap<StoryCandidateEntity>(
      api.post(`/candidates/${candidateId}/apply`),
    ),
};

export function createSSEStream(
  sceneId: string,
  onChunk: (data: {
    run_id: string;
    content_delta: string;
    finish_reason: string | null;
    version?: SceneVersion;
    error?: string;
  }) => void,
  onDone: () => void,
  onError: (error: string) => void,
): AbortController {
  const controller = new AbortController();
  fetch(`${API_BASE_URL}/scenes/${sceneId}/generate`, {
    method: "POST",
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
