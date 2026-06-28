import { useEffect, useRef, useState } from "react";

import { createSSEStream } from "../../api/client";
import type { SceneVersion } from "../../types/entities";

interface Props {
  sceneId: string;
  onVersionCreated?: (version: SceneVersion) => void;
}

export default function SceneGenerationPanel({
  sceneId,
  onVersionCreated,
}: Props) {
  const [generating, setGenerating] = useState(false);
  const [content, setContent] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [version, setVersion] = useState<SceneVersion | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const contentRef = useRef<HTMLPreElement>(null);

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

    controllerRef.current = createSSEStream(
      sceneId,
      (data) => {
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
    setGenerating(false);
  }

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold text-gray-700">
          AI 场景生成
        </h3>
        {!generating && !done && (
          <button
            onClick={handleGenerate}
            className="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            生成
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
          <span className="text-xs text-indigo-600 animate-pulse">
            生成中…
          </span>
        )}
      </div>

      {error && (
        <div className="p-2 bg-red-50 text-red-700 text-xs rounded border border-red-200">
          {error}
        </div>
      )}

      {(content || generating) && (
        <pre
          ref={contentRef}
          className="flex-1 p-3 bg-gray-50 border rounded text-sm text-gray-800 whitespace-pre-wrap overflow-auto max-h-80"
        >
          {content}
          {generating && <span className="inline-block w-2 h-4 bg-indigo-600 animate-pulse" />}
        </pre>
      )}

      {done && !error && (
        <div className="text-xs text-green-700">
          生成完成。
          {version && (
            <span className="ml-1">
              已保存为版本 #{version.version_no}。
            </span>
          )}
        </div>
      )}
    </div>
  );
}
