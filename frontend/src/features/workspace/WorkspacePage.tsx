import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BookMarked,
  Check,
  CirclePlus,
  Globe2,
  Maximize2,
  Minimize2,
  Pencil,
  Trash2,
  UserPlus,
  X,
} from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { API_BASE_URL, apiClient } from "../../api/client";
import { IconButton } from "../../components/IconButton";
import { ModelSelector } from "../../components/ModelSelector";
import { StatusPill } from "../../components/StatusPill";
import type {
  Chapter,
  Scene,
  SceneVersion,
  Volume,
} from "../../types/entities";
import { label, PROJECT_STATUS_LABELS } from "../../utils/enumLabels";
import { MemoryCandidatePanel } from "./MemoryCandidatePanel";
import { ReviewIssuePanel } from "./ReviewIssuePanel";
import { SceneCardEditor } from "./SceneCardEditor";
import { SceneApprovalPanel } from "./SceneApprovalPanel";
import { SceneEditor } from "./SceneEditor";
import { WritingAssistant } from "./WritingAssistant";
import { CreativeDiscussionPanel } from "./CreativeDiscussionPanel";
import { WritingSettingsPanel } from "./WritingSettingsPanel";
import { SceneVersionSelector } from "./SceneVersionSelector";
import { WorkspaceShell } from "./WorkspaceShell";
import {
  getDefaultSceneVersionId,
  resolveSceneVersionSelection,
} from "./sceneVersionSelection";
import ContextChecker from "./ContextChecker";
import SceneGenerationPanel from "../workflows/SceneGenerationPanel";
import {
  WorkspacePanelTabs,
  type WorkspacePanelTab,
} from "./WorkspacePanelTabs";

function nextSequence<T extends { sequence_no: number }>(
  items: T[] | undefined,
): number {
  return (
    (items?.reduce((max, item) => Math.max(max, item.sequence_no), 0) ?? 0) + 1
  );
}

type WritingFont = "sans" | "serif";
type WritingSize = "small" | "medium" | "large" | "xlarge";
type WritingSpacing = "compact" | "comfortable" | "relaxed";
type WritingWidth = "narrow" | "standard" | "wide";

interface WritingPreferences {
  font: WritingFont;
  size: WritingSize;
  spacing: WritingSpacing;
  width: WritingWidth;
}

const WRITING_PREFERENCES_KEY = "novelflow:writing-preferences";
const DEFAULT_WRITING_PREFERENCES: WritingPreferences = {
  font: "sans",
  size: "medium",
  spacing: "comfortable",
  width: "standard",
};

function loadWritingPreferences(): WritingPreferences {
  try {
    const stored = JSON.parse(
      window.localStorage.getItem(WRITING_PREFERENCES_KEY) ?? "{}",
    ) as Partial<WritingPreferences>;
    return {
      font: stored.font === "serif" ? "serif" : "sans",
      size: ["small", "medium", "large", "xlarge"].includes(stored.size ?? "")
        ? (stored.size as WritingSize)
        : DEFAULT_WRITING_PREFERENCES.size,
      spacing: ["compact", "comfortable", "relaxed"].includes(
        stored.spacing ?? "",
      )
        ? (stored.spacing as WritingSpacing)
        : DEFAULT_WRITING_PREFERENCES.spacing,
      width: ["narrow", "standard", "wide"].includes(stored.width ?? "")
        ? (stored.width as WritingWidth)
        : DEFAULT_WRITING_PREFERENCES.width,
    };
  } catch {
    return DEFAULT_WRITING_PREFERENCES;
  }
}

