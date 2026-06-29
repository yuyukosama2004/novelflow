import { useCallback, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  BookMarked,
  Check,
  CirclePlus,
  Globe2,
  Pencil,
  Trash2,
  UserPlus,
  X,
} from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

import { API_BASE_URL, apiClient } from '../../api/client';
import { IconButton } from '../../components/IconButton';
import { ModelSelector } from '../../components/ModelSelector';
import { StatusPill } from '../../components/StatusPill';
import type { Chapter, Scene, SceneVersion, Volume } from '../../types/entities';
import { label, PROJECT_STATUS_LABELS } from '../../utils/enumLabels';
import { MemoryCandidatePanel } from './MemoryCandidatePanel';
import { ReviewIssuePanel } from './ReviewIssuePanel';
import { SceneCardEditor } from './SceneCardEditor';
import { SceneEditor } from './SceneEditor';
import { WritingAssistant } from './WritingAssistant';
import { SceneVersionSelector } from './SceneVersionSelector';
import {
  getDefaultSceneVersionId,
  resolveSceneVersionSelection,
} from './sceneVersionSelection';
import ContextChecker from './ContextChecker';
import SceneGenerationPanel from '../workflows/SceneGenerationPanel';

function nextSequence<T extends { sequence_no: number }>(items: T[] | undefined): number {
  return (items?.reduce((max, item) => Math.max(max, item.sequence_no), 0) ?? 0) + 1;
}

