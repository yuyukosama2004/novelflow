import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Check, RefreshCw, X } from "lucide-react";

import { apiClient } from "../../api/client";
import { IconButton } from "../../components/IconButton";
import { StatusPill } from "../../components/StatusPill";
import type {
  ChangeOperation,
  ChangeSet,
  SceneWorkingDraft,
} from "../../types/entities";
import { RichTextCodec, type RichTextNode } from "../../utils/richTextCodec";

interface Props {
  sceneId: string;
  disabledReason?: string;
  onDraftApplied?: (draft: SceneWorkingDraft) => void;
}

interface Decision {
  changeSetId: string;
  acceptIds: string[];
  rejectIds: string[];
}

const PURPOSE_LABELS: Record<ChangeSet["purpose"], string> = {
  generation: "生成",
  rewrite: "改写",
  review_fix: "审查修复",
  restore: "恢复",
  merge: "合并",
};

const CHANGE_SET_STATUS_LABELS: Record<ChangeSet["status"], string> = {
  pending: "待处理",
  partially_accepted: "部分已应用",
  accepted: "已接受",
  rejected: "已拒绝",
  conflicted: "存在冲突",
};

const OPERATION_LABELS: Record<ChangeOperation["operation_type"], string> = {
  insert_before: "在前方插入",
  insert_after: "在后方插入",
  replace_block: "替换段落",
  delete_block: "删除段落",
};

const OPERATION_STATUS_LABELS: Record<ChangeOperation["status"], string> = {
  pending: "待决定",
  accepted: "已接受",
  rejected: "已拒绝",
  conflicted: "冲突",
  orphaned: "目标丢失",
};

function renderBlock(
  value: Record<string, unknown>,
  emptyLabel: string,
): string {
  if (!value.type) {
    return emptyLabel;
  }
  try {
    return RichTextCodec.toMarkdown({
      type: "doc",
      content: [value as unknown as RichTextNode],
    });
  } catch {
    return JSON.stringify(value, null, 2);
  }
}

function operationPreview(operation: ChangeOperation) {
  if (
    operation.operation_type === "insert_before" ||
    operation.operation_type === "insert_after"
  ) {
    return {
      original: "（新增内容）",
      proposed: renderBlock(operation.proposed_json, "（空内容）"),
    };
  }
  if (operation.operation_type === "delete_block") {
    return {
      original: renderBlock(operation.original_json, "（原段落不可用）"),
      proposed: "（删除该段落）",
    };
  }
  return {
    original: renderBlock(operation.original_json, "（原段落不可用）"),
    proposed: renderBlock(operation.proposed_json, "（空内容）"),
  };
}

function errorReason(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return "";
  }
  const data = error.response?.data as
    | { details?: { reason?: string } }
    | undefined;
  return data?.details?.reason ?? "";
}