export function WorkspacePage() {
  const { projectId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const isQuickEntry = searchParams.get("entry") === "quick";
  const queryClient = useQueryClient();
  const [selectedVolumeId, setSelectedVolumeId] = useState<string>("");
  const [selectedChapterId, setSelectedChapterId] = useState<string>("");
  const [selectedSceneId, setSelectedSceneId] = useState<string>("");
  const [selectedSceneVersionId, setSelectedSceneVersionId] =
    useState<string>("");
  const [pendingSceneVersionId, setPendingSceneVersionId] =
    useState<string>("");
  const [
    hasExplicitSceneVersionSelection,
    setHasExplicitSceneVersionSelection,
  ] = useState(false);
  const [characterName, setCharacterName] = useState("");
  const [worldName, setWorldName] = useState("");
  const [sceneTitle, setSceneTitle] = useState("");

  // 编辑状态
  const [editingProject, setEditingProject] = useState(false);
  const [projectTitle, setProjectTitle] = useState("");
  const [editingCharacterId, setEditingCharacterId] = useState<string | null>(
    null,
  );
  const [editingCharacterName, setEditingCharacterName] = useState("");
  const [editingCharacterRole, setEditingCharacterRole] = useState("");
  const [editingWorldId, setEditingWorldId] = useState<string | null>(null);
  const [editingWorldName, setEditingWorldName] = useState("");
  const [editingWorldSummary, setEditingWorldSummary] = useState("");
  const [editingVolumeId, setEditingVolumeId] = useState<string | null>(null);
  const [editingVolumeTitle, setEditingVolumeTitle] = useState("");
  const [editingChapterId, setEditingChapterId] = useState<string | null>(null);
  const [editingChapterTitle, setEditingChapterTitle] = useState("");
  const [editingSceneId, setEditingSceneId] = useState<string | null>(null);
  const [editingSceneTitle, setEditingSceneTitle] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const [modelProfileId, setModelProfileId] = useState("");
  const [rightTab, setRightTab] = useState<WorkspacePanelTab>("ai");
  const [focusMode, setFocusMode] = useState(false);
  const [writingPreferences, setWritingPreferences] =
    useState<WritingPreferences>(loadWritingPreferences);
  const [editorContent, setEditorContent] = useState("");
  const [discussionInstruction, setDiscussionInstruction] = useState("");

  useEffect(() => {
    window.localStorage.setItem(
      WRITING_PREFERENCES_KEY,
      JSON.stringify(writingPreferences),
    );
  }, [writingPreferences]);

  // ── 数据查询 ──
  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => apiClient.getProject(projectId),
    enabled: Boolean(projectId),
  });
  const characters = useQuery({
    queryKey: ["characters", projectId],
    queryFn: () => apiClient.listCharacters(projectId),
    enabled: Boolean(projectId),
  });
  const worldEntries = useQuery({
    queryKey: ["world", projectId],
    queryFn: () => apiClient.listWorldEntries(projectId),
    enabled: Boolean(projectId),
  });
  const impactReports = useQuery({
    queryKey: ["impact-reports", projectId],
    queryFn: () => apiClient.listImpactReports(projectId),
    enabled: Boolean(projectId),
  });
  const acknowledgeImpact = useMutation({
    mutationFn: (reportId: string) =>
      apiClient.updateImpactReport(reportId, "acknowledged"),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["impact-reports", projectId],
      }),
  });
  const volumes = useQuery({
    queryKey: ["volumes", projectId],
    queryFn: () => apiClient.listVolumes(projectId),
    enabled: Boolean(projectId),
  });
  const chapters = useQuery({
    queryKey: ["chapters", selectedVolumeId],
    queryFn: () => apiClient.listChapters(selectedVolumeId),
    enabled: Boolean(selectedVolumeId),
  });
  const scenes = useQuery({
    queryKey: ["scenes", selectedChapterId],
    queryFn: () => apiClient.listScenes(selectedChapterId),
    enabled: Boolean(selectedChapterId),
  });
  const scene = useQuery({
    queryKey: ["scene", selectedSceneId],
    queryFn: () => apiClient.getScene(selectedSceneId),
    enabled: Boolean(selectedSceneId),
  });
  const sceneVersions = useQuery({
    queryKey: ["scene-versions", selectedSceneId],
    queryFn: () => apiClient.listVersions(selectedSceneId),
    enabled: Boolean(selectedSceneId),
  });

  useEffect(() => {
    if (project.data?.default_model_profile_id) {
      setModelProfileId(project.data.default_model_profile_id);
    }
  }, [project.data?.default_model_profile_id]);

  // ── 级联默认选择 ──
  useEffect(() => {
    if (!selectedVolumeId && volumes.data?.[0]) {
      setSelectedVolumeId(volumes.data[0].id);
    }
  }, [selectedVolumeId, volumes.data]);

  useEffect(() => {
    if (!selectedChapterId && chapters.data?.[0]) {
      setSelectedChapterId(chapters.data[0].id);
    }
  }, [chapters.data, selectedChapterId]);

  useEffect(() => {
    if (!selectedSceneId && scenes.data?.[0]) {
      setSelectedSceneId(scenes.data[0].id);
    }
  }, [scenes.data, selectedSceneId]);

  const defaultSceneVersionId = useMemo(
    () =>
      getDefaultSceneVersionId(
        sceneVersions.data ?? [],
        scene.data?.approved_version_id,
      ),
    [scene.data?.approved_version_id, sceneVersions.data],
  );

  useEffect(() => {
    setSelectedSceneVersionId("");
    setPendingSceneVersionId("");
    setHasExplicitSceneVersionSelection(false);
  }, [selectedSceneId]);

  useEffect(() => {
    if (!selectedSceneId) {
      setSelectedSceneVersionId("");
      setPendingSceneVersionId("");
      setHasExplicitSceneVersionSelection(false);
      return;
    }
    const nextSelection = resolveSceneVersionSelection({
      versions: sceneVersions.data ?? [],
      defaultVersionId: defaultSceneVersionId,
      selectedVersionId: selectedSceneVersionId,
      pendingVersionId: pendingSceneVersionId,
      hasExplicitSelection: hasExplicitSceneVersionSelection,
    });
    if (nextSelection.selectedVersionId !== selectedSceneVersionId) {
      setSelectedSceneVersionId(nextSelection.selectedVersionId);
    }
    if (nextSelection.pendingVersionId !== pendingSceneVersionId) {
      setPendingSceneVersionId(nextSelection.pendingVersionId);
    }
    if (
      nextSelection.hasExplicitSelection !== hasExplicitSceneVersionSelection
    ) {
      setHasExplicitSceneVersionSelection(nextSelection.hasExplicitSelection);
    }
  }, [
    defaultSceneVersionId,
    hasExplicitSceneVersionSelection,
    pendingSceneVersionId,
    sceneVersions.data,
    selectedSceneId,
    selectedSceneVersionId,
  ]);

  const handleVersionSelectionChange = useCallback((versionId: string) => {
    setPendingSceneVersionId("");
    setHasExplicitSceneVersionSelection(true);
    setSelectedSceneVersionId(versionId);
  }, []);

  const handleVersionCreated = useCallback(
    (version?: SceneVersion) => {
      if (version?.id) {
        setPendingSceneVersionId(version.id);
      }
      queryClient.invalidateQueries({
        queryKey: ["scene-versions", selectedSceneId],
      });
      if (version?.id && isQuickEntry) {
        void apiClient
          .runReview(version.id, modelProfileId || undefined)
          .then(() => {
            queryClient.invalidateQueries({
              queryKey: ["scene-versions", selectedSceneId],
            });
            queryClient.invalidateQueries({
              queryKey: ["review-runs", version.id],
            });
          })
          .catch(() => undefined);
      }
    },
    [isQuickEntry, modelProfileId, queryClient, selectedSceneId],
  );

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    queryClient.invalidateQueries({ queryKey: ["characters", projectId] });
    queryClient.invalidateQueries({ queryKey: ["world", projectId] });
    queryClient.invalidateQueries({ queryKey: ["volumes", projectId] });
    queryClient.invalidateQueries({ queryKey: ["chapters", selectedVolumeId] });
    queryClient.invalidateQueries({ queryKey: ["scenes", selectedChapterId] });
  };

  // ── 创建操作 ──
  const createCharacter = useMutation({
    mutationFn: () =>
      apiClient.createCharacter(projectId, {
        name: characterName,
        role: "角色",
      }),
    onSuccess: () => {
      setCharacterName("");
      queryClient.invalidateQueries({ queryKey: ["characters", projectId] });
    },
  });
  const createWorld = useMutation({
    mutationFn: () =>
      apiClient.createWorldEntry(projectId, {
        name: worldName,
        entry_type: "custom",
        canon_status: "draft",
      }),
    onSuccess: () => {
      setWorldName("");
      queryClient.invalidateQueries({ queryKey: ["world", projectId] });
    },
  });
  const createVolume = useMutation({
    mutationFn: () =>
      apiClient.createVolume(projectId, {
        sequence_no: nextSequence(volumes.data),
        title: `第${nextSequence(volumes.data)} 卷`,
      }),
    onSuccess: (volume: Volume) => {
      setSelectedVolumeId(volume.id);
      setSelectedChapterId("");
      setSelectedSceneId("");
      queryClient.invalidateQueries({ queryKey: ["volumes", projectId] });
    },
  });
  const createChapter = useMutation({
    mutationFn: () =>
      apiClient.createChapter(selectedVolumeId, {
        sequence_no: nextSequence(chapters.data),
        title: `第${nextSequence(chapters.data)} 章`,
      }),
    onSuccess: (chapter: Chapter) => {
      setSelectedChapterId(chapter.id);
      setSelectedSceneId("");
      queryClient.invalidateQueries({
        queryKey: ["chapters", selectedVolumeId],
      });
    },
  });
  const createScene = useMutation({
    mutationFn: () =>
      apiClient.createScene(selectedChapterId, {
        sequence_no: nextSequence(scenes.data),
        title: sceneTitle || `场景 ${nextSequence(scenes.data)}`,
      }),
    onSuccess: (createdScene: Scene) => {
      setSceneTitle("");
      setSelectedSceneId(createdScene.id);
      queryClient.invalidateQueries({
        queryKey: ["scenes", selectedChapterId],
      });
    },
  });

  // ── 编辑/删除操作 ──
  const saveProject = useMutation({
    mutationFn: () =>
      apiClient.patchProject(projectId, { title: projectTitle }),
    onSuccess: () => {
      setEditingProject(false);
      invalidateAll();
    },
  });
  const archiveProject = useMutation({
    mutationFn: () => apiClient.archiveProject(projectId),
    onSuccess: () => invalidateAll(),
  });

  const saveCharacter = useMutation({
    mutationFn: () =>
      apiClient.patchCharacter(editingCharacterId!, {
        name: editingCharacterName,
        role: editingCharacterRole,
      }),
    onSuccess: () => {
      setEditingCharacterId(null);
      queryClient.invalidateQueries({ queryKey: ["characters", projectId] });
    },
  });
  const deleteCharacter = useMutation({
    mutationFn: (id: string) => apiClient.deleteCharacter(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["characters", projectId] }),
  });

  const saveWorld = useMutation({
    mutationFn: () =>
      apiClient.patchWorldEntry(editingWorldId!, {
        name: editingWorldName,
        summary: editingWorldSummary,
      }),
    onSuccess: () => {
      setEditingWorldId(null);
      queryClient.invalidateQueries({ queryKey: ["world", projectId] });
    },
  });
  const deleteWorld = useMutation({
    mutationFn: (id: string) => apiClient.deleteWorldEntry(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["world", projectId] }),
  });

  const saveVolume = useMutation({
    mutationFn: () =>
      apiClient.patchVolume(editingVolumeId!, { title: editingVolumeTitle }),
    onSuccess: () => {
      setEditingVolumeId(null);
      queryClient.invalidateQueries({ queryKey: ["volumes", projectId] });
    },
  });
  const saveChapter = useMutation({
    mutationFn: () =>
      apiClient.patchChapter(editingChapterId!, { title: editingChapterTitle }),
    onSuccess: () => {
      setEditingChapterId(null);
      queryClient.invalidateQueries({
        queryKey: ["chapters", selectedVolumeId],
      });
    },
  });
  const saveScene = useMutation({
    mutationFn: () =>
      apiClient.patchScene(editingSceneId!, { title: editingSceneTitle }),
    onSuccess: () => {
      setEditingSceneId(null);
      queryClient.invalidateQueries({
        queryKey: ["scenes", selectedChapterId],
      });
    },
  });
  const removeScene = useMutation({
    mutationFn: (id: string) => apiClient.deleteScene(id),
    onSuccess: () => {
      if (selectedSceneId) {
        setSelectedSceneId("");
      }
      queryClient.invalidateQueries({
        queryKey: ["scenes", selectedChapterId],
      });
    },
  });

  const sortedVolumes = useMemo(
    () =>
      [...(volumes.data ?? [])].sort((a, b) => a.sequence_no - b.sequence_no),
    [volumes.data],
  );

  if (!projectId) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100">
        <p className="text-slate-500">未找到项目</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-stone-50 text-stone-800">
      <header className="border-b border-stone-200 bg-white/95 shadow-sm">
        <div className="mx-auto flex max-w-[1800px] flex-wrap items-start justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="min-w-0">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm text-stone-500 transition hover:text-brand-800"
            >
              <ArrowLeft size={15} />
              返回项目列表
            </Link>
            <div className="mt-1 flex items-center gap-3">
              {editingProject ? (
                <div className="flex items-center gap-2">
                  <input
                    value={projectTitle}
                    onChange={(e) => setProjectTitle(e.target.value)}
                    className="min-w-0 rounded-md border border-slate-300 px-3 py-1 text-xl font-semibold outline-none focus:border-emerald-600"
                    autoFocus
                  />
                  <IconButton
                    icon={<Check size={15} />}
                    label="保存"
                    tone="primary"
                    onClick={() => saveProject.mutate()}
                    disabled={saveProject.isPending}
                  />
                  <IconButton
                    icon={<X size={15} />}
                    label="取消"
                    onClick={() => setEditingProject(false)}
                  />
                </div>
              ) : (
                <>
                  <h1 className="truncate text-xl font-semibold text-stone-950">
                    {project.data?.title ?? "加载中…"}
                  </h1>
                  <button
                    onClick={() => {
                      setProjectTitle(project.data?.title ?? "");
                      setEditingProject(true);
                    }}
                    className="rounded p-1 text-stone-400 transition hover:bg-stone-100 hover:text-stone-600"
                    title="编辑项目"
                  >
                    <Pencil size={14} />
                  </button>
                </>
              )}
            </div>
            {project.data ? (
              <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                <span className="rounded-full bg-brand-50 px-2 py-1 text-brand-700">
                  {project.data.pov_type === "first_person"
                    ? "第一人称"
                    : project.data.pov_type === "third_person_omniscient"
                      ? "第三人称全知"
                      : "第三人称限知"}
                </span>
                <span className="rounded-full bg-amber-50 px-2 py-1 text-amber-800">
                  {project.data.writing_style_preset === "light_novel"
                    ? "轻小说"
                    : project.data.writing_style_preset === "male_web"
                      ? "男频成长冒险"
                      : project.data.writing_style_preset === "female_web"
                        ? "女频情感成长"
                        : project.data.writing_style_preset === "suspense"
                          ? "悬疑推理"
                          : project.data.writing_style_preset === "literary"
                            ? "文学现实主义"
                            : project.data.writing_style_preset === "historical"
                              ? "古风历史"
                              : project.data.writing_style_preset === "scifi"
                                ? "科幻幻想"
                                : project.data.writing_style_preset === "custom"
                                  ? "自定义文风"
                                  : "通用网络小说"}
                </span>
                <span className="rounded-full bg-stone-100 px-2 py-1 text-stone-600">
                  单场目标 {project.data.default_scene_word_count} 字
                </span>
              </div>
            ) : null}
          </div>
          <div className="flex max-w-full flex-wrap items-center justify-end gap-2">
            <StatusPill tone="ok">
              {label(PROJECT_STATUS_LABELS, project.data?.status)}
            </StatusPill>
            <ModelSelector
              selectedId={modelProfileId}
              onChange={setModelProfileId}
            />
            <button
              onClick={() => setFocusMode((value) => !value)}
              className="flex items-center gap-1 rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm text-stone-600 shadow-sm transition hover:bg-stone-50"
            >
              {focusMode ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
              {focusMode ? "退出专注" : "专注写作"}
            </button>
            <Link
              to={`/projects/${projectId}/bible`}
              className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm font-medium text-amber-800 shadow-sm transition hover:bg-amber-50"
            >
              故事圣经
            </Link>
            <Link
              to={`/projects/${projectId}/wizard`}
              className="rounded-lg border border-brand-200 bg-white px-3 py-2 text-sm font-medium text-brand-700 shadow-sm transition hover:bg-brand-50"
            >
              创作向导
            </Link>
            <a
              href={`${API_BASE_URL}/projects/${projectId}/exports/markdown`}
              className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm font-medium text-stone-700 shadow-sm transition hover:border-brand-300 hover:bg-brand-50"
            >
              导出 Markdown
            </a>
            <button
              onClick={() => {
                if (
                  confirm("确定要归档此项目吗？归档后仍可在项目列表中查看。")
                ) {
                  archiveProject.mutate();
                }
              }}
              className="rounded-lg border border-rose-200 bg-white px-3 py-2 text-sm font-medium text-rose-700 shadow-sm transition hover:bg-rose-50"
            >
              归档
            </button>
          </div>
        </div>
      </header>

      <WorkspaceShell
        focusMode={focusMode}
        left={
          <>
            {/* ── 左侧栏：大纲 + 设定库 ── */}
            <aside className={`space-y-4 ${focusMode ? "hidden" : ""}`}>
              {/* 大纲 */}
              <section className="rounded-md border border-slate-200 bg-white">
                <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2">
                  <h2 className="text-sm font-semibold text-slate-900">大纲</h2>
                  <div className="flex gap-2">
                    <IconButton
                      icon={<CirclePlus size={15} />}
                      label="新建卷"
                      onClick={() => createVolume.mutate()}
                      disabled={createVolume.isPending}
                    />
                    <IconButton
                      icon={<BookMarked size={15} />}
                      label="新建章"
                      onClick={() => createChapter.mutate()}
                      disabled={!selectedVolumeId || createChapter.isPending}
                    />
                  </div>
                </div>
                <div className="max-h-[420px] overflow-auto p-2">
                  {sortedVolumes.map((volume) => (
                    <div key={volume.id} className="mb-2">
                      {/* 卷标题行 */}
                      {editingVolumeId === volume.id ? (
                        <div className="flex items-center gap-1 px-2 py-1">
                          <input
                            value={editingVolumeTitle}
                            onChange={(e) =>
                              setEditingVolumeTitle(e.target.value)
                            }
                            className="min-w-0 flex-1 rounded border border-slate-300 px-2 py-1 text-sm outline-none focus:border-emerald-600"
                            autoFocus
                          />
                          <button
                            onClick={() => saveVolume.mutate()}
                            disabled={saveVolume.isPending}
                            className="rounded p-1 text-emerald-600 hover:bg-emerald-50"
                            title="保存"
                          >
                            <Check size={14} />
                          </button>
                          <button
                            onClick={() => setEditingVolumeId(null)}
                            className="rounded p-1 text-slate-400 hover:bg-slate-100"
                            title="取消"
                          >
                            <X size={14} />
                          </button>
                        </div>
                      ) : (
                        <div className="group flex items-center gap-1">
                          <button
                            onClick={() => {
                              setSelectedVolumeId(volume.id);
                              setSelectedChapterId("");
                              setSelectedSceneId("");
                            }}
                            className={`flex-1 rounded-md px-3 py-2 text-left text-sm font-medium ${
                              selectedVolumeId === volume.id
                                ? "bg-emerald-50 text-emerald-800"
                                : "text-slate-700"
                            }`}
                          >
                            {volume.sequence_no}. {volume.title}
                          </button>
                          <button
                            onClick={() => {
                              setEditingVolumeId(volume.id);
                              setEditingVolumeTitle(volume.title);
                            }}
                            className="hidden rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 group-hover:inline-flex"
                            title="编辑卷名"
                          >
                            <Pencil size={12} />
                          </button>
                        </div>
                      )}
                      {/* 章列表 */}
                      {selectedVolumeId === volume.id ? (
                        <div className="ml-3 mt-1 space-y-1 border-l border-slate-200 pl-2">
                          {chapters.data?.map((chapter) => (
                            <div key={chapter.id}>
                              {editingChapterId === chapter.id ? (
                                <div className="flex items-center gap-1 px-1 py-1">
                                  <input
                                    value={editingChapterTitle}
                                    onChange={(e) =>
                                      setEditingChapterTitle(e.target.value)
                                    }
                                    className="min-w-0 flex-1 rounded border border-slate-300 px-2 py-1 text-sm outline-none focus:border-emerald-600"
                                    autoFocus
                                  />
                                  <button
                                    onClick={() => saveChapter.mutate()}
                                    disabled={saveChapter.isPending}
                                    className="rounded p-1 text-emerald-600 hover:bg-emerald-50"
                                    title="保存"
                                  >
                                    <Check size={14} />
                                  </button>
                                  <button
                                    onClick={() => setEditingChapterId(null)}
                                    className="rounded p-1 text-slate-400 hover:bg-slate-100"
                                    title="取消"
                                  >
                                    <X size={14} />
                                  </button>
                                </div>
                              ) : (
                                <div className="group flex items-center gap-1">
                                  <button
                                    onClick={() => {
                                      setSelectedChapterId(chapter.id);
                                      setSelectedSceneId("");
                                    }}
                                    className={`flex-1 rounded-md px-2 py-1.5 text-left text-sm ${
                                      selectedChapterId === chapter.id
                                        ? "bg-amber-50 text-amber-900"
                                        : "text-slate-600"
                                    }`}
                                  >
                                    {chapter.sequence_no}. {chapter.title}
                                  </button>
                                  <button
                                    onClick={() => {
                                      setEditingChapterId(chapter.id);
                                      setEditingChapterTitle(chapter.title);
                                    }}
                                    className="hidden rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 group-hover:inline-flex"
                                    title="编辑章名"
                                  >
                                    <Pencil size={12} />
                                  </button>
                                </div>
                              )}
                              {/* 场景列表 */}
                              {selectedChapterId === chapter.id ? (
                                <div className="ml-2 mt-1 space-y-1">
                                  {scenes.data?.map((item) => (
                                    <div
                                      key={item.id}
                                      className="group flex items-center gap-1"
                                    >
                                      {editingSceneId === item.id ? (
                                        <div className="flex flex-1 items-center gap-1 px-1 py-1">
                                          <input
                                            value={editingSceneTitle}
                                            onChange={(e) =>
                                              setEditingSceneTitle(
                                                e.target.value,
                                              )
                                            }
                                            className="min-w-0 flex-1 rounded border border-slate-300 px-2 py-1 text-sm outline-none focus:border-emerald-600"
                                            autoFocus
                                          />
                                          <button
                                            onClick={() => saveScene.mutate()}
                                            disabled={saveScene.isPending}
                                            className="rounded p-1 text-emerald-600 hover:bg-emerald-50"
                                            title="保存"
                                          >
                                            <Check size={14} />
                                          </button>
                                          <button
                                            onClick={() =>
                                              setEditingSceneId(null)
                                            }
                                            className="rounded p-1 text-slate-400 hover:bg-slate-100"
                                            title="取消"
                                          >
                                            <X size={14} />
                                          </button>
                                        </div>
                                      ) : (
                                        <button
                                          onClick={() =>
                                            setSelectedSceneId(item.id)
                                          }
                                          className={`flex-1 rounded-md px-2 py-1.5 text-left text-sm ${
                                            selectedSceneId === item.id
                                              ? "bg-slate-900 text-white"
                                              : "text-slate-600 hover:bg-slate-50"
                                          }`}
                                        >
                                          {item.sequence_no}. {item.title}
                                          {item.is_stale ? (
                                            <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] text-amber-800">
                                              需复查
                                            </span>
                                          ) : null}
                                        </button>
                                      )}
                                      {selectedSceneId !== item.id && (
                                        <>
                                          <button
                                            onClick={() => {
                                              setEditingSceneId(item.id);
                                              setEditingSceneTitle(item.title);
                                            }}
                                            className="hidden rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 group-hover:inline-flex"
                                            title="编辑场景名"
                                          >
                                            <Pencil size={12} />
                                          </button>
                                          <button
                                            onClick={() => {
                                              if (
                                                confirm(
                                                  `确定要删除场景「${item.title}」吗？`,
                                                )
                                              ) {
                                                removeScene.mutate(item.id);
                                              }
                                            }}
                                            className="hidden rounded p-1 text-rose-400 hover:bg-rose-50 hover:text-rose-600 group-hover:inline-flex"
                                            title="删除场景"
                                          >
                                            <Trash2 size={12} />
                                          </button>
                                        </>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              ) : null}
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ))}
                  {sortedVolumes.length === 0 ? (
                    <p className="p-3 text-sm text-slate-500">
                      暂无大纲，请新建一个卷
                    </p>
                  ) : null}
                </div>
              </section>

              {/* 新建场景 */}
              <section className="rounded-md border border-slate-200 bg-white p-3">
                <h2 className="text-sm font-semibold text-slate-900">
                  新建场景
                </h2>
                <div className="mt-3 flex gap-2">
                  <input
                    value={sceneTitle}
                    onChange={(event) => setSceneTitle(event.target.value)}
                    className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-600"
                    placeholder="场景标题"
                  />
                  <IconButton
                    icon={<CirclePlus size={15} />}
                    label="添加"
                    tone="primary"
                    disabled={!selectedChapterId || createScene.isPending}
                    onClick={() => createScene.mutate()}
                  />
                </div>
              </section>

              {/* 设定库 */}
              <section className="rounded-md border border-slate-200 bg-white">
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className="flex w-full items-center justify-between border-b border-slate-200 px-3 py-2"
                >
                  <h2 className="text-sm font-semibold text-slate-900">
                    设定库
                  </h2>
                  <span className="text-xs text-slate-400">
                    {showSettings ? "收起" : "展开"}
                  </span>
                </button>
                {showSettings ? (
                  <div className="space-y-3 p-3">
                    {/* 人物设定 */}
                    <div>
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-semibold text-slate-700">
                          人物设定
                          <span className="ml-1 font-normal text-slate-400">
                            {characters.data?.length ?? 0}
                          </span>
                        </h3>
                      </div>
                      <div className="mt-2 flex gap-2">
                        <input
                          value={characterName}
                          onChange={(event) =>
                            setCharacterName(event.target.value)
                          }
                          className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-600"
                          placeholder="人物名"
                        />
                        <IconButton
                          icon={<UserPlus size={15} />}
                          label="添加"
                          onClick={() => createCharacter.mutate()}
                          disabled={
                            !characterName.trim() || createCharacter.isPending
                          }
                        />
                      </div>
                      <div className="mt-2 space-y-1">
                        {characters.data?.map((character) => (
                          <div key={character.id}>
                            {editingCharacterId === character.id ? (
                              <div className="flex items-start gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-2">
                                <div className="min-w-0 flex-1 space-y-1">
                                  <input
                                    value={editingCharacterName}
                                    onChange={(e) =>
                                      setEditingCharacterName(e.target.value)
                                    }
                                    className="w-full rounded border border-slate-300 px-2 py-1 text-sm outline-none focus:border-emerald-600"
                                    placeholder="名称"
                                  />
                                  <input
                                    value={editingCharacterRole}
                                    onChange={(e) =>
                                      setEditingCharacterRole(e.target.value)
                                    }
                                    className="w-full rounded border border-slate-300 px-2 py-1 text-xs outline-none focus:border-emerald-600"
                                    placeholder="身份/角色"
                                  />
                                </div>
                                <div className="flex shrink-0 gap-1">
                                  <button
                                    onClick={() => saveCharacter.mutate()}
                                    disabled={saveCharacter.isPending}
                                    className="rounded p-1 text-emerald-600 hover:bg-emerald-100"
                                    title="保存"
                                  >
                                    <Check size={14} />
                                  </button>
                                  <button
                                    onClick={() => setEditingCharacterId(null)}
                                    className="rounded p-1 text-slate-400 hover:bg-slate-100"
                                    title="取消"
                                  >
                                    <X size={14} />
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <div className="group flex items-center justify-between rounded-md border border-slate-100 px-2 py-1.5">
                                <div className="min-w-0">
                                  <span className="text-sm font-medium text-slate-900">
                                    {character.name}
                                  </span>
                                  <span className="ml-2 text-xs text-slate-500">
                                    {character.role || "未设置身份"}
                                  </span>
                                </div>
                                <div className="hidden items-center gap-1 group-hover:flex">
                                  <button
                                    onClick={() => {
                                      setEditingCharacterId(character.id);
                                      setEditingCharacterName(character.name);
                                      setEditingCharacterRole(
                                        character.role || "",
                                      );
                                    }}
                                    className="rounded p-1 text-slate-400 hover:text-slate-600"
                                    title="编辑"
                                  >
                                    <Pencil size={12} />
                                  </button>
                                  <button
                                    onClick={() => {
                                      if (
                                        confirm(
                                          `确定要删除人物「${character.name}」吗？`,
                                        )
                                      ) {
                                        deleteCharacter.mutate(character.id);
                                      }
                                    }}
                                    className="rounded p-1 text-rose-400 hover:text-rose-600"
                                    title="删除"
                                  >
                                    <Trash2 size={12} />
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* 世界观设定 */}
                    <div>
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-semibold text-slate-700">
                          世界观设定
                          <span className="ml-1 font-normal text-slate-400">
                            {worldEntries.data?.length ?? 0}
                          </span>
                        </h3>
                      </div>
                      <div className="mt-2 flex gap-2">
                        <input
                          value={worldName}
                          onChange={(event) => setWorldName(event.target.value)}
                          className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-600"
                          placeholder="设定名"
                        />
                        <IconButton
                          icon={<Globe2 size={15} />}
                          label="添加"
                          onClick={() => createWorld.mutate()}
                          disabled={!worldName.trim() || createWorld.isPending}
                        />
                      </div>
                      <div className="mt-2 space-y-1">
                        {worldEntries.data?.map((entry) => (
                          <div key={entry.id}>
                            {editingWorldId === entry.id ? (
                              <div className="flex items-start gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-2">
                                <div className="min-w-0 flex-1 space-y-1">
                                  <input
                                    value={editingWorldName}
                                    onChange={(e) =>
                                      setEditingWorldName(e.target.value)
                                    }
                                    className="w-full rounded border border-slate-300 px-2 py-1 text-sm outline-none focus:border-emerald-600"
                                    placeholder="名称"
                                  />
                                  <input
                                    value={editingWorldSummary}
                                    onChange={(e) =>
                                      setEditingWorldSummary(e.target.value)
                                    }
                                    className="w-full rounded border border-slate-300 px-2 py-1 text-xs outline-none focus:border-emerald-600"
                                    placeholder="摘要"
                                  />
                                </div>
                                <div className="flex shrink-0 gap-1">
                                  <button
                                    onClick={() => saveWorld.mutate()}
                                    disabled={saveWorld.isPending}
                                    className="rounded p-1 text-emerald-600 hover:bg-emerald-100"
                                    title="保存"
                                  >
                                    <Check size={14} />
                                  </button>
                                  <button
                                    onClick={() => setEditingWorldId(null)}
                                    className="rounded p-1 text-slate-400 hover:bg-slate-100"
                                    title="取消"
                                  >
                                    <X size={14} />
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <div className="group flex items-center justify-between rounded-md border border-slate-100 px-2 py-1.5">
                                <div className="min-w-0">
                                  <span className="text-sm font-medium text-slate-900">
                                    {entry.name}
                                  </span>
                                  <span className="ml-2 text-xs text-slate-400">
                                    {entry.entry_type}
                                  </span>
                                </div>
                                <div className="hidden items-center gap-1 group-hover:flex">
                                  <button
                                    onClick={() => {
                                      setEditingWorldId(entry.id);
                                      setEditingWorldName(entry.name);
                                      setEditingWorldSummary(
                                        entry.summary || "",
                                      );
                                    }}
                                    className="rounded p-1 text-slate-400 hover:text-slate-600"
                                    title="编辑"
                                  >
                                    <Pencil size={12} />
                                  </button>
                                  <button
                                    onClick={() => {
                                      if (
                                        confirm(
                                          `确定要删除世界观条目「${entry.name}」吗？`,
                                        )
                                      ) {
                                        deleteWorld.mutate(entry.id);
                                      }
                                    }}
                                    className="rounded p-1 text-rose-400 hover:text-rose-600"
                                    title="删除"
                                  >
                                    <Trash2 size={12} />
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : null}
              </section>
            </aside>
          </>
        }
        center={
          <>
            {/* ── 中间：正文优先 ── */}
            <div
              className={`mx-auto w-full space-y-4 ${
                writingPreferences.width === "narrow"
                  ? "max-w-2xl"
                  : writingPreferences.width === "wide"
                    ? "max-w-5xl"
                    : "max-w-3xl"
              } ${
                writingPreferences.font === "serif"
                  ? "novel-font-serif"
                  : "novel-font-sans"
              } ${
                writingPreferences.size === "small"
                  ? "[&_.ProseMirror]:text-sm"
                  : writingPreferences.size === "large"
                    ? "[&_.ProseMirror]:text-lg"
                    : writingPreferences.size === "xlarge"
                      ? "[&_.ProseMirror]:text-xl"
                      : "[&_.ProseMirror]:text-base"
              } ${
                writingPreferences.spacing === "compact"
                  ? "[&_.ProseMirror]:leading-6"
                  : writingPreferences.spacing === "relaxed"
                    ? "[&_.ProseMirror]:leading-8"
                    : "[&_.ProseMirror]:leading-7"
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs shadow-panel">
                <div className="flex items-center gap-2 text-stone-500">
                  <span className="font-medium text-stone-700">阅读设置</span>
                  <span className="hidden sm:inline">仅影响本机显示</span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    aria-label="正文字体"
                    value={writingPreferences.font}
                    onChange={(event) =>
                      setWritingPreferences((current) => ({
                        ...current,
                        font: event.target.value === "serif" ? "serif" : "sans",
                      }))
                    }
                    className="rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-stone-700 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                  >
                    <option value="sans">现代无衬线</option>
                    <option value="serif">书籍衬线</option>
                  </select>
                  <select
                    aria-label="正文字号"
                    value={writingPreferences.size}
                    onChange={(event) =>
                      setWritingPreferences((current) => ({
                        ...current,
                        size: event.target.value as WritingSize,
                      }))
                    }
                    className="rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-stone-700 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                  >
                    <option value="small">14px</option>
                    <option value="medium">16px</option>
                    <option value="large">18px</option>
                    <option value="xlarge">20px</option>
                  </select>
                  <select
                    aria-label="正文行距"
                    value={writingPreferences.spacing}
                    onChange={(event) =>
                      setWritingPreferences((current) => ({
                        ...current,
                        spacing: event.target.value as WritingSpacing,
                      }))
                    }
                    className="rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-stone-700 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                  >
                    <option value="compact">紧凑 1.6</option>
                    <option value="comfortable">舒适 1.8</option>
                    <option value="relaxed">宽松 2.0</option>
                  </select>
                  <select
                    aria-label="正文版心"
                    value={writingPreferences.width}
                    onChange={(event) =>
                      setWritingPreferences((current) => ({
                        ...current,
                        width: event.target.value as WritingWidth,
                      }))
                    }
                    className="rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-stone-700 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                  >
                    <option value="narrow">窄版心</option>
                    <option value="standard">标准版心</option>
                    <option value="wide">宽版心</option>
                  </select>
                </div>
              </div>
              <SceneEditor
                scene={scene.data ?? null}
                selectedVersionId={selectedSceneVersionId}
                loadSelectedVersion={hasExplicitSceneVersionSelection}
                onVersionCreated={handleVersionCreated}
                targetWordCount={project.data?.default_scene_word_count ?? 1000}
                onContentChange={setEditorContent}
              />
            </div>
          </>
        }
        right={
          <>
            {/* ── 右侧栏：当前场景版本工具 ── */}
            <aside className={`min-w-0 space-y-3 ${focusMode ? "hidden" : ""}`}>
              <WorkspacePanelTabs value={rightTab} onChange={setRightTab} />

              {rightTab === "ai" ? (
                <SceneGenerationPanel
                  sceneId={selectedSceneId}
                  modelProfileId={modelProfileId}
                  defaultTargetWordCount={
                    project.data?.default_scene_word_count ?? 1000
                  }
                  baseContent={editorContent}
                  instructionFromDiscussion={discussionInstruction}
                  onVersionCreated={handleVersionCreated}
                />
              ) : null}

              {rightTab === "review" ? (
                <>
                  <ReviewIssuePanel
                    sceneVersionId={selectedSceneVersionId}
                    modelProfileId={modelProfileId}
                  />
                  {impactReports.data
                    ?.filter((report) => report.status === "open")
                    .map((report) => (
                      <section
                        key={report.id}
                        className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900"
                      >
                        <p className="font-semibold">正式稿替换影响</p>
                        <p className="mt-1">
                          以下 {report.affected_scene_ids_json.length}{" "}
                          个后续场景需要复查：
                          {report.affected_scene_ids_json.join("、") || "无"}
                        </p>
                        <button
                          className="mt-2 rounded border border-amber-300 bg-white px-2 py-1"
                          onClick={() => acknowledgeImpact.mutate(report.id)}
                        >
                          已查看影响
                        </button>
                      </section>
                    ))}
                </>
              ) : null}

              {rightTab === "memory" ? (
                <MemoryCandidatePanel
                  sceneId={selectedSceneId}
                  sceneVersionId={selectedSceneVersionId}
                  approvedVersionId={scene.data?.approved_version_id ?? null}
                  modelProfileId={modelProfileId}
                />
              ) : null}

              {rightTab === "history" ? (
                <div className="space-y-3">
                  <SceneVersionSelector
                    versions={sceneVersions.data ?? []}
                    approvedVersionId={scene.data?.approved_version_id ?? null}
                    selectedVersionId={selectedSceneVersionId || null}
                    onSelect={handleVersionSelectionChange}
                    onSummaryGenerated={() =>
                      queryClient.invalidateQueries({
                        queryKey: ["scene-versions", selectedSceneId],
                      })
                    }
                  />
                  <SceneApprovalPanel
                    scene={scene.data ?? null}
                    versions={sceneVersions.data ?? []}
                    modelProfileId={modelProfileId}
                  />
                </div>
              ) : null}

              {rightTab === "discussion" ? (
                <CreativeDiscussionPanel
                  projectId={projectId}
                  sceneId={selectedSceneId}
                  modelProfileId={modelProfileId}
                  onApplyRewriteInstruction={(instruction) => {
                    setDiscussionInstruction(instruction);
                    setRightTab("ai");
                  }}
                />
              ) : null}

              {rightTab === "advanced" ? (
                <div className="space-y-3">
                  <WritingSettingsPanel project={project.data ?? null} />
                  <details className="rounded-md border border-slate-200 bg-white p-3">
                    <summary className="cursor-pointer text-xs font-medium text-slate-700">
                      写作上下文与约束
                    </summary>
                    <div className="mt-3">
                      <WritingAssistant sceneId={selectedSceneId} />
                    </div>
                  </details>
                  <SceneCardEditor
                    scene={scene.data ?? null}
                    characters={characters.data}
                    worldEntries={worldEntries.data}
                  />
                  <ContextChecker sceneId={selectedSceneId} />
                </div>
              ) : null}
            </aside>
          </>
        }
      />
    </main>
  );
}
