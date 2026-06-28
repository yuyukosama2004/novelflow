import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, BookOpen, Globe2, Heart, ListChecks, Users, Clock } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

import { apiClient } from '../../api/client';
import { CoreConceptPanel } from './CoreConceptPanel';
import { CharacterDetailPanel } from './CharacterDetailPanel';
import { OutlineGeneratorPanel } from './OutlineGeneratorPanel';
import { WorldEntryDetailPanel } from './WorldEntryDetailPanel';
import { RelationshipPanel } from './RelationshipPanel';
import { TimelinePanel } from './TimelinePanel';

type Tab = 'concept' | 'characters' | 'relationships' | 'world' | 'outline' | 'timeline';

const TABS: { key: Tab; label: string; icon: React.ElementType }[] = [
  { key: 'concept', label: '核心概念', icon: BookOpen },
  { key: 'characters', label: '人物', icon: Users },
  { key: 'relationships', label: '人物关系', icon: Heart },
  { key: 'world', label: '世界观', icon: Globe2 },
  { key: 'outline', label: '大纲', icon: ListChecks },
  { key: 'timeline', label: '时间线', icon: Clock },
];

export function StoryBiblePage() {
  const { projectId = '' } = useParams();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>('concept');
  const [selectedCharId, setSelectedCharId] = useState<string | null>(null);

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
  const relationships = useQuery({
    queryKey: ['relationships', projectId],
    queryFn: () => apiClient.listRelationships(projectId),
    enabled: Boolean(projectId),
  });
  const volumes = useQuery({
    queryKey: ['volumes', projectId],
    queryFn: () => apiClient.listVolumes(projectId),
    enabled: Boolean(projectId),
  });

  const saveProject = useMutation({
    mutationFn: (payload: Record<string, string>) =>
      apiClient.patchProject(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['project', projectId] }),
  });

  const saveCharacter = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) =>
      apiClient.patchCharacter(id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['characters', projectId] }),
  });

  const saveWorldEntry = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) =>
      apiClient.patchWorldEntry(id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['world', projectId] }),
  });

  const createRelationship = useMutation({
    mutationFn: (payload: {
      character_a_id: string;
      character_b_id: string;
      relation_type: string;
      description: string;
      timeline_info: string;
    }) => apiClient.createRelationship(projectId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['relationships', projectId] }),
  });

  const deleteRelationship = useMutation({
    mutationFn: (id: string) => apiClient.deleteRelationship(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['relationships', projectId] }),
  });

  return (
    <main className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-3">
          <div className="flex items-center gap-4">
            <Link to="/" className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900">
              <ArrowLeft size={15} /> 返回项目列表
            </Link>
            <h1 className="text-lg font-semibold text-slate-950">
              {project.data?.title ?? '加载中…'} · 故事圣经
            </h1>
          </div>
          <Link to={`/projects/${projectId}`}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700">
            进入工作台
          </Link>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-5 py-4">
        {/* Tab 导航 */}
        <nav className="flex gap-1 rounded-md border border-slate-200 bg-white p-1 mb-4">
          {TABS.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 rounded px-4 py-2 text-sm font-medium transition ${
                tab === t.key
                  ? 'bg-emerald-600 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}>
              <t.icon size={15} />
              {t.label}
            </button>
          ))}
        </nav>

        {/* Tab 内容 */}
        <div className="rounded-md border border-slate-200 bg-white p-6">
          {tab === 'concept' ? (
            <CoreConceptPanel
              project={project.data}
              isLoading={project.isLoading}
              onSave={(p) => saveProject.mutate(p)}
              isSaving={saveProject.isPending}
            />
          ) : tab === 'characters' ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">人物设定</h2>
                <span className="text-xs text-slate-400">{characters.data?.length ?? 0} 个</span>
              </div>
              {characters.data?.length === 0 ? (
                <div className="rounded-md border border-dashed border-slate-200 px-3 py-8 text-center text-sm text-slate-400">
                  暂无人物。在创作向导中通过访谈添加，或在左侧列表中选择人物查看详情。
                </div>
              ) : selectedCharId ? (
                <div>
                  <button onClick={() => setSelectedCharId(null)}
                    className="mb-3 text-xs text-indigo-600 hover:text-indigo-800">
                    ← 返回人物列表
                  </button>
                  {characters.data?.filter((c) => c.id === selectedCharId).map((c) => (
                    <CharacterDetailPanel key={c.id} character={c}
                      onSave={(id, payload) => saveCharacter.mutate({ id, payload })}
                      isSaving={saveCharacter.isPending} />
                  ))}
                </div>
              ) : (
                <div className="grid gap-2">
                  {characters.data?.map((c) => (
                    <button key={c.id} onClick={() => setSelectedCharId(c.id)}
                      className="flex items-center justify-between rounded-md border border-slate-200 bg-white p-3 text-left hover:bg-slate-50">
                      <div>
                        <span className="font-medium text-slate-900">{c.name}</span>
                        <span className="ml-2 text-xs text-slate-500">{c.role || '未设置身份'}</span>
                      </div>
                      <span className="text-xs text-slate-400">查看详情 →</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : tab === 'relationships' ? (
            <RelationshipPanel
              relationships={relationships.data ?? []}
              characters={characters.data ?? []}
              onCreate={(p) => createRelationship.mutate(p)}
              onDelete={(id) => deleteRelationship.mutate(id)}
              isCreating={createRelationship.isPending}
            />
          ) : tab === 'world' ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">世界观设定</h2>
                <span className="text-xs text-slate-400">{worldEntries.data?.length ?? 0} 条</span>
              </div>
              {worldEntries.data?.length === 0 ? (
                <div className="rounded-md border border-dashed border-slate-200 px-3 py-8 text-center text-sm text-slate-400">
                  暂无世界观条目。在创作向导中通过访谈添加。
                </div>
              ) : (
                <div className="space-y-3">
                  {worldEntries.data?.map((e) => (
                    <div key={e.id} className="rounded-md border border-slate-200 bg-white p-3">
                      <WorldEntryDetailPanel entry={e}
                        onSave={(id, payload) => saveWorldEntry.mutate({ id, payload })}
                        isSaving={saveWorldEntry.isPending} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : tab === 'outline' ? (
            <OutlineGeneratorPanel
              projectId={projectId}
              hasExistingOutline={(volumes.data?.length ?? 0) > 0}
            />
          ) : tab === 'timeline' ? (
            <TimelinePanel projectId={projectId} />
          ) : null}
        </div>
      </div>
    </main>
  );
}
