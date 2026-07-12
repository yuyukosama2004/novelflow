import { ChevronsUpDown, Layers } from "lucide-react";

import type { SceneVersion } from "../../types/entities";

interface Props {
  versions: SceneVersion[];
  approvedVersionId: string | null;
  selectedVersionId: string | null;
  onSelect: (versionId: string) => void;
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]+>/g, "");
}

function versionPreview(version: SceneVersion): string {
  const summary = version.summary?.trim();
  const content = stripHtml(version.content_markdown).trim();
  const looksLikeRawOpening =
    Boolean(summary) &&
    (summary!.length > 120 ||
      content.startsWith(summary!.replace(/\.\.\.$/, "")));
  if (summary && !looksLikeRawOpening) {
    return version.summary;
  }
  return "未填写内容梗概";
}

function versionSourceLabel(sourceType: string): string {
  if (sourceType === "ai_generated") return "生成";
  if (sourceType === "ai_revised") return "重写";
  if (sourceType === "ai_polished") return "润色";
  return "人工";
}

function versionWordCount(version: SceneVersion): number {
  return stripHtml(version.content_markdown).replace(/\s+/g, "").length;
}

export function SceneVersionSelector({
  versions,
  selectedVersionId,
  onSelect,
}: Props) {
  if (versions.length === 0) {
    return (
      <section className="rounded-md border border-slate-200 bg-white p-3 text-xs">
        <div className="flex items-center gap-2">
          <Layers size={14} className="text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-900">场景版本</h2>
        </div>
        <p className="mt-2 text-slate-500">
          暂无版本，请生成或保存草稿以创建版本。
        </p>
      </section>
    );
  }

  const sorted = [...versions].sort((a, b) => b.version_no - a.version_no);
  const selected = selectedVersionId
    ? (versions.find((version) => version.id === selectedVersionId) ?? null)
    : null;

  return (
    <section className="rounded-md border border-slate-200 bg-white p-3 text-xs">
      <div className="mb-2 flex items-center gap-2">
        <Layers size={14} className="text-slate-400" />
        <h2 className="text-sm font-semibold text-slate-900">场景版本</h2>
      </div>

      <div className="relative">
        <select
          value={selected?.id ?? ""}
          onChange={(event) => onSelect(event.target.value)}
          aria-label="选择用于审查和记忆操作的场景版本"
          className="w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-8 text-sm text-slate-800 outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600"
        >
          {sorted.map((version) => {
            return (
              <option key={version.id} value={version.id}>
                v{version.version_no} /{" "}
                {versionSourceLabel(version.source_type)} /{" "}
                {versionPreview(version).slice(0, 60)} /{" "}
                {versionWordCount(version)} 字
              </option>
            );
          })}
        </select>
        <ChevronsUpDown
          size={14}
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
        />
      </div>

      {selected ? (
        <div className="mt-2 rounded-md border border-slate-100 bg-slate-50 p-2">
          <div className="flex flex-wrap items-center gap-1.5 text-slate-700">
            <span className="font-medium text-slate-900">
              v{selected.version_no}
            </span>
            <span>/</span>
            <span>{versionSourceLabel(selected.source_type)}</span>
            <span>/</span>
            <span>{versionWordCount(selected)} 字</span>
          </div>
          <p className="mt-1 line-clamp-2 text-slate-500">
            内容梗概：{versionPreview(selected)}
          </p>
        </div>
      ) : null}
    </section>
  );
}
