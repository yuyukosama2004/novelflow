import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, EyeOff, RefreshCw, Search, X } from 'lucide-react';

import { apiClient } from '../../api/client';
import { IconButton } from '../../components/IconButton';
import { StatusPill } from '../../components/StatusPill';
import type {
  ReviewIssue,
  ReviewIssueStatus,
  ReviewRunStatus,
} from '../../types/entities';
import {
  label,
  ISSUE_STATUS_LABELS,
  ISSUE_TYPE_LABELS,
  REVIEW_SEVERITY_LABELS,
} from '../../utils/enumLabels';

interface Props {
  sceneVersionId: string;
  modelProfileId?: string;
}

type IssueAction = Exclude<ReviewIssueStatus, 'open'>;

const SEVERITY_TONE: Record<string, 'neutral' | 'ok' | 'warn'> = {
  low: 'ok',
  medium: 'neutral',
  high: 'warn',
  blocking: 'warn',
};

const RUN_STATUS_LABELS: Record<ReviewRunStatus, string> = {
  pending: '等待审查',
  running: '审查中',
  completed: '审查完成',
  failed: '审查失败',
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

function runOptionLabel(status: ReviewRunStatus, createdAt: string): string {
  return (
    RUN_STATUS_LABELS[status] +
    ' · ' +
    new Date(createdAt).toLocaleString('zh-CN')
  );
}

export function ReviewIssuePanel({ sceneVersionId, modelProfileId = '' }: Props) {
  const queryClient = useQueryClient();
  const [selectedRunId, setSelectedRunId] = useState('');
  const hasVersion = Boolean(sceneVersionId);

  const runsQuery = useQuery({
    queryKey: ['review-runs', sceneVersionId],
    queryFn: () => apiClient.listReviewRuns(sceneVersionId),
    enabled: hasVersion,
  });
  const runs = runsQuery.data ?? [];
  const activeRunId = runs.some((run) => run.id === selectedRunId)
    ? selectedRunId
    : (runs[0]?.id ?? '');

  const runQuery = useQuery({
    queryKey: ['review-run', activeRunId],
    queryFn: () => apiClient.getReviewRun(activeRunId),
    enabled: Boolean(activeRunId),
  });

  const runReview = useMutation({
    mutationFn: () =>
      modelProfileId
        ? apiClient.runReview(sceneVersionId, modelProfileId)
        : apiClient.runReview(sceneVersionId),
    onSuccess: (result) => {
      setSelectedRunId(result.run.id);
      queryClient.setQueryData(['review-run', result.run.id], result);
      queryClient.invalidateQueries({
        queryKey: ['review-runs', sceneVersionId],
      });
    },
  });

  const updateIssue = useMutation({
    mutationFn: ({
      issueId,
      status,
    }: {
      issueId: string;
      status: IssueAction;
    }) => apiClient.updateIssue(issueId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['review-run', activeRunId],
      });
    },
  });

  const result = runQuery.data;
  const run = result?.run;
  const issues = result?.issues ?? [];
  const isRunning = runReview.isPending || run?.status === 'running';
  const isLoading =
    runsQuery.isLoading ||
    runsQuery.isFetching ||
    runQuery.isLoading ||
    runQuery.isFetching ||
    runReview.isPending;
  const hasError =
    runsQuery.isError ||
    runQuery.isError ||
    runReview.isError ||
    updateIssue.isError;

  function refresh() {
    queryClient.invalidateQueries({
      queryKey: ['review-runs', sceneVersionId],
    });
    if (activeRunId) {
      queryClient.invalidateQueries({
        queryKey: ['review-run', activeRunId],
      });
    }
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-3 text-xs">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">连续性审查</h2>
          <p className="mt-1 text-slate-500">
            在批准前检查当前版本是否存在故事设定冲突。
          </p>
        </div>
        <StatusPill
          tone={
            issues.length > 0 || run?.status === 'failed' ? 'warn' : 'neutral'
          }
        >
          {!hasVersion
            ? '暂无版本'
            : run
              ? RUN_STATUS_LABELS[run.status]
              : '尚未审查'}
        </StatusPill>
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        <IconButton
          icon={<Search size={14} />}
          label={isRunning ? '审查中…' : '执行审查'}
          tone="primary"
          onClick={() => runReview.mutate()}
          disabled={isRunning || !hasVersion}
        />
        <IconButton
          icon={<RefreshCw size={14} />}
          label="刷新"
          onClick={refresh}
          disabled={isLoading || !hasVersion}
        />
      </div>

      {runs.length > 0 ? (
        <label className="mb-3 block text-slate-600">
          <span className="mb-1 block font-medium">审查轮次</span>
          <select
            aria-label="审查轮次"
            value={activeRunId}
            onChange={(event) => setSelectedRunId(event.target.value)}
            className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5"
          >
            {runs.map((item) => (
              <option key={item.id} value={item.id}>
                {runOptionLabel(item.status, item.created_at)}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {!hasVersion ? (
        <div className="rounded-md border border-dashed border-slate-200 px-3 py-4 text-center text-slate-500">
          请先保存、生成或批准场景版本，再进行审查。
        </div>
      ) : null}

      {hasError ? (
        <div className="mb-3 rounded-md border border-rose-200 bg-rose-50 p-2 text-rose-700">
          审查操作失败，请刷新后重试。
        </div>
      ) : null}

      {hasVersion && isLoading ? (
        <div className="py-4 text-center text-slate-500">
          {isRunning ? '正在执行连续性审查…' : '加载审查记录…'}
        </div>
      ) : null}

      {hasVersion && !isLoading && !hasError && runs.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-200 px-3 py-4 text-center text-slate-500">
          尚未执行审查。
        </div>
      ) : null}

      {!isLoading && !hasError && run?.status === 'failed' ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-4 text-center text-rose-700">
          本轮审查失败，请重新执行审查。
        </div>
      ) : null}

      {!isLoading &&
      !hasError &&
      run?.status === 'completed' &&
      issues.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-200 px-3 py-4 text-center text-slate-500">
          {run.summary || '本轮未发现问题。'}
        </div>
      ) : null}

      {!isLoading && issues.length > 0 ? (
        <div className="max-h-80 space-y-2 overflow-auto">
          {issues.map((issue: ReviewIssue) => (
            <div
              key={issue.id}
              className="rounded-md border border-slate-200 bg-slate-50 p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span
                      className={[
                        'font-medium',
                        severityLabelColor(issue.severity),
                      ].join(' ')}
                    >
                      {label(ISSUE_TYPE_LABELS, issue.issue_type)}
                    </span>
                    <StatusPill
                      tone={SEVERITY_TONE[issue.severity] ?? 'neutral'}
                    >
                      {label(REVIEW_SEVERITY_LABELS, issue.severity)}
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
                      {label(ISSUE_STATUS_LABELS, issue.status)}
                    </StatusPill>
                    {issue.confidence < 1 ? (
                      <span className="text-slate-400">
                        {(issue.confidence * 100).toFixed(0)}%
                      </span>
                    ) : null}
                  </div>

                  {issue.conflict_rule ? (
                    <p className="mt-2 text-slate-600">
                      <span className="font-medium">规则：</span>{' '}
                      {issue.conflict_rule}
                    </p>
                  ) : null}
                  {issue.suggestion ? (
                    <p className="mt-1 text-slate-500">
                      <span className="font-medium">建议：</span>{' '}
                      {issue.suggestion}
                    </p>
                  ) : null}
                  {issue.evidence_json ? (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-slate-400 hover:text-slate-600">
                        证据
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
                        updateIssue.mutate({
                          issueId: issue.id,
                          status: 'accepted',
                        })
                      }
                      disabled={updateIssue.isPending}
                      title="接受"
                      aria-label="接受问题"
                      className="rounded p-1 text-emerald-600 hover:bg-emerald-50 disabled:opacity-50"
                    >
                      <Check size={14} />
                    </button>
                    <button
                      onClick={() =>
                        updateIssue.mutate({
                          issueId: issue.id,
                          status: 'ignored',
                        })
                      }
                      disabled={updateIssue.isPending}
                      title="忽略"
                      aria-label="忽略问题"
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
                      title="标记误报"
                      aria-label="标记为误报"
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
