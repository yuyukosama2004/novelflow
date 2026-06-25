import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, EyeOff, RefreshCw, Search, X } from 'lucide-react';

import { apiClient } from '../../api/client';
import { IconButton } from '../../components/IconButton';
import { StatusPill } from '../../components/StatusPill';
import type { ReviewIssue, ReviewIssueStatus } from '../../types/entities';

interface Props {
  sceneVersionId: string;
}

type IssueAction = Exclude<ReviewIssueStatus, 'open'>;

const SEVERITY_TONE: Record<string, 'neutral' | 'ok' | 'warn'> = {
  low: 'ok',
  medium: 'neutral',
  high: 'warn',
  blocking: 'warn',
};

const STATUS_LABELS: Record<ReviewIssueStatus, string> = {
  open: 'Open',
  accepted: 'Accepted',
  ignored: 'Ignored',
  false_positive: 'False positive',
};

function severityLabelColor(severity: string): string {
  if (severity === 'blocking' || severity === 'high') {
    return 'text-rose-700';
  }
  if (severity === 'medium') {
    return 'text-amber-700';
  }
  return 'text-emerald-700';
}

function formatEvidence(evidence: string): string {
  if (!evidence.trim()) {
    return '';
  }
  try {
    return JSON.stringify(JSON.parse(evidence), null, 2);
  } catch {
    return evidence;
  }
}

export function ReviewIssuePanel({ sceneVersionId }: Props) {
  const queryClient = useQueryClient();
  const hasVersion = Boolean(sceneVersionId);

  const issuesQuery = useQuery({
    queryKey: ['review-issues', sceneVersionId],
    queryFn: () => apiClient.listIssues(sceneVersionId),
    enabled: hasVersion,
  });

  const runReview = useMutation({
    mutationFn: () => apiClient.runReview(sceneVersionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-issues', sceneVersionId] });
    },
  });

  const updateIssue = useMutation({
    mutationFn: ({ issueId, status }: { issueId: string; status: IssueAction }) =>
      apiClient.updateIssue(issueId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-issues', sceneVersionId] });
    },
  });

  const issues = issuesQuery.data ?? [];
  const isRunning = runReview.isPending;
  const isLoading = issuesQuery.isLoading || issuesQuery.isFetching || isRunning;
  const hasError = issuesQuery.isError || runReview.isError || updateIssue.isError;

  return (
    <section className="rounded-md border border-slate-200 bg-white p-3 text-xs">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Continuity Review</h2>
          <p className="mt-1 text-slate-500">
            Check the current version against story context before approving it.
          </p>
        </div>
        <StatusPill tone={issues.length > 0 ? 'warn' : 'neutral'}>
          {hasVersion ? `${issues.length} issues` : 'No version'}
        </StatusPill>
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        <IconButton
          icon={<Search size={14} />}
          label={isRunning ? 'Reviewing' : 'Run review'}
          tone="primary"
          onClick={() => runReview.mutate()}
          disabled={isRunning || !hasVersion}
        />
        <IconButton
          icon={<RefreshCw size={14} />}
          label="Refresh"
          onClick={() =>
            queryClient.invalidateQueries({ queryKey: ['review-issues', sceneVersionId] })
          }
          disabled={isLoading || !hasVersion}
        />
      </div>

      {!hasVersion ? (
        <div className="rounded-md border border-dashed border-slate-200 px-3 py-4 text-center text-slate-500">
          Save, generate, or approve a scene version before running review.
        </div>
      ) : null}

      {hasError ? (
        <div className="mb-3 rounded-md border border-rose-200 bg-rose-50 p-2 text-rose-700">
          Review action failed. Please refresh and try again.
        </div>
      ) : null}

      {hasVersion && isLoading ? (
        <div className="py-4 text-center text-slate-500">
          {isRunning ? 'Running continuity review...' : 'Loading review issues...'}
        </div>
      ) : null}

      {hasVersion && !isLoading && !hasError && issues.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-200 px-3 py-4 text-center text-slate-500">
          No review issues yet. Run a review to check this version.
        </div>
      ) : null}

      {!isLoading && issues.length > 0 ? (
        <div className="max-h-80 space-y-2 overflow-auto">
          {issues.map((issue: ReviewIssue) => (
            <div key={issue.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className={`font-medium ${severityLabelColor(issue.severity)}`}>
                      {issue.issue_type.replace(/_/g, ' ')}
                    </span>
                    <StatusPill tone={SEVERITY_TONE[issue.severity] ?? 'neutral'}>
                      {issue.severity}
                    </StatusPill>
                    <StatusPill
                      tone={
                        issue.status === 'accepted'
                          ? 'ok'
                          : issue.status === 'open'
                            ? 'warn'
                            : 'neutral'
                      }
                    >
                      {STATUS_LABELS[issue.status]}
                    </StatusPill>
                    {issue.confidence < 1 ? (
                      <span className="text-slate-400">
                        {(issue.confidence * 100).toFixed(0)}%
                      </span>
                    ) : null}
                  </div>

                  {issue.conflict_rule ? (
                    <p className="mt-2 text-slate-600">
                      <span className="font-medium">Rule:</span> {issue.conflict_rule}
                    </p>
                  ) : null}
                  {issue.suggestion ? (
                    <p className="mt-1 text-slate-500">
                      <span className="font-medium">Suggestion:</span> {issue.suggestion}
                    </p>
                  ) : null}
                  {issue.evidence_json ? (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-slate-400 hover:text-slate-600">
                        Evidence
                      </summary>
                      <pre className="mt-1 max-h-28 overflow-auto whitespace-pre-wrap rounded bg-white p-2 text-slate-600">
                        {formatEvidence(issue.evidence_json)}
                      </pre>
                    </details>
                  ) : null}
                </div>

                {issue.status === 'open' ? (
                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      onClick={() =>
                        updateIssue.mutate({ issueId: issue.id, status: 'accepted' })
                      }
                      disabled={updateIssue.isPending}
                      title="Accept"
                      aria-label="Accept issue"
                      className="rounded p-1 text-emerald-600 hover:bg-emerald-50 disabled:opacity-50"
                    >
                      <Check size={14} />
                    </button>
                    <button
                      onClick={() =>
                        updateIssue.mutate({ issueId: issue.id, status: 'ignored' })
                      }
                      disabled={updateIssue.isPending}
                      title="Ignore"
                      aria-label="Ignore issue"
                      className="rounded p-1 text-amber-600 hover:bg-amber-50 disabled:opacity-50"
                    >
                      <EyeOff size={14} />
                    </button>
                    <button
                      onClick={() =>
                        updateIssue.mutate({
                          issueId: issue.id,
                          status: 'false_positive',
                        })
                      }
                      disabled={updateIssue.isPending}
                      title="Mark false positive"
                      aria-label="Mark issue false positive"
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
