import { useState } from 'react';
import { Check, Pencil, X } from 'lucide-react';

import type { NovelProject } from '../../types/entities';

interface Props {
  project: NovelProject | undefined;
  isLoading: boolean;
  onSave: (payload: Record<string, string>) => void;
  isSaving: boolean;
}

export function CoreConceptPanel({ project, isLoading, onSave, isSaving }: Props) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    title: '',
    genre: '',
    tone: '',
    summary: '',
  });

  if (isLoading) {
    return <div className="py-8 text-center text-sm text-slate-400">加载中…</div>;
  }
  if (!project) {
    return <div className="py-8 text-center text-sm text-slate-400">项目未加载</div>;
  }

  function startEdit() {
    setForm({
      title: project?.title ?? '',
      genre: project?.genre ?? '',
      tone: project?.tone ?? '',
      summary: project?.summary ?? '',
    });
    setEditing(true);
  }

  function handleSave() {
    onSave(form);
    setEditing(false);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">核心概念</h2>
        {!editing ? (
          <button onClick={startEdit} className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800">
            <Pencil size={13} /> 编辑
          </button>
        ) : (
          <div className="flex gap-1">
            <button onClick={handleSave} disabled={isSaving}
              className="flex items-center gap-1 rounded bg-emerald-600 px-2 py-1 text-xs text-white hover:bg-emerald-700">
              <Check size={13} /> 保存
            </button>
            <button onClick={() => setEditing(false)}
              className="rounded border px-2 py-1 text-xs hover:bg-slate-100">
              <X size={13} /> 取消
            </button>
          </div>
        )}
      </div>

      {editing ? (
        <div className="grid gap-3">
          <label className="block text-sm">
            <span className="font-medium text-slate-700">书名</span>
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-600" />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">类型</span>
            <input value={form.genre} onChange={(e) => setForm({ ...form, genre: e.target.value })}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-600" />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">基调</span>
            <input value={form.tone} onChange={(e) => setForm({ ...form, tone: e.target.value })}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-600" />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">简介 / 梗概</span>
            <textarea value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })}
              rows={4}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-600" />
          </label>
        </div>
      ) : (
        <div className="grid gap-2 text-sm">
          <div><span className="font-medium text-slate-600">书名：</span>{project.title}</div>
          <div><span className="font-medium text-slate-600">类型：</span>{project.genre || '未设定'}</div>
          <div><span className="font-medium text-slate-600">基调：</span>{project.tone || '未设定'}</div>
          <div><span className="font-medium text-slate-600">视角：</span>{project.pov_type || '未设定'}</div>
          <div><span className="font-medium text-slate-600">语言：</span>{project.language || 'zh-CN'}</div>
          <div className="mt-2">
            <span className="font-medium text-slate-600">梗概：</span>
            <p className="mt-1 text-slate-500">{project.summary || '暂无'}</p>
          </div>
        </div>
      )}
    </div>
  );
}
