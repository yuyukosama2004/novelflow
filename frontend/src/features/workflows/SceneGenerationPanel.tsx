import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiClient, createSSEStream, resumeSSEStream } from "../../api/client";
import { Button } from "../../components/ui/button";
import type { SceneVersion, SSEChunk } from "../../types/entities";

interface Props {
  sceneId: string;
  modelProfileId?: string;
  defaultTargetWordCount?: number;
  baseContent?: string;
  instructionFromDiscussion?: string;
  onVersionCreated?: (version: SceneVersion) => void;
}

export default function SceneGenerationPanel({
  sceneId,
  modelProfileId = "",
  defaultTargetWordCount = 1000,
  baseContent = "",
  instructionFromDiscussion = "",
  onVersionCreated,
}: Props) {
  const [generating, setGenerating] = useState(false);
  const [content, setContent] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [version, setVersion] = useState<SceneVersion | null>(null);
  const [runId, setRunId] = useState("");
  const [perspectiveWarning, setPerspectiveWarning] = useState("");
  const [generationMode, setGenerationMode] = useState<
    "new" | "rewrite" | "polish"
  >("new");
  const [instruction, setInstruction] = useState("");
  const [targetWordCount, setTargetWordCount] = useState(
    defaultTargetWordCount,
  );
  const controllerRef = useRef<AbortController | null>(null);
  const resumedRunIdRef = useRef("");
  const contentRef = useRef<HTMLPreElement>(null);
  const runs = useQuery({
    queryKey: ["workflow-runs", sceneId],
    queryFn: () => apiClient.listWorkflowRuns(sceneId),
    enabled: Boolean(sceneId),
  });
  const handleWorkflowEvent = useCallback(
    (data: SSEChunk) => {
      if (data.run_id) setRunId(data.run_id);
      if (data.error) {
        setError(data.error);
        setGenerating(false);
        return;
      }
      if (data.event === "draft_reset") {
        setContent("");
      }
      if (data.content_delta) {
        setContent((previous) => previous + data.content_delta);
      }
      if (data.version) {
        setVersion(data.version);
        if (onVersionCreated) onVersionCreated(data.version);
      }
      if (data.perspective_warning) {
        setPerspectiveWarning(data.perspective_warning);
      }
    },
    [onVersionCreated],
  );
  const handleWorkflowDone = useCallback(() => {
    controllerRef.current = null;
    setDone(true);
    setGenerating(false);
  }, []);
  const handleWorkflowError = useCallback((errorMessage: string) => {
    controllerRef.current = null;
    setError(errorMessage);
    setGenerating(false);
  }, []);

  useEffect(() => {
    const latest = runs.data?.[0];
    if (!latest) return;
    setRunId(latest.id);
    setContent(latest.draft || latest.final_content);
    const active = [
      "pending",
      "planning",
      "drafting",
      "queued",
      "running",
    ].includes(latest.status);
    setGenerating(active);
    setDone(["waiting_review", "done"].includes(latest.status));
    if (
      latest.status === "error" ||
      latest.status === "failed" ||
      latest.status === "cancelled"
    ) {
      setError(latest.error || "生成任务未完成");
    }
    if (active && resumedRunIdRef.current !== latest.id) {
      resumedRunIdRef.current = latest.id;
      controllerRef.current = resumeSSEStream(
        latest.id,
        latest.last_event_sequence,
        handleWorkflowEvent,
        handleWorkflowDone,
        handleWorkflowError,
      );
    }
  }, [handleWorkflowDone, handleWorkflowError, handleWorkflowEvent, runs.data]);

  useEffect(() => {
    setTargetWordCount(defaultTargetWordCount);
  }, [defaultTargetWordCount, sceneId]);

  useEffect(() => {
    if (!instructionFromDiscussion.trim()) return;
    setInstruction(instructionFromDiscussion);
    setGenerationMode("rewrite");
  }, [instructionFromDiscussion]);

  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [content]);

  function handleGenerate() {
    setGenerating(true);
    setContent("");
    setError("");
    setDone(false);
    setVersion(null);
    setPerspectiveWarning("");

    controllerRef.current = createSSEStream(
      sceneId,
      {
        modelProfileId,
        generationMode,
        instruction,
        baseContent,
        targetWordCount,
        idempotencyKey: crypto.randomUUID(),
      },
      handleWorkflowEvent,
      handleWorkflowDone,
      handleWorkflowError,
    );
  }

  function handleCancel() {
    controllerRef.current?.abort();
    if (runId) void apiClient.cancelWorkflowRun(runId);
    setGenerating(false);
    setError("用户已取消生成");
  }

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-panel">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-[11px] font-semibold tracking-[0.14em] text-brand-700">
              AI 草案
            </p>
            <h3 className="mt-1 text-sm font-semibold text-stone-900">
              场景生成
            </h3>
          </div>
          {!generating && (
            <Button
              onClick={handleGenerate}
              disabled={generationMode !== "new" && !baseContent.trim()}
              variant="primary"
              size="sm"
            >
              {done ? "重新生成" : "生成"}
            </Button>
          )}
          {generating && (
            <Button onClick={handleCancel} variant="danger" size="sm">
              取消
            </Button>
          )}
        </div>
        <p className="mt-2 text-xs leading-5 text-stone-500">
          生成结果会同步到正文和版本历史，仍需由你审查并批准为正式稿。
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
          {error}
        </div>
      )}

      {!generating && (
        <div className="space-y-3 rounded-xl border border-stone-200 bg-white p-4 text-xs shadow-panel">
          <label className="block">
            <span className="font-medium text-stone-700">生成方式</span>
            <select
              value={generationMode}
              onChange={(event) =>
                setGenerationMode(
                  event.target.value as "new" | "rewrite" | "polish",
                )
              }
              className="mt-1 w-full rounded-lg border border-stone-300 bg-white px-2.5 py-2 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <option value="new">按场景卡全新生成</option>
              <option value="rewrite">根据当前正文全文重写</option>
              <option value="polish">润色当前正文，不改剧情</option>
            </select>
          </label>
          <label className="block">
            <span className="font-medium text-stone-700">本次目标字数</span>
            <input
              type="number"
              min="300"
              max="10000"
              step="100"
              value={targetWordCount}
              onChange={(event) =>
                setTargetWordCount(Number(event.target.value))
              }
              className="mt-1 w-full rounded-lg border border-stone-300 px-2.5 py-2 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </label>
          <label className="block">
            <span className="font-medium text-stone-700">
              本次修改要求（可选）
            </span>
            <textarea
              value={instruction}
              onChange={(event) => setInstruction(event.target.value)}
              rows={3}
              placeholder="例如：减少血腥描写，加强两人初次见面的戒备感。"
              className="mt-1 w-full rounded-lg border border-stone-300 px-2.5 py-2 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </label>
          {generationMode !== "new" && !baseContent.trim() ? (
            <p className="rounded-lg bg-amber-50 px-3 py-2 leading-5 text-amber-800">
              请先在正文编辑器中保留需要处理的内容。
            </p>
          ) : null}
        </div>
      )}

      {generating && (
        <pre
          ref={contentRef}
          className="max-h-80 flex-1 overflow-auto rounded-xl border border-stone-200 bg-stone-50 p-4 text-sm whitespace-pre-wrap text-stone-800 shadow-panel"
        >
          {content}
          {generating && (
            <span className="inline-block h-4 w-2 animate-pulse bg-brand-600" />
          )}
        </pre>
      )}

      {done && !error && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs leading-5 text-emerald-900">
          已生成并同步到正文编辑器。
          {version && (
            <span className="ml-1">
              已保存为版本 #{version.version_no}，请审核后再批准为正式稿。
            </span>
          )}
        </div>
      )}

      {perspectiveWarning ? (
        <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800">
          {perspectiveWarning}
        </p>
      ) : null}
    </div>
  );
}