export function WorkspacePage() {
  const { projectId = '' } = useParams();
  const queryClient = useQueryClient();
  const [selectedVolumeId, setSelectedVolumeId] = useState<string>('');
  const [selectedChapterId, setSelectedChapterId] = useState<string>('');
  const [selectedSceneId, setSelectedSceneId] = useState<string>('');
  const [selectedSceneVersionId, setSelectedSceneVersionId] = useState<string>('');
  const [pendingSceneVersionId, setPendingSceneVersionId] = useState<string>('');
  const [hasExplicitSceneVersionSelection, setHasExplicitSceneVersionSelection] =
    useState(false);
  const [characterName, setCharacterName] = useState('');
  const [worldName, setWorldName] = useState('');
  const [sceneTitle, setSceneTitle] = useState('');

  // 编辑状态
  const [editingProject, setEditingProject] = useState(false);
  const [projectTitle, setProjectTitle] = useState('');
  const [editingCharacterId, setEditingCharacterId] = useState<string | null>(null);
  const [editingCharacterName, setEditingCharacterName] = useState('');
  const [editingCharacterRole, setEditingCharacterRole] = useState('');
  const [editingWorldId, setEditingWorldId] = useState<string | null>(null);
  const [editingWorldName, setEditingWorldName] = useState('');
  const [editingWorldSummary, setEditingWorldSummary] = useState('');
  const [editingVolumeId, setEditingVolumeId] = useState<string | null>(null);
  const [editingVolumeTitle, setEditingVolumeTitle] = useState('');
  const [editingChapterId, setEditingChapterId] = useState<string | null>(null);
  const [editingChapterTitle, setEditingChapterTitle] = useState('');
  const [editingSceneId, setEditingSceneId] = useState<string | null>(null);
  const [editingSceneTitle, setEditingSceneTitle] = useState('');
  const [showSettings, setShowSettings] = useState(true);
  const [modelProfileId, setModelProfileId] = useState('');

  // ── 数据查询 ──
  const project = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => apiClient.getProject(projectId),
    enabled: Boolean(projectId),
  });
  const characters = useQuery({
    queryKey: ['characters', projectId],
    queryFn: () => apiClient.listCharacters(projectId),
    enabled: Boolean(projectId),
  });
  const worldEntries = useQuery({
    queryKey: ['world', projectId],
    queryFn: () => apiClient.listWorldEntries(projectId),
    enabled: Boolean(projectId),
  });
  const volumes = useQuery({
    queryKey: ['volumes', projectId],
    queryFn: () => apiClient.listVolumes(projectId),
    enabled: Boolean(projectId),
  });
  const chapters = useQuery({
    queryKey: ['chapters', selectedVolumeId],
    queryFn: () => apiClient.listChapters(selectedVolumeId),
    enabled: Boolean(selectedVolumeId),
  });
  const scenes = useQuery({
    queryKey: ['scenes', selectedChapterId],
    queryFn: () => apiClient.listScenes(selectedChapterId),
    enabled: Boolean(selectedChapterId),
  });
  const scene = useQuery({
    queryKey: ['scene', selectedSceneId],
    queryFn: () => apiClient.getScene(selectedSceneId),
    enabled: Boolean(selectedSceneId),
  });
  const sceneVersions = useQuery({
    queryKey: ['scene-versions', selectedSceneId],
    queryFn: () => apiClient.listVersions(selectedSceneId),
    enabled: Boolean(selectedSceneId),
  });

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
    setSelectedSceneVersionId('');
    setPendingSceneVersionId('');
    setHasExplicitSceneVersionSelection(false);
  }, [selectedSceneId]);

  useEffect(() => {
    if (!selectedSceneId) {
      setSelectedSceneVersionId('');
      setPendingSceneVersionId('');
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
    if (nextSelection.hasExplicitSelection !== hasExplicitSceneVersionSelection) {
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
    setPendingSceneVersionId('');
    setHasExplicitSceneVersionSelection(true);
    setSelectedSceneVersionId(versionId);
  }, []);

  const handleVersionCreated = useCallback(
    (version?: SceneVersion) => {
      if (version?.id) {
        setPendingSceneVersionId(version.id);
      }
      queryClient.invalidateQueries({ queryKey: ['scene-versions', selectedSceneId] });
    },
    [queryClient, selectedSceneId],
  );

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    queryClient.invalidateQueries({ queryKey: ['characters', projectId] });
    queryClient.invalidateQueries({ queryKey: ['world', projectId] });
    queryClient.invalidateQueries({ queryKey: ['volumes', projectId] });
    queryClient.invalidateQueries({ queryKey: ['chapters', selectedVolumeId] });
    queryClient.invalidateQueries({ queryKey: ['scenes', selectedChapterId] });
  };

  // ── 创建操作 ──
  const createCharacter = useMutation({
    mutationFn: () =>
      apiClient.createCharacter(projectId, { name: characterName, role: '角色' }),
    onSuccess: () => {
      setCharacterName('');
      queryClient.invalidateQueries({ queryKey: ['characters', projectId] });
    },
  });
  const createWorld = useMutation({
    mutationFn: () =>
      apiClient.createWorldEntry(projectId, {
        name: worldName,
        entry_type: 'custom',
        canon_status: 'draft',
      }),
    onSuccess: () => {
      setWorldName('');
      queryClient.invalidateQueries({ queryKey: ['world', projectId] });
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
      setSelectedChapterId('');
      setSelectedSceneId('');
      queryClient.invalidateQueries({ queryKey: ['volumes', projectId] });
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
      setSelectedSceneId('');
      queryClient.invalidateQueries({ queryKey: ['chapters', selectedVolumeId] });
    },
  });
  const createScene = useMutation({
    mutationFn: () =>
      apiClient.createScene(selectedChapterId, {
        sequence_no: nextSequence(scenes.data),
        title: sceneTitle || `场景 ${nextSequence(scenes.data)}`,
      }),
    onSuccess: (createdScene: Scene) => {
      setSceneTitle('');
      setSelectedSceneId(createdScene.id);
      queryClient.invalidateQueries({ queryKey: ['scenes', selectedChapterId] });
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
      queryClient.invalidateQueries({ queryKey: ['characters', projectId] });
    },
  });
  const deleteCharacter = useMutation({
    mutationFn: (id: string) => apiClient.deleteCharacter(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['characters', projectId] }),
  });

  const saveWorld = useMutation({
    mutationFn: () =>
      apiClient.patchWorldEntry(editingWorldId!, {
        name: editingWorldName,
        summary: editingWorldSummary,
      }),
    onSuccess: () => {
      setEditingWorldId(null);
      queryClient.invalidateQueries({ queryKey: ['world', projectId] });
    },
  });
  const deleteWorld = useMutation({
    mutationFn: (id: string) => apiClient.deleteWorldEntry(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['world', projectId] }),
  });

  const saveVolume = useMutation({
    mutationFn: () =>
      apiClient.patchVolume(editingVolumeId!, { title: editingVolumeTitle }),
    onSuccess: () => {
      setEditingVolumeId(null);
      queryClient.invalidateQueries({ queryKey: ['volumes', projectId] });
    },
  });
  const saveChapter = useMutation({
    mutationFn: () =>
      apiClient.patchChapter(editingChapterId!, { title: editingChapterTitle }),
    onSuccess: () => {
      setEditingChapterId(null);
      queryClient.invalidateQueries({ queryKey: ['chapters', selectedVolumeId] });
    },
  });
  const saveScene = useMutation({
    mutationFn: () =>
      apiClient.patchScene(editingSceneId!, { title: editingSceneTitle }),
    onSuccess: () => {
      setEditingSceneId(null);
      queryClient.invalidateQueries({ queryKey: ['scenes', selectedChapterId] });
    },
  });
  const removeScene = useMutation({
    mutationFn: (id: string) => apiClient.deleteScene(id),
    onSuccess: () => {
      if (selectedSceneId) {
        setSelectedSceneId('');
      }
      queryClient.invalidateQueries({ queryKey: ['scenes', selectedChapterId] });
    },
  });

  const sortedVolumes = useMemo(
    () => [...(volumes.data ?? [])].sort((a, b) => a.sequence_no - b.sequence_no),
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
    <main className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-5 py-3">
          <div className="min-w-0">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"
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
                  <h1 className="truncate text-xl font-semibold text-slate-950">
                    {project.data?.title ?? '加载中…'}
                  </h1>
                  <button
                    onClick={() => {
                      setProjectTitle(project.data?.title ?? '');
                      setEditingProject(true);
                    }}
                    className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                    title="编辑项目"
                  >
                    <Pencil size={14} />
                  </button>
                </>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <StatusPill tone="ok">
              {label(PROJECT_STATUS_LABELS, project.data?.status)}
            </StatusPill>
            <ModelSelector selectedId={modelProfileId} onChange={setModelProfileId} />
            <Link
              to={`/projects/${projectId}/bible`}
              className="rounded-md border border-amber-200 bg-white px-3 py-2 text-sm font-medium text-amber-700 hover:bg-amber-50"
            >
              故事圣经
            </Link>
            <Link
              to={`/projects/${projectId}/wizard`}
              className="rounded-md border border-indigo-200 bg-white px-3 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
            >
              创作向导
            </Link>
            <a
              href={`${API_BASE_URL}/projects/${projectId}/exports/markdown`}
              className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-emerald-400"
            >
              导出 Markdown
            </a>
            <button
              onClick={() => {
                if (confirm('确定要归档此项目吗？归档后仍可在项目列表中查看。')) {
                  archiveProject.mutate();
                }
              }}
              className="rounded-md border border-rose-200 bg-white px-3 py-2 text-sm font-medium text-rose-600 hover:bg-rose-50"
            >
              归档
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1600px] gap-4 px-5 py-4 xl:grid-cols-[300px_minmax(0,1fr)_340px]">
        {/* ── 左侧栏：大纲 + 设定库 ── */}
        <aside className="space-y-4">
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
                        onChange={(e) => setEditingVolumeTitle(e.target.value)}
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
                          setSelectedChapterId('');
                          setSelectedSceneId('');
                        }}
                        className={`flex-1 rounded-md px-3 py-2 text-left text-sm font-medium ${
                          selectedVolumeId === volume.id
                            ? 'bg-emerald-50 text-emerald-800'
                            : 'text-slate-700'
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
                                onChange={(e) => setEditingChapterTitle(e.target.value)}
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
                                  setSelectedSceneId('');
                                }}
                                className={`flex-1 rounded-md px-2 py-1.5 text-left text-sm ${
                                  selectedChapterId === chapter.id
                                    ? 'bg-amber-50 text-amber-900'
                                    : 'text-slate-600'
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
                                <div key={item.id} className="group flex items-center gap-1">
                                  {editingSceneId === item.id ? (
                                    <div className="flex flex-1 items-center gap-1 px-1 py-1">
                                      <input
                                        value={editingSceneTitle}
                                        onChange={(e) => setEditingSceneTitle(e.target.value)}
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
                                        onClick={() => setEditingSceneId(null)}
                                        className="rounded p-1 text-slate-400 hover:bg-slate-100"
                                        title="取消"
                                      >
                                        <X size={14} />
                                      </button>
                                    </div>
                                  ) : (
                                    <button
                                      onClick={() => setSelectedSceneId(item.id)}
                                      className={`flex-1 rounded-md px-2 py-1.5 text-left text-sm ${
                                        selectedSceneId === item.id
                                          ? 'bg-slate-900 text-white'
                                          : 'text-slate-600 hover:bg-slate-50'
                                      }`}
                                    >
                                      {item.sequence_no}. {item.title}
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
                                          if (confirm(`确定要删除场景「${item.title}」吗？`)) {
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
                <p className="p-3 text-sm text-slate-500">暂无大纲，请新建一个卷</p>
              ) : null}
            </div>
          </section>

          {/* 新建场景 */}
          <section className="rounded-md border border-slate-200 bg-white p-3">
            <h2 className="text-sm font-semibold text-slate-900">新建场景</h2>
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
              <h2 className="text-sm font-semibold text-slate-900">设定库</h2>
              <span className="text-xs text-slate-400">{showSettings ? '收起' : '展开'}</span>
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
                      onChange={(event) => setCharacterName(event.target.value)}
                      className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-600"
                      placeholder="人物名"
                    />
                    <IconButton
                      icon={<UserPlus size={15} />}
                      label="添加"
                      onClick={() => createCharacter.mutate()}
                      disabled={!characterName.trim() || createCharacter.isPending}
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
                                onChange={(e) => setEditingCharacterName(e.target.value)}
                                className="w-full rounded border border-slate-300 px-2 py-1 text-sm outline-none focus:border-emerald-600"
                                placeholder="名称"
                              />
                              <input
                                value={editingCharacterRole}
                                onChange={(e) => setEditingCharacterRole(e.target.value)}
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
                                {character.role || '未设置身份'}
                              </span>
                            </div>
                            <div className="hidden items-center gap-1 group-hover:flex">
                              <button
                                onClick={() => {
                                  setEditingCharacterId(character.id);
                                  setEditingCharacterName(character.name);
                                  setEditingCharacterRole(character.role || '');
                                }}
                                className="rounded p-1 text-slate-400 hover:text-slate-600"
                                title="编辑"
                              >
                                <Pencil size={12} />
                              </button>
                              <button
                                onClick={() => {
                                  if (confirm(`确定要删除人物「${character.name}」吗？`)) {
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
                                onChange={(e) => setEditingWorldName(e.target.value)}
                                className="w-full rounded border border-slate-300 px-2 py-1 text-sm outline-none focus:border-emerald-600"
                                placeholder="名称"
                              />
                              <input
                                value={editingWorldSummary}
                                onChange={(e) => setEditingWorldSummary(e.target.value)}
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
                                  setEditingWorldSummary(entry.summary || '');
                                }}
                                className="rounded p-1 text-slate-400 hover:text-slate-600"
                                title="编辑"
                              >
                                <Pencil size={12} />
                              </button>
                              <button
                                onClick={() => {
                                  if (confirm(`确定要删除世界观条目「${entry.name}」吗？`)) {
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

        {/* ── 中间：写作辅助 + 场景编辑器 ── */}
        <div className="space-y-4">
          <WritingAssistant sceneId={selectedSceneId} />
          <SceneEditor
            scene={scene.data ?? null}
            onVersionCreated={handleVersionCreated}
          />
        </div>

        {/* ── 右侧栏：当前场景版本工具 ── */}
        <aside className="space-y-4">
          <SceneVersionSelector
            versions={sceneVersions.data ?? []}
            approvedVersionId={scene.data?.approved_version_id ?? null}
            selectedVersionId={selectedSceneVersionId || null}
            onSelect={handleVersionSelectionChange}
          />
          <SceneGenerationPanel
            sceneId={selectedSceneId}
            onVersionCreated={handleVersionCreated}
          />
          <SceneCardEditor scene={scene.data ?? null} />
          <ContextChecker sceneId={selectedSceneId} />
          <ReviewIssuePanel sceneVersionId={selectedSceneVersionId} />
          <MemoryCandidatePanel sceneVersionId={selectedSceneVersionId} />
        </aside>
      </div>
    </main>
  );
}
