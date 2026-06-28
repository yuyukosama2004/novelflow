import { useState } from 'react';
import { Check, Pencil, X } from 'lucide-react';

import type { Character } from '../../types/entities';

interface Props {
  character: Character;
  onSave: (id: string, payload: Record<string, unknown>) => void;
  isSaving: boolean;
}

export function CharacterDetailPanel({ character, onSave, isSaving }: Props) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});

  function startEdit() {
    setForm({
      name: character.name,
      role: character.role || '',
      age_text: character.age_text || '',
      appearance: character.appearance || '',
      background: character.background || '',
      public_identity: character.public_identity || '',
      secret_identity: character.secret_identity || '',
      core_desire: character.core_desire || '',
      core_fear: character.core_fear || '',
      decision_pattern: character.decision_pattern || '',
      stress_response: character.stress_response || '',
      speech_style: character.speech_style || '',
      arc_plan: character.arc_plan || '',
    });
    setEditing(true);
  }

  function handleSave() {
    onSave(character.id, form);
    setEditing(false);
  }

  const fields = [
    { key: 'name', label: '姓名' },
    { key: 'role', label: '身份' },
    { key: 'age_text', label: '年龄' },
    { key: 'appearance', label: '外貌', textarea: true },
    { key: 'background', label: '背景', textarea: true },
    { key: 'public_identity', label: '公开身份', textarea: true },
    { key: 'secret_identity', label: '秘密身份', textarea: true },
    { key: 'core_desire', label: '核心欲望', textarea: true },
    { key: 'core_fear', label: '核心恐惧', textarea: true },
    { key: 'decision_pattern', label: '决策模式', textarea: true },
    { key: 'stress_response', label: '应激反应', textarea: true },
    { key: 'speech_style', label: '说话风格', textarea: true },
    { key: 'arc_plan', label: '成长弧线', textarea: true },
  ];

  if (editing) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">编辑人物</h3>
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
        </div>
        {fields.map((f) => (
          <label key={f.key} className="block text-sm">
            <span className="font-medium text-slate-700">{f.label}</span>
            {f.textarea ? (
              <textarea value={form[f.key] ?? ''} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                rows={2} className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-emerald-600" />
            ) : (
              <input value={form[f.key] ?? ''} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-emerald-600" />
            )}
          </label>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-900">{character.name}</h3>
        <button onClick={startEdit} className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800">
          <Pencil size={13} /> 编辑
        </button>
      </div>
      <div className="grid gap-1.5 text-sm">
        {fields.map((f) => {
          const val = (character as unknown as Record<string, unknown>)[f.key];
          if (!val || (typeof val === 'string' && !val.trim())) return null;
          return (
            <div key={f.key}>
              <span className="font-medium text-slate-600">{f.label}：</span>
              <span className="text-slate-500">{String(val)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
