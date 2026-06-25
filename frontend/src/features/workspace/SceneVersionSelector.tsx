import { ChevronsUpDown, Layers } from 'lucide-react';

import { StatusPill } from '../../components/StatusPill';
import type { SceneVersion } from '../../types/entities';

interface Props {
  versions: SceneVersion[];
  approvedVersionId: string | null;
  selectedVersionId: string | null;
  onSelect: (versionId: string) => void;
}

const SOURCE_TYPE_LABELS: Record<string, string> = {
  ai_generated: 'AI',
  human_revised: 'Draft',
  approved: 'Approved',
};

function stripHtml(html: string): string {
  return html.replace(/<[^>]+>/g, '');
}

function versionPreview(version: SceneVersion): string {
  if (version.summary?.trim()) {
    return version.summary;
  }
  const text = stripHtml(version.content_markdown).trim();
  return text.slice(0, 100) || '(empty)';
}

function reviewStatusLabel(reviewStatus: string): string {
  if (!reviewStatus || reviewStatus === 'none') {
    return '';
  }
  return reviewStatus.replace(/_/g, ' ');
}

function sourceTypeLabel(sourceType: string): string {
  return SOURCE_TYPE_LABELS[sourceType] ?? sourceType;
}

export function SceneVersionSelector({
  versions,
  approvedVersionId,
  selectedVersionId,
  onSelect,
}: Props) {
  if (versions.length === 0) {
    return (
      <section className="rounded-md border border-slate-200 bg-white p-3 text-xs">
        <div className="flex items-center gap-2">
          <Layers size={14} className="text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-900">Scene Version</h2>
        </div>
        <p className="mt-2 text-slate-500">
          No versions yet. Generate or save a draft to create one.
        </p>
      </section>
    );
  }

  const sorted = [...versions].sort((a, b) => b.version_no - a.version_no);
  const selected = selectedVersionId
    ? versions.find((version) => version.id === selectedVersionId) ?? null
    : null;

  return (
    <section className="rounded-md border border-slate-200 bg-white p-3 text-xs">
      <div className="mb-2 flex items-center gap-2">
        <Layers size={14} className="text-slate-400" />
        <h2 className="text-sm font-semibold text-slate-900">Scene Version</h2>
      </div>

      <div className="relative">
        <select
          value={selected?.id ?? ''}
          onChange={(event) => onSelect(event.target.value)}
          aria-label="Select scene version for review and memory actions"
          className="w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-3 pr-8 text-sm text-slate-800 outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600"
        >
          {sorted.map((version) => {
            const isApproved = version.id === approvedVersionId;
            const reviewLabel = reviewStatusLabel(version.review_status);
            const labelParts = [`v${version.version_no}`, sourceTypeLabel(version.source_type)];
            if (isApproved) {
              labelParts.push('approved');
            }
            if (reviewLabel) {
              labelParts.push(reviewLabel);
            }

            return (
              <option key={version.id} value={version.id}>
                {labelParts.join(' / ')} - {versionPreview(version).slice(0, 60)}
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
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-medium text-slate-900">v{selected.version_no}</span>
            <StatusPill tone={selected.id === approvedVersionId ? 'ok' : 'neutral'}>
              {`${sourceTypeLabel(selected.source_type)}${
                selected.id === approvedVersionId ? ' (approved)' : ''
              }`}
            </StatusPill>
            {reviewStatusLabel(selected.review_status) ? (
              <StatusPill tone="neutral">
                {reviewStatusLabel(selected.review_status)}
              </StatusPill>
            ) : null}
          </div>
          <p className="mt-1 line-clamp-2 text-slate-500">{versionPreview(selected)}</p>
        </div>
      ) : null}
    </section>
  );
}
