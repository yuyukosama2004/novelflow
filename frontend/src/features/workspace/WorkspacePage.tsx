import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, BookMarked, CirclePlus, Globe2, UserPlus } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

import { apiClient } from '../../api/client';
import { IconButton } from '../../components/IconButton';
import { StatusPill } from '../../components/StatusPill';
import type { Chapter, Scene, Volume } from '../../types/entities';
import { SceneEditor } from './SceneEditor';
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
  const [characterName, setCharacterName] = useState('');
  const [worldName, setWorldName] = useState('');
  const [sceneTitle, setSceneTitle] = useState('');

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

  const createCharacter = useMutation({
    mutationFn: () => apiClient.createCharacter(projectId, { name: characterName, role: '角色' }),
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

  const sortedVolumes = useMemo(() => [...(volumes.data ?? [])].sort((a, b) => a.sequence_no - b.sequence_no), [
    volumes.data,
  ]);

  return (
    <main className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-5 py-3">
          <div className="min-w-0">
            <Link to="/" className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900">
              <ArrowLeft size={15} />
              项目
            </Link>
            <h1 className="mt-1 truncate text-xl font-semibold text-slate-950">
              {project.data?.title ?? 'NovelFlow'}
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <StatusPill tone="ok">{project.data?.status ?? 'loading'}</StatusPill>
            <a
              href={`http://localhost:8000/api/projects/${projectId}/exports/markdown`}
              className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-emerald-400"
            >
              导出 Markdown
            </a>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1600px] gap-4 px-5 py-4 xl:grid-cols-[300px_minmax(0,1fr)_340px]">
        <aside className="space-y-4">
          <section className="rounded-md border border-slate-200 bg-white">
            <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2">
              <h2 className="text-sm font-semibold text-slate-900">大纲</h2>
              <div className="flex gap-2">
                <IconButton
                  icon={<CirclePlus size={15} />}
                  label="卷"
                  onClick={() => createVolume.mutate()}
                  disabled={createVolume.isPending}
                />
                <IconButton
                  icon={<BookMarked size={15} />}
                  label="章"
                  onClick={() => createChapter.mutate()}
                  disabled={!selectedVolumeId || createChapter.isPending}
                />
              </div>
            </div>
            <div className="max-h-[520px] overflow-auto p-2">
              {sortedVolumes.map((volume) => (
                <div key={volume.id} className="mb-2">
                  <button
                    onClick={() => {
                      setSelectedVolumeId(volume.id);
                      setSelectedChapterId('');
                      setSelectedSceneId('');
                    }}
                    className={`w-full rounded-md px-3 py-2 text-left text-sm font-medium ${
                      selectedVolumeId === volume.id ? 'bg-emerald-50 text-emerald-800' : 'text-slate-700'
                    }`}
                  >
                    {volume.sequence_no}. {volume.title}
                  </button>
                  {selectedVolumeId === volume.id ? (
                    <div className="ml-3 mt-1 space-y-1 border-l border-slate-200 pl-2">
                      {chapters.data?.map((chapter) => (
                        <div key={chapter.id}>
                          <button
                            onClick={() => {
                              setSelectedChapterId(chapter.id);
                              setSelectedSceneId('');
                            }}
                            className={`w-full rounded-md px-2 py-1.5 text-left text-sm ${
                              selectedChapterId === chapter.id
                                ? 'bg-amber-50 text-amber-900'
                                : 'text-slate-600'
                            }`}
                          >
                            {chapter.sequence_no}. {chapter.title}
                          </button>
                          {selectedChapterId === chapter.id ? (
                            <div className="ml-2 mt-1 space-y-1">
                              {scenes.data?.map((item) => (
                                <button
                                  key={item.id}
                                  onClick={() => setSelectedSceneId(item.id)}
                                  className={`w-full rounded-md px-2 py-1.5 text-left text-sm ${
                                    selectedSceneId === item.id
                                      ? 'bg-slate-900 text-white'
                                      : 'text-slate-600 hover:bg-slate-50'
                                  }`}
                                >
                                  {item.sequence_no}. {item.title}
                                </button>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
              {sortedVolumes.length === 0 ? <p className="p-3 text-sm text-slate-500">暂无大纲</p> : null}
            </div>
          </section>

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
        </aside>

        <SceneEditor scene={scene.data ?? null} />
          <ContextChecker sceneId={selectedSceneId} />
          <SceneGenerationPanel sceneId={selectedSceneId} />

        <aside className="space-y-4">
          <section className="rounded-md border border-slate-200 bg-white p-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-900">人物</h2>
              <StatusPill>{String(characters.data?.length ?? 0)}</StatusPill>
            </div>
            <div className="mt-3 flex gap-2">
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
            <div className="mt-3 space-y-2">
              {characters.data?.map((character) => (
                <div key={character.id} className="rounded-md border border-slate-100 px-3 py-2">
                  <div className="font-medium text-slate-900">{character.name}</div>
                  <div className="mt-1 text-xs text-slate-500">{character.role || '未设置身份'}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-md border border-slate-200 bg-white p-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-900">世界观</h2>
              <StatusPill>{String(worldEntries.data?.length ?? 0)}</StatusPill>
            </div>
            <div className="mt-3 flex gap-2">
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
            <div className="mt-3 space-y-2">
              {worldEntries.data?.map((entry) => (
                <div key={entry.id} className="rounded-md border border-slate-100 px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0 font-medium text-slate-900">{entry.name}</div>
                    <StatusPill tone={entry.canon_status === 'approved' ? 'ok' : 'neutral'}>
                      {entry.canon_status}
                    </StatusPill>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{entry.entry_type}</div>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </main>
  );
}
