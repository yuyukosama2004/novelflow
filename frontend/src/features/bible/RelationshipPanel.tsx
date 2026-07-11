import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import type { Character, CharacterRelationship } from "../../types/entities";

const RELATION_TYPE_LABELS: Record<string, string> = {
  ally: "盟友",
  rival: "对手",
  lover: "恋人",
  family: "家人",
  mentor: "师徒",
  conflict: "利益冲突",
  secret: "秘密关联",
  other: "其他",
};

interface Props {
  relationships: CharacterRelationship[];
  characters: Character[];
  onCreate: (payload: {
    character_a_id: string;
    character_b_id: string;
    relation_type: string;
    description: string;
    timeline_info: string;
  }) => void;
  onDelete: (id: string) => void;
  isCreating: boolean;
}

export function RelationshipPanel({
  relationships,
  characters,
  onCreate,
  onDelete,
  isCreating,
}: Props) {
  const [adding, setAdding] = useState(false);
  const [charA, setCharA] = useState("");
  const [charB, setCharB] = useState("");
  const [relType, setRelType] = useState("other");
  const [desc, setDesc] = useState("");
  const [timeline, setTimeline] = useState("");

  function handleCreate() {
    if (!charA || !charB) return;
    onCreate({
      character_a_id: charA,
      character_b_id: charB,
      relation_type: relType,
      description: desc,
      timeline_info: timeline,
    });
    setCharA("");
    setCharB("");
    setRelType("other");
    setDesc("");
    setTimeline("");
    setAdding(false);
  }

  function charName(id: string): string {
    return characters.find((c) => c.id === id)?.name ?? id.slice(0, 8);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">人物关系</h2>
        <button
          onClick={() => setAdding(!adding)}
          className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800"
        >
          <Plus size={13} /> 添加关系
        </button>
      </div>

      {adding ? (
        <div className="rounded-md border border-indigo-200 bg-indigo-50 p-3 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs">
              <span className="font-medium">人物 A</span>
              <select
                value={charA}
                onChange={(e) => setCharA(e.target.value)}
                className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs outline-none focus:border-emerald-600"
              >
                <option value="">选择…</option>
                {characters.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs">
              <span className="font-medium">人物 B</span>
              <select
                value={charB}
                onChange={(e) => setCharB(e.target.value)}
                className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs outline-none focus:border-emerald-600"
              >
                <option value="">选择…</option>
                {characters.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="block text-xs">
            <span className="font-medium">关系类型</span>
            <select
              value={relType}
              onChange={(e) => setRelType(e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs outline-none focus:border-emerald-600"
            >
              {Object.entries(RELATION_TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs">
            <span className="font-medium">描述</span>
            <input
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs outline-none focus:border-emerald-600"
            />
          </label>
          <label className="block text-xs">
            <span className="font-medium">时间线背景</span>
            <input
              value={timeline}
              onChange={(e) => setTimeline(e.target.value)}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs outline-none focus:border-emerald-600"
            />
          </label>
          <div className="flex gap-1">
            <button
              onClick={handleCreate}
              disabled={!charA || !charB || isCreating}
              className="rounded bg-emerald-600 px-2 py-1 text-xs text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              保存
            </button>
            <button
              onClick={() => setAdding(false)}
              className="rounded border px-2 py-1 text-xs hover:bg-slate-100"
            >
              取消
            </button>
          </div>
        </div>
      ) : null}

      {relationships.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-slate-400">
          暂无人物关系，点击「添加关系」创建。
        </div>
      ) : (
        <div className="space-y-2">
          {relationships.map((rel) => (
            <div
              key={rel.id}
              className="flex items-start justify-between rounded-md border border-slate-200 bg-white p-3"
            >
              <div className="min-w-0 text-sm">
                <span className="font-medium text-slate-900">
                  {charName(rel.character_a_id)}
                </span>
                <span className="mx-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                  {RELATION_TYPE_LABELS[rel.relation_type] ?? rel.relation_type}
                </span>
                <span className="font-medium text-slate-900">
                  {charName(rel.character_b_id)}
                </span>
                {rel.description ? (
                  <p className="mt-1 text-xs text-slate-500">
                    {rel.description}
                  </p>
                ) : null}
              </div>
              <button
                onClick={() => onDelete(rel.id)}
                className="shrink-0 rounded p-1 text-rose-400 hover:bg-rose-50 hover:text-rose-600"
                title="删除"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
