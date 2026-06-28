import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, Pencil, X } from 'lucide-react';

import { apiClient } from '../../api/client';
import type { Scene } from '../../types/entities';

interface Props {
  scene: Scene | null;
}

const FIELD_LABELS: { key: string; label: string; textarea?: boolean }[] = [
  { key: 'title', label: '场景标题' },
  { key: 'time_text', label: '时间描述' },
  { key: 'goal', label: '场景目标', textarea: true },
  { key: 'conflict', label: '冲突', textarea: true },
  { key: 'turning_point', label: '转折点', textarea: true },
  { key: 'ending_hook', label: '结尾钩子', textarea: true },
];

export function SceneCardEditor({ scene }: Props) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});

  const saveScene = useMutation({
    mutationFn: (payload: Record<string, string>) =>
      apiClient.patchScene(scene?.id ?? '', payload),
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
        <div><span className="font-medium text-slate-600">时间线序号：</span><span className="text-slate-500">{scene.timeline_order}</span></div>
      </div>
    </section>
  );
}
