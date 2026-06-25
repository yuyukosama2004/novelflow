import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, RefreshCw, Sparkles, X } from 'lucide-react';

import { apiClient } from '../../api/client';
import { IconButton } from '../../components/IconButton';
import { StatusPill } from '../../components/StatusPill';
import type { MemoryCandidate, MemoryCandidateStatus } from '../../types/entities';

interface Props {
  sceneVersionId: string;
}

type CandidateAction = Extract<MemoryCandidateStatus, 'approved' | 'rejected'>;

const STATUS_TONE: Record<MemoryCandidateStatus, 'neutral' | 'ok' | 'warn'> = {
  pending: 'warn',
  approved: 'ok',
  rejected: 'neutral',
  conflicted: 'warn',
};

function formatPayload(payload: Record<string, unknown>): string {
  return JSON.stringify(payload, null, 2);
}

function candidateTitle(candidate: MemoryCandidate): string {
  return candidate.candidate_type.replace(/_/g, ' ');
}

export function MemoryCandidatePanel({ sceneVersionId }: Props) {
  const queryClient = useQueryClient();
  const hasVersion = Boolean(sceneVersionId);

  const candidatesQuery = useQuery({
    queryKey: ['memory-candidates', sceneVersionId],
    queryFn: () => apiClient.listCandidates(sceneVersionId),
    enabled: hasVersion,
  });

  const extractMemories = useMutation({
    mutationFn: () => apiClient.extractMemories(sceneVersionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memory-candidates', sceneVersionId] });
    },
  });

  const updateCandidate = useMutation({
    mutationFn: ({
      candidateId,
      status,
    }: {
      candidateId: string;
      status: CandidateAction;
    }) => apiClient.updateCandidate(candidateId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memory-candidates', sceneVersionId] });
      queryClient.invalidateQueries({ queryKey: ['context'] });
    },
  });

  const candidates = candidatesQuery.data ?? [];
  const pendingCount = candidates.filter((candidate) => candidate.status === 'pending').length;
  const isExtracting = extractMemories.isPending;
  const isLoading = candidatesQuery.isLoading || candidatesQuery.isFetching || isExtracting;
  const hasError =
    candidatesQuery.isError || extractMemories.isError || updateCandidate.isError;

  function resolveCandidate(candidateId: string, status: CandidateAction) {
    updateCandidate.mutate({ candidateId, status });
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-3 text-xs">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Memory Candidates</h2>
          <p className="mt-1 text-slate-500">
            Extract facts from this version, then approve only what should become canon.
          </p>
        </div>
        <StatusPill tone={pendingCount > 0 ? 'warn' : 'neutral'}>
          {hasVersion ? `${pendingCount} pending` : 'No version'}
        </StatusPill>
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        <IconButton
          icon={<Sparkles size={14} />}
          label={isExtracting ? 'Extracting' : 'Extract'}
          tone="primary"
          onClick={() => extractMemories.mutate()}
          disabled={isExtracting || !hasVersion}
        />
        <IconButton
          icon={<RefreshCw size={14} />}
          label="Refresh"
          onClick={() =>
            queryClient.invalidateQueries({ queryKey: ['memory-candidates', sceneVersionId] })
          }
          disabled={isLoading || !hasVersion}
        />
      </div>

      {!hasVersion ? (
        <div className="rounded-md border border-dashed border-slate-200 px-3 py-4 text-center text-slate-500">
          Save, generate, or approve a scene version before extracting memory.
        </div>
      ) : null}

      {hasError ? (
        <div className="mb-3 rounded-md border border-rose-200 bg-rose-50 p-2 text-rose-700">
          Memory action failed. Please refresh and try again.
        </div>
      ) : null}

      {hasVersion && isLoading ? (
        <div className="py-4 text-center text-slate-500">
          {isExtracting ? 'Extracting memory candidates...' : 'Loading candidates...'}
        </div>
      ) : null}

      {hasVersion && !isLoading && !hasError && candidates.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-200 px-3 py-4 text-center text-slate-500">
          No memory candidates yet. Extract candidates after reviewing the draft.
        </div>
      ) : null}

      {!isLoading && candidates.length > 0 ? (
        <div className="max-h-96 space-y-2 overflow-auto">
          {candidates.map((candidate: MemoryCandidate) => (
            <div key={candidate.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="font-medium text-slate-900">
                      {candidateTitle(candidate)}
                    </span>
                    <StatusPill tone={STATUS_TONE[candidate.status]}>
                      {candidate.status}
                    </StatusPill>
                    <span className="text-slate-400">
                      {(candidate.confidence * 100).toFixed(0)}%
                    </span>
                  </div>

                  {candidate.evidence ? (
                    <p className="mt-2 text-slate-600">
                      <span className="font-medium">Evidence:</span> {candidate.evidence}
                    </p>
                  ) : null}

                  <details className="mt-1">
                    <summary className="cursor-pointer text-slate-400 hover:text-slate-600">
                      Payload
                    </summary>
                    <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap rounded bg-white p-2 text-slate-600">
                      {formatPayload(candidate.content_json)}
                    </pre>
                  </details>
                </div>

                {candidate.status === 'pending' ? (
                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      onClick={() => resolveCandidate(candidate.id, 'approved')}
                      disabled={updateCandidate.isPending}
                      title="Approve"
                      aria-label="Approve memory candidate"
                      className="rounded p-1 text-emerald-600 hover:bg-emerald-50 disabled:opacity-50"
                    >
                      <Check size={14} />
                    </button>
                    <button
                      onClick={() => resolveCandidate(candidate.id, 'rejected')}
                      disabled={updateCandidate.isPending}
                      title="Reject"
                      aria-label="Reject memory candidate"
                      className="rounded p-1 text-rose-600 hover:bg-rose-50 disabled:opacity-50"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
