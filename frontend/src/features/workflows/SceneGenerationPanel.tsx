import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiClient, createSSEStream } from "../../api/client";
import type { SceneVersion } from "../../types/entities";

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
  const contentRef = useRef<HTMLPreElement>(null);
  const runs = useQuery({
    queryKey: ["workflow-runs", sceneId],
    queryFn: () => apiClient.listWorkflowRuns(sceneId),
    enabled: Boolean(sceneId),
  });

  useEffect(() => {
    const latest = runs.data?.[0];
    if (!latest) return;
    setRunId(latest.id);
    setContent(latest.draft || latest.final_content);
    setGenerating(["pending", "planning", "drafting"].includes(latest.status));
    setDone(["waiting_review", "done"].includes(latest.status));
    if (latest.status === "error" || latest.status === "cancelled") {
      setError(latest.error || "生成任务未完成");
    }
  }, [runs.data]);

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
      },
      (data) => {
        if (data.run_id) setRunId(data.run_id);
        if (data.error) {
          setError(data.error);
          setGenerating(false);
          return;
        }
        if (data.content_delta) {
          setContent((prev) => prev + data.content_delta);
        }
        if (data.version) {
          setVersion(data.version);
          if (onVersionCreated) onVersionCreated(data.version);
        }
        if (data.perspective_warning) {
          setPerspectiveWarning(data.perspective_warning);
        }
      },
      () => {
        setDone(true);
        setGenerating(false);
      },
      (err) => {
        setError(err);
        setGenerating(false);
      },
    );
  }

  function handleCancel() {
    controllerRef.current?.abort();
    if (runId) void apiClient.cancelWorkflowRun(runId);
    setGenerating(false);
    setError("用户已取消生成");
  }

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold text-gray-700">AI 场景生成</h3>
        {!generating && (
          <button
            onClick={handleGenerate}
            disabled={generationMode !== "new" && !baseContent.trim()}
            className="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            {done ? "重新生成" : "生成"}
          </button>
        )}
        {generating && (
          <button
            onClick={handleCancel}
            className="px-3 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600"
          >
            取消
          </button>
        )}
        {generating && (
          <span className="text-xs text-indigo-600 animate-pulse">生成中…</span>
        )}
      </div>

      {error && (
        <div className="p-2 bg-red-50 text-red-700 text-xs rounded border border-red-200">
          {error}
        </div>
      )}

      {!generating && (
        <div className="space-y-2 rounded border border-slate-200 bg-white p-2 text-xs">
          <label className="block">
            <span className="font-medium text-slate-600">生成方式</span>
            <select
              value={generationMode}
              onChange={(event) =>
                setGenerationMode(
                  event.target.value as "new" | "rewrite" | "polish",
                )
              }
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
            >
              <option value="new">按场景卡全新生成</option>
              <option value="rewrite">根据当前正文全文重写</option>
              <option value="polish">润色当前正文，不改剧情</option>
            </select>
          </label>
          <label className="block">
            <span className="font-medium text-slate-600">本次目标字数</span>
            <input
              type="number"
              min="300"
              max="10000"
              step="100"
              value={targetWordCount}
              onChange={(event) =>
                setTargetWordCount(Number(event.target.value))
              }
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
            />
          </label>
          <label className="block">
            <span className="font-medium text-slate-600">
              本次修改要求（可选）
            </span>
            <textarea
              value={instruction}
              onChange={(event) => setInstruction(event.target.value)}
              rows={3}
              placeholder="例如：减少血腥描写，加强两人初次见面的戒备感。"
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
            />
          </label>
          {generationMode !== "new" && !baseContent.trim() ? (
            <p className="text-amber-700">
              请先在正文编辑器中保留需要处理的内容。
            </p>
          ) : null}
        </div>
      )}

      {generating && (
        <pre
          ref={contentRef}
          className="flex-1 p-3 bg-gray-50 border rounded text-sm text-gray-800 whitespace-pre-wrap overflow-auto max-h-80"
        >
          {content}
          {generating && (
            <span className="inline-block w-2 h-4 bg-indigo-600 animate-pulse" />
          )}
        </pre>
      )}

      {done && !error && (
        <div className="rounded border border-emerald-100 bg-emerald-50 p-2 text-xs text-emerald-800">
          已生成并载入编辑器。
          {version && (
            <span className="ml-1">
              已保存为版本 #{version.version_no}，请审核后再批准为正式稿。
            </span>
          )}
          {content ? (
            <details className="mt-2 text-slate-600">
              <summary className="cursor-pointer">查看本次生成预览</summary>
              <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-white p-2 text-xs">
                {content}
              </pre>
            </details>
          ) : null}
        </div>
      )}

      {perspectiveWarning ? (
        <p className="rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
          {perspectiveWarning}
        </p>
      ) : null}
    </div>
  );
}
