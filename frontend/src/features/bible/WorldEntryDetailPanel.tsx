import { useState } from "react";
import { Check, Pencil, X } from "lucide-react";

import type { WorldEntry } from "../../types/entities";
import { label, CANON_STATUS_LABELS } from "../../utils/enumLabels";

interface Props {
  entry: WorldEntry;
  onSave: (id: string, payload: Record<string, unknown>) => void;
  isSaving: boolean;
}

export function WorldEntryDetailPanel({ entry, onSave, isSaving }: Props) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});

  function startEdit() {
    setForm({
      name: entry.name,
      entry_type: entry.entry_type || "custom",
      summary: entry.summary || "",
      content: entry.content || "",
    });
    setEditing(true);
  }

  function handleSave() {
    onSave(entry.id, form);
    setEditing(false);
  }

  if (editing) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">编辑世界观</h3>
          <div className="flex gap-1">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-1 rounded bg-emerald-600 px-2 py-1 text-xs text-white hover:bg-emerald-700"
            >
              <Check size={13} /> 保存
            </button>
            <button
              onClick={() => setEditing(false)}
              className="rounded border px-2 py-1 text-xs hover:bg-slate-100"
            >
              <X size={13} /> 取消
            </button>
          </div>
        </div>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">名称</span>
          <input
            value={form.name ?? ""}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-emerald-600"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">类型</span>
          <input
            value={form.entry_type ?? ""}
            onChange={(e) => setForm({ ...form, entry_type: e.target.value })}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-emerald-600"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">摘要</span>
          <textarea
            value={form.summary ?? ""}
            onChange={(e) => setForm({ ...form, summary: e.target.value })}
            rows={2}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-emerald-600"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">详细内容</span>
          <textarea
            value={form.content ?? ""}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
            rows={4}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-emerald-600"
          />
        </label>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-slate-900">{entry.name}</h3>
          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
            {entry.entry_type}
          </span>
          <span className="text-xs text-slate-400">
            {label(CANON_STATUS_LABELS, entry.canon_status)}
          </span>
        </div>
        <button
          onClick={startEdit}
          className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800"
        >
          <Pencil size={13} /> 编辑
        </button>
      </div>
      {entry.summary ? (
        <p className="text-sm text-slate-600">{entry.summary}</p>
      ) : null}
      {entry.content ? (
        <p className="text-sm text-slate-500 whitespace-pre-wrap">
          {entry.content}
        </p>
      ) : null}
    </div>
  );
}
