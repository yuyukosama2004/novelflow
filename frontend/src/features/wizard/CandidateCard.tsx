import { useState } from "react";
import { Check, ChevronDown, ChevronUp, Pencil, X } from "lucide-react";

import type { StoryCandidateEntity } from "../../types/entities";

const CANDIDATE_TYPE_LABELS: Record<string, string> = {
  project_setting: "项目设定",
  character: "人物",
  world_entry: "世界观",
};

interface Props {
  candidate: StoryCandidateEntity;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onEdit: (id: string, contentJson: Record<string, unknown>) => void;
  onApply: (id: string) => void;
  isUpdating: boolean;
}

function candidateSummary(candidate: StoryCandidateEntity): string {
  const c = candidate.content_json as Record<string, string>;
  switch (candidate.candidate_type) {
    case "character":
      return [c.name, c.role].filter(Boolean).join(" — ") || candidate.title;
    case "world_entry":
      return (c.summary || c.name || candidate.title) as string;
    case "project_setting":
      return [c.genre, c.tone].filter(Boolean).join(" · ") || candidate.title;
    default:
      return candidate.title;
  }
}

export function CandidateCard({
  candidate,
  onApprove,
  onReject,
  onEdit,
  onApply,
  isUpdating,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editJson, setEditJson] = useState("");

  const typeLabel =
    CANDIDATE_TYPE_LABELS[candidate.candidate_type] ?? candidate.candidate_type;
  const summary = candidateSummary(candidate);
  const isApplied = Boolean(candidate.applied_entity_id);

  function startEdit() {
    setEditJson(JSON.stringify(candidate.content_json, null, 2));
    setEditing(true);
  }

  function saveEdit() {
    try {
      const parsed = JSON.parse(editJson);
      onEdit(candidate.id, parsed);
      setEditing(false);
    } catch {
      // keep editing on parse error
    }
  }

  return (
    <div
      className={`rounded-md border p-3 text-xs ${
        candidate.status === "approved"
          ? "border-emerald-200 bg-emerald-50"
          : candidate.status === "rejected"
            ? "border-slate-100 bg-slate-50 opacity-60"
            : "border-amber-200 bg-amber-50"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="rounded bg-white px-1.5 py-0.5 font-medium text-slate-600">
              {typeLabel}
            </span>
            <span className="font-medium text-slate-900 truncate">
              {candidate.title}
            </span>
            {candidate.confidence > 0 && (
              <span className="text-slate-400">
                {(candidate.confidence * 100).toFixed(0)}%
              </span>
            )}
          </div>
          <p className="mt-1 text-slate-600">{summary}</p>

          {candidate.proposal && (
            <p className="mt-1 text-slate-400 italic">
              依据：{candidate.proposal}
            </p>
          )}

          {expanded ? (
            <div className="mt-2">
              <pre className="max-h-40 overflow-auto rounded bg-white p-2 text-slate-600 whitespace-pre-wrap">
                {editing
                  ? editJson
                  : JSON.stringify(candidate.content_json, null, 2)}
              </pre>
              {editing && (
                <div className="mt-1 flex gap-1">
                  <button
                    onClick={saveEdit}
                    className="rounded bg-emerald-600 px-2 py-0.5 text-white text-xs hover:bg-emerald-700"
                  >
                    保存
                  </button>
                  <button
                    onClick={() => setEditing(false)}
                    className="rounded border border-slate-300 px-2 py-0.5 text-xs hover:bg-slate-100"
                  >
                    取消
                  </button>
                </div>
              )}
            </div>
          ) : null}

          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-1 flex items-center gap-1 text-slate-400 hover:text-slate-600"
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {expanded ? "收起" : "展开详情"}
          </button>
        </div>

        {candidate.status === "pending" ? (
          <div className="flex shrink-0 items-center gap-1">
            <button
              onClick={() => onApprove(candidate.id)}
              disabled={isUpdating}
              title="确认"
              className="rounded p-1.5 text-emerald-600 hover:bg-emerald-100 disabled:opacity-50"
            >
              <Check size={14} />
            </button>
            <button
              onClick={startEdit}
              disabled={isUpdating}
              title="编辑"
              className="rounded p-1.5 text-slate-500 hover:bg-slate-100 disabled:opacity-50"
            >
              <Pencil size={14} />
            </button>
            <button
              onClick={() => onReject(candidate.id)}
              disabled={isUpdating}
              title="拒绝"
              className="rounded p-1.5 text-rose-600 hover:bg-rose-100 disabled:opacity-50"
            >
              <X size={14} />
            </button>
          </div>
        ) : candidate.status === "approved" && !isApplied ? (
          <button
            onClick={() => onApply(candidate.id)}
            disabled={isUpdating}
            className="shrink-0 rounded bg-emerald-600 px-2 py-1 text-xs text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            应用
          </button>
        ) : isApplied ? (
          <span className="shrink-0 text-xs text-emerald-600 font-medium">
            已应用
          </span>
        ) : null}
      </div>
    </div>
  );
}
