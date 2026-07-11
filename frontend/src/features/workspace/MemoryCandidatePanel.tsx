import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Check, CheckCircle2, RefreshCw, Sparkles, X } from "lucide-react";

import { apiClient } from "../../api/client";
import { IconButton } from "../../components/IconButton";
import { StatusPill } from "../../components/StatusPill";
import type {
  MemoryCandidate,
  MemoryCandidateStatus,
} from "../../types/entities";
import {
  label,
  CANDIDATE_TYPE_LABELS,
  MEMORY_CANDIDATE_STATUS_LABELS,
} from "../../utils/enumLabels";

interface Props {
  sceneId?: string;
  sceneVersionId: string;
  approvedVersionId?: string | null;
  modelProfileId?: string;
}

type CandidateAction = Extract<MemoryCandidateStatus, "approved" | "rejected">;

const STATUS_TONE: Record<MemoryCandidateStatus, "neutral" | "ok" | "warn"> = {
  pending: "warn",
  approved: "ok",
  rejected: "neutral",
  conflicted: "warn",
  invalidated: "neutral",
};

function formatPayload(payload: Record<string, unknown>): string {
  return JSON.stringify(payload, null, 2);
}

function completionFailureMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) return "场景完成失败，请刷新后重试。";
  const data = error.response?.data as
    | { details?: { reason?: string } }
    | undefined;
  if (data?.details?.reason === "APPROVED_VERSION_REQUIRED") {
    return "请先批准一个正式版本。";
  }
  if (data?.details?.reason === "MEMORY_EXTRACTION_REQUIRED") {
    return "请先对正式版本提取记忆。";
  }
  if (data?.details?.reason === "PENDING_MEMORY_CANDIDATES") {
    return "请先处理完所有待确认的记忆候选。";
  }
  return "场景完成失败，请刷新后重试。";
}