export function ChangeSetReviewPanel({
  sceneId,
  disabledReason = "",
  onDraftApplied,
}: Props) {
  const queryClient = useQueryClient();
  const [selectedChangeSetId, setSelectedChangeSetId] = useState("");
  const [message, setMessage] = useState("");

  const changeSetsQuery = useQuery({
    queryKey: ["change-sets", sceneId],
    queryFn: () => apiClient.listChangeSets(sceneId),
    enabled: Boolean(sceneId),
  });
  const draftQuery = useQuery({
    queryKey: ["scene-working-draft", sceneId],
    queryFn: () => apiClient.getWorkingDraft(sceneId),
    enabled: Boolean(sceneId),
  });

  const changeSets = changeSetsQuery.data ?? [];
  const activeChangeSetId = changeSets.some(
    (item) => item.id === selectedChangeSetId,
  )
    ? selectedChangeSetId
    : (changeSets[0]?.id ?? "");
  const activeChangeSet = changeSets.find(
    (item) => item.id === activeChangeSetId,
  );

  const applyDecision = useMutation({
    mutationFn: (decision: Decision) =>
      apiClient.applyChangeSet(decision.changeSetId, {
        expected_draft_revision: draftQuery.data?.revision ?? 0,
        accept_operation_ids: decision.acceptIds,
        reject_operation_ids: decision.rejectIds,
      }),
    onSuccess: (result) => {
      setMessage(result.draft ? "改动已应用到工作草稿。" : "审阅决定已保存。");
      queryClient.setQueryData<ChangeSet[]>(
        ["change-sets", sceneId],
        (current) =>
          current?.map((item) =>
            item.id === result.change_set.id ? result.change_set : item,
          ) ?? [result.change_set],
      );
      queryClient.setQueryData(
        ["change-set", result.change_set.id],
        result.change_set,
      );
      if (result.draft) {
        queryClient.setQueryData(
          ["scene-working-draft", sceneId],
          result.draft,
        );
        onDraftApplied?.(result.draft);
      }
    },
    onError: (error) => {
      if (errorReason(error) === "DRAFT_REVISION_CONFLICT") {
        setMessage("草稿已在别处变化，已刷新最新内容，请重新审阅。");
        queryClient.invalidateQueries({
          queryKey: ["scene-working-draft", sceneId],
        });
        queryClient.invalidateQueries({
          queryKey: ["change-sets", sceneId],
        });
        return;
      }
      setMessage("改动处理失败，请刷新后重试。");
    },
  });

  const isLoading =
    changeSetsQuery.isLoading ||
    changeSetsQuery.isFetching ||
    draftQuery.isLoading ||
    draftQuery.isFetching;
  const actionsDisabled =
    Boolean(disabledReason) ||
    isLoading ||
    applyDecision.isPending ||
    !draftQuery.data;
  const pendingOperations =
    activeChangeSet?.operations.filter((item) => item.status === "pending") ??
    [];

  function decide(operation: ChangeOperation, accept: boolean) {
    if (!activeChangeSet) return;
    setMessage("");
    applyDecision.mutate({
      changeSetId: activeChangeSet.id,
      acceptIds: accept ? [operation.id] : [],
      rejectIds: accept ? [] : [operation.id],
    });
  }

  function decideAll(accept: boolean) {
    if (!activeChangeSet || pendingOperations.length === 0) return;
    setMessage("");
    const ids = pendingOperations.map((item) => item.id);
    applyDecision.mutate({
      changeSetId: activeChangeSet.id,
      acceptIds: accept ? ids : [],
      rejectIds: accept ? [] : ids,
    });
  }

  function refresh() {
    setMessage("");
    queryClient.invalidateQueries({ queryKey: ["change-sets", sceneId] });
    queryClient.invalidateQueries({
      queryKey: ["scene-working-draft", sceneId],
    });
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-3 text-xs">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">改动审阅</h2>
          <p className="mt-1 text-slate-500">
            对 AI 提议逐项确认，接受后才写入工作草稿。
          </p>
        </div>
        <StatusPill
          tone={activeChangeSet?.status === "conflicted" ? "warn" : "neutral"}
        >
          {activeChangeSet
            ? CHANGE_SET_STATUS_LABELS[activeChangeSet.status]
            : "暂无改动"}
        </StatusPill>
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        <IconButton
          icon={<RefreshCw size={14} />}
          label="刷新"
          onClick={refresh}
          disabled={isLoading || !sceneId}
        />
        <IconButton
          icon={<Check size={14} />}
          label="接受全部待处理"
          tone="primary"
          onClick={() => decideAll(true)}
          disabled={actionsDisabled || pendingOperations.length === 0}
        />
        <IconButton
          icon={<X size={14} />}
          label="拒绝全部待处理"
          onClick={() => decideAll(false)}
          disabled={actionsDisabled || pendingOperations.length === 0}
        />
      </div>

      {disabledReason ? (
        <div className="mb-3 rounded-md border border-amber-200 bg-amber-50 p-2 text-amber-800">
          {disabledReason}
        </div>
      ) : null}
      {message ? (
        <div
          className={`mb-3 rounded-md border p-2 ${
            applyDecision.isError
              ? "border-amber-200 bg-amber-50 text-amber-800"
              : "border-emerald-200 bg-emerald-50 text-emerald-800"
          }`}
        >
          {message}
        </div>
      ) : null}
      {changeSetsQuery.isError || draftQuery.isError ? (
        <div className="mb-3 rounded-md border border-rose-200 bg-rose-50 p-2 text-rose-700">
          改动或草稿加载失败，请刷新后重试。
        </div>
      ) : null}

      {changeSets.length > 0 ? (
        <label className="mb-3 block text-slate-600">
          <span className="mb-1 block font-medium">改动批次</span>
          <select
            aria-label="改动批次"
            value={activeChangeSetId}
            onChange={(event) => {
              setSelectedChangeSetId(event.target.value);
              setMessage("");
            }}
            className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5"
          >
            {changeSets.map((item) => (
              <option key={item.id} value={item.id}>
                {PURPOSE_LABELS[item.purpose]} ·{" "}
                {CHANGE_SET_STATUS_LABELS[item.status]} ·{" "}
                {new Date(item.created_at).toLocaleString("zh-CN")}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {isLoading ? (
        <div className="py-4 text-center text-slate-500">加载改动记录…</div>
      ) : null}
      {!isLoading && changeSets.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-200 px-3 py-4 text-center text-slate-500">
          当前场景还没有待审阅的 AI 改动。
        </div>
      ) : null}

      {activeChangeSet ? (
        <div className="space-y-3">
          {activeChangeSet.summary ? (
            <p className="rounded-md bg-slate-50 p-2 text-slate-600">
              {activeChangeSet.summary}
            </p>
          ) : null}
          {activeChangeSet.operations.map((operation) => {
            const preview = operationPreview(operation);
            const isPending = operation.status === "pending";
            return (
              <article
                key={operation.id}
                className="rounded-md border border-slate-200 p-2.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="font-semibold text-slate-800">
                    #{operation.sequence_no}{" "}
                    {OPERATION_LABELS[operation.operation_type]}
                  </p>
                  <span className="text-[11px] text-slate-500">
                    {OPERATION_STATUS_LABELS[operation.status]}
                  </span>
                </div>
                <div className="mt-2 grid gap-2">
                  <div>
                    <p className="mb-1 font-medium text-rose-700">原文</p>
                    <pre className="whitespace-pre-wrap break-words rounded bg-rose-50 p-2 font-sans leading-5 text-slate-700">
                      {preview.original}
                    </pre>
                  </div>
                  <div>
                    <p className="mb-1 font-medium text-emerald-700">建议</p>
                    <pre className="whitespace-pre-wrap break-words rounded bg-emerald-50 p-2 font-sans leading-5 text-slate-700">
                      {preview.proposed}
                    </pre>
                  </div>
                </div>
                {operation.conflict_reason ? (
                  <p className="mt-2 rounded bg-amber-50 p-2 text-amber-800">
                    无法自动应用：{operation.conflict_reason}
                  </p>
                ) : null}
                {isPending ? (
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      onClick={() => decide(operation, true)}
                      disabled={actionsDisabled}
                      className="rounded border border-emerald-300 bg-emerald-50 px-2 py-1 font-medium text-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      接受
                    </button>
                    <button
                      type="button"
                      onClick={() => decide(operation, false)}
                      disabled={actionsDisabled}
                      className="rounded border border-slate-300 bg-white px-2 py-1 font-medium text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      拒绝
                    </button>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
