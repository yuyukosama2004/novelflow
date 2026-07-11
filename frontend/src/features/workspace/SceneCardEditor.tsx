import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Pencil, X } from 'lucide-react';

import { apiClient } from '../../api/client';
import type { Character, Scene, SceneContextLinks, WorldEntry } from '../../types/entities';

interface Props {
  scene: Scene | null;
  characters?: Character[];
  worldEntries?: WorldEntry[];
}

const FIELD_LABELS: { key: string; label: string; textarea?: boolean }[] = [
  { key: 'title', label: '场景标题' },
  { key: 'time_text', label: '时间描述' },
  { key: 'goal', label: '场景目标', textarea: true },
  { key: 'conflict', label: '冲突', textarea: true },
  { key: 'turning_point', label: '转折点', textarea: true },
  { key: 'ending_hook', label: '结尾钩子', textarea: true },
];

export function SceneCardEditor({
  scene,
  characters = [],
  worldEntries = [],
}: Props) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});

  const contextLinks = useQuery({
    queryKey: ['scene-context-links', scene?.id],
    queryFn: () => apiClient.getSceneContextLinks(scene?.id ?? ''),
    enabled: Boolean(scene?.id),
  });

  const saveContextLinks = useMutation({
    mutationFn: (payload: SceneContextLinks) =>
      apiClient.replaceSceneContextLinks(scene?.id ?? '', payload),
    onSuccess: (links) => {
      queryClient.setQueryData(['scene-context-links', scene?.id], links);
      queryClient.invalidateQueries({ queryKey: ['context', scene?.id] });
    },
  });

  function toggleContextLink(
    kind: 'character_ids' | 'world_entry_ids',
    id: string,
  ) {
    const current = contextLinks.data ?? {
      character_ids: [],
      world_entry_ids: [],
    };
    const selected = new Set(current[kind]);
    if (selected.has(id)) selected.delete(id);
    else selected.add(id);
    saveContextLinks.mutate({
      ...current,
      [kind]: [...selected],
    });
  }

  const saveScene = useMutation({
    mutationFn: (payload: Record<string, string>) => {
      const { story_time_order, ...textFields } = payload;
      return apiClient.patchScene(scene?.id ?? '', {
        ...textFields,
        story_time_order: Number(story_time_order),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scene', scene?.id] });
      queryClient.invalidateQueries({ queryKey: ['scenes'] });
      setEditing(false);
    },
  });

  if (!scene) {
    return (
      <section className="rounded-md border border-slate-200 bg-white p-3 text-xs">
        <p className="text-slate-400 text-center py-4">未选择场景</p>
      </section>
    );
  }

  function startEdit() {
    const vals: Record<string, string> = {};
    FIELD_LABELS.forEach((f) => {
      vals[f.key] = String((scene as unknown as Record<string, unknown>)[f.key] ?? '');
    });
    vals.story_time_order = String(scene?.story_time_order ?? 1);
    setForm(vals);
    setEditing(true);
  }

  if (editing) {
    return (
      <section className="rounded-md border border-slate-200 bg-white p-3 text-xs space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-900">编辑场景卡</h3>
          <div className="flex gap-1">
            <button onClick={() => saveScene.mutate(form)} disabled={saveScene.isPending}
              className="flex items-center gap-1 rounded bg-emerald-600 px-2 py-1 text-xs text-white hover:bg-emerald-700">
              <Check size={12} /> 保存
            </button>
            <button onClick={() => setEditing(false)}
              className="rounded border px-2 py-1 text-xs hover:bg-slate-100">
              <X size={12} /> 取消
            </button>
          </div>
        </div>
        {FIELD_LABELS.map((f) => (
          <label key={f.key} className="block">
            <span className="font-medium text-slate-600">{f.label}</span>
            {f.textarea ? (
              <textarea value={form[f.key] ?? ''} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                rows={2} className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs outline-none focus:border-emerald-600" />
            ) : (
              <input value={form[f.key] ?? ''} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs outline-none focus:border-emerald-600" />
            )}
          </label>
        ))}
        <details className="rounded border border-slate-200 px-2 py-1.5">
          <summary className="cursor-pointer font-medium text-slate-600">
            高级设置
          </summary>
          <label className="mt-2 block">
            <span className="font-medium text-slate-600">故事时间序号</span>
            <input
              type="number"
              value={form.story_time_order ?? ''}
              onChange={(event) =>
                setForm({ ...form, story_time_order: event.target.value })
              }
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs outline-none focus:border-emerald-600"
            />
          </label>
        </details>
      </section>
    );
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-3 text-xs">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-900">场景卡</h3>
        <button onClick={startEdit} className="flex items-center gap-1 text-indigo-600 hover:text-indigo-800">
          <Pencil size={12} /> 编辑
        </button>
      </div>
      <div className="space-y-1.5">
        {FIELD_LABELS.map((f) => {
          const val = String((scene as unknown as Record<string, unknown>)[f.key] ?? '');
          if (!val.trim()) return null;
          return (
            <div key={f.key}>
              <span className="font-medium text-slate-600">{f.label}：</span>
              <span className="text-slate-500">{val}</span>
            </div>
          );
        })}
        <div><span className="font-medium text-slate-600">POV 人物：</span><span className="text-slate-500">{scene.pov_character_id || '未设定'}</span></div>
        <details className="rounded border border-slate-200 px-2 py-1.5">
          <summary className="cursor-pointer font-medium text-slate-600">
            高级设置
          </summary>
          <div className="mt-2">
            <span className="font-medium text-slate-600">故事时间序号：</span>
            <span className="text-slate-500">{scene.story_time_order}</span>
          </div>
          <div className="mt-2 border-t border-slate-100 pt-2">
            <p className="font-medium text-slate-600">相关人物</p>
            {characters.map((character) => (
              <label key={character.id} className="mt-1 flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={contextLinks.data?.character_ids.includes(character.id) ?? false}
                  onChange={() => toggleContextLink('character_ids', character.id)}
                />
                {character.name}
              </label>
            ))}
            <p className="mt-2 font-medium text-slate-600">相关世界观</p>
            {worldEntries.map((entry) => (
              <label key={entry.id} className="mt-1 flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={contextLinks.data?.world_entry_ids.includes(entry.id) ?? false}
                  onChange={() => toggleContextLink('world_entry_ids', entry.id)}
                />
                {entry.name}
              </label>
            ))}
          </div>
        </details>
      </div>
    </section>
  );
}