export function MemoryCandidatePanel({
  sceneId,
  sceneVersionId,
  approvedVersionId,
  modelProfileId = "",
}: Props) {
  const queryClient = useQueryClient();
  const hasVersion = Boolean(sceneVersionId);
  const isApprovedVersion =
    approvedVersionId === undefined || approvedVersionId === sceneVersionId;

  const candidatesQuery = useQuery({
    queryKey: ["memory-candidates", sceneVersionId],
    queryFn: () => apiClient.listCandidates(sceneVersionId),
    enabled: hasVersion,
  });

  const extractionRunsQuery = useQuery({
    queryKey: ["memory-extraction-runs", sceneVersionId],
    queryFn: () => apiClient.listMemoryExtractionRuns(sceneVersionId),
    enabled: hasVersion,
  });

  const extractMemories = useMutation({
    mutationFn: () =>
      modelProfileId
        ? apiClient.extractMemories(sceneVersionId, modelProfileId)
        : apiClient.extractMemories(sceneVersionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["memory-candidates", sceneVersionId],
      });
      queryClient.invalidateQueries({
        queryKey: ["memory-extraction-runs", sceneVersionId],
      });
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
      queryClient.invalidateQueries({
        queryKey: ["memory-candidates", sceneVersionId],
      });
      queryClient.invalidateQueries({ queryKey: ["context"] });
    },
  });

  const completeScene = useMutation({
    mutationFn: () => apiClient.completeScene(sceneId ?? ""),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scene", sceneId] });
      queryClient.invalidateQueries({ queryKey: ["scenes"] });
    },
  });

  const candidates = candidatesQuery.data ?? [];
  const pendingCount = candidates.filter(
    (candidate) => candidate.status === "pending",
  ).length;
  const hasCompletedExtraction = (extractionRunsQuery.data ?? []).some(
    (run) => run.status === "completed",
  );
  const canComplete = Boolean(
    sceneId &&
    isApprovedVersion &&
    hasCompletedExtraction &&
    !candidatesQuery.isLoading &&
    !candidatesQuery.isFetching &&
    pendingCount === 0,
  );
  const isExtracting = extractMemories.isPending;
  const isLoading =
    candidatesQuery.isLoading ||
    candidatesQuery.isFetching ||
    extractionRunsQuery.isLoading ||
    isExtracting;
  const hasError =
    candidatesQuery.isError ||
    extractionRunsQuery.isError ||
    extractMemories.isError ||
    updateCandidate.isError;

  function resolveCandidate(candidateId: string, status: CandidateAction) {
    updateCandidate.mutate({ candidateId, status });
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-3 text-xs">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">记忆候选</h2>
          <p className="mt-1 text-slate-500">
            从此版本提取事实变更，仅批准应成为正史的内容。
          </p>
        </div>
        <StatusPill tone={pendingCount > 0 ? "warn" : "neutral"}>
          {hasVersion ? `${pendingCount} 条待确认` : "暂无版本"}
        </StatusPill>
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        <IconButton
          icon={<Sparkles size={14} />}
          label={isExtracting ? "提取中…" : "提取记忆"}
          tone="primary"
          onClick={() => extractMemories.mutate()}
          disabled={isExtracting || !hasVersion}
        />
        <IconButton
          icon={<RefreshCw size={14} />}
          label="刷新"
          onClick={() =>
            queryClient.invalidateQueries({
              queryKey: ["memory-candidates", sceneVersionId],
            })
          }
          disabled={isLoading || !hasVersion}
        />
        {sceneId ? (
          <IconButton
            icon={<CheckCircle2 size={14} />}
            label={completeScene.isPending ? "完成中…" : "完成场景"}
            onClick={() => completeScene.mutate()}
            disabled={!canComplete || completeScene.isPending}
          />
        ) : null}
      </div>

      {!hasVersion ? (
        <div className="rounded-md border border-dashed border-slate-200 px-3 py-4 text-center text-slate-500">
          请先保存、生成或批准场景版本，再进行记忆提取。
        </div>
      ) : null}

      {hasError ? (
        <div className="mb-3 rounded-md border border-rose-200 bg-rose-50 p-2 text-rose-700">
          记忆操作失败，请刷新后重试。
        </div>
      ) : null}

      {completeScene.isError ? (
        <div className="mb-3 rounded-md border border-rose-200 bg-rose-50 p-2 text-rose-700">
          {completionFailureMessage(completeScene.error)}
        </div>
      ) : null}

      {completeScene.isSuccess ? (
        <div className="mb-3 rounded-md border border-emerald-200 bg-emerald-50 p-2 text-emerald-700">
          场景已完成。
        </div>
      ) : null}

      {hasVersion && !isApprovedVersion ? (
        <div className="mb-3 rounded-md border border-amber-200 bg-amber-50 p-2 text-amber-800">
          这是草稿版本：可以提取和预览候选，也可以拒绝候选；只有当前正式版本的候选可以批准写入正史。
        </div>
      ) : null}

      {hasVersion && isLoading ? (
        <div className="py-4 text-center text-slate-500">
          {isExtracting ? "正在提取记忆候选…" : "加载候选…"}
        </div>
      ) : null}

      {hasVersion && !isLoading && !hasError && candidates.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-200 px-3 py-4 text-center text-slate-500">
          暂无记忆候选，请先审查草稿后再提取。
        </div>
      ) : null}

      {!isLoading && candidates.length > 0 ? (
        <div className="max-h-96 space-y-2 overflow-auto">
          {candidates.map((candidate: MemoryCandidate) => (
            <div
              key={candidate.id}
              className="rounded-md border border-slate-200 bg-slate-50 p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="font-medium text-slate-900">
                      {label(CANDIDATE_TYPE_LABELS, candidate.candidate_type)}
                    </span>
                    <StatusPill tone={STATUS_TONE[candidate.status]}>
                      {label(MEMORY_CANDIDATE_STATUS_LABELS, candidate.status)}
                    </StatusPill>
                    <span className="text-slate-400">
                      {(candidate.confidence * 100).toFixed(0)}%
                    </span>
                  </div>

                  {candidate.evidence ? (
                    <p className="mt-2 text-slate-600">
                      <span className="font-medium">证据：</span>{" "}
                      {candidate.evidence}
                    </p>
                  ) : null}

                  <details className="mt-1">
                    <summary className="cursor-pointer text-slate-400 hover:text-slate-600">
                      内容
                    </summary>
                    <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap rounded bg-white p-2 text-slate-600">
                      {formatPayload(candidate.content_json)}
                    </pre>
                  </details>
                </div>

                {candidate.status === "pending" ? (
                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      onClick={() => resolveCandidate(candidate.id, "approved")}
                      disabled={updateCandidate.isPending || !isApprovedVersion}
                      title={
                        isApprovedVersion
                          ? "批准"
                          : "只有正式版本的候选可以批准"
                      }
                      aria-label="批准记忆候选"
                      className="rounded p-1 text-emerald-600 hover:bg-emerald-50 disabled:opacity-50"
                    >
                      <Check size={14} />
                    </button>
                    <button
                      onClick={() => resolveCandidate(candidate.id, "rejected")}
                      disabled={updateCandidate.isPending}
                      title="拒绝"
                      aria-label="拒绝记忆候选"
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
