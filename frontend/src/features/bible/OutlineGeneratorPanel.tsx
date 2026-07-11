import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, Sparkles, Trash2 } from "lucide-react";

import { apiClient } from "../../api/client";
import { IconButton } from "../../components/IconButton";

interface VolumeOutline {
  sequence_no: number;
  title: string;
  summary: string;
  goal: string;
  chapters: ChapterOutline[];
}

interface ChapterOutline {
  sequence_no: number;
  title: string;
  summary: string;
  goal: string;
  scenes: SceneOutline[];
}

interface SceneOutline {
  sequence_no: number;
  title: string;
  goal: string;
  conflict: string;
  turning_point: string;
  ending_hook: string;
}

interface Props {
  projectId: string;
  hasExistingOutline: boolean;
  modelProfileId?: string;
}

export function OutlineGeneratorPanel({
  projectId,
  hasExistingOutline,
  modelProfileId = "",
}: Props) {
  const queryClient = useQueryClient();
  const [outline, setOutline] = useState<VolumeOutline[] | null>(null);
  const [error, setError] = useState("");

  const generate = useMutation({
    mutationFn: () => apiClient.generateOutline(projectId, modelProfileId),
    onSuccess: (data) => {
      setOutline(data);
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const apply = useMutation({
    mutationFn: () =>
      apiClient.applyOutline(
        projectId,
        outline as unknown as Record<string, unknown>[],
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["volumes", projectId] });
      setOutline(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">大纲生成</h2>
        {!outline ? (
          <IconButton
            icon={<Sparkles size={14} />}
            label={generate.isPending ? "生成中…" : "LLM 生成大纲"}
            tone="primary"
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
          />
        ) : (
          <div className="flex gap-2">
            <IconButton
              icon={<ArrowDown size={14} />}
              label={apply.isPending ? "写入中…" : "写入数据库"}
              tone="primary"
              onClick={() => apply.mutate()}
              disabled={apply.isPending || hasExistingOutline}
            />
            <IconButton
              icon={<Trash2 size={14} />}
              label="清除"
              onClick={() => setOutline(null)}
            />
          </div>
        )}
      </div>

      {hasExistingOutline ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700">
          大纲已存在。重新生成会覆盖现有卷/章/场景。请先在左侧大纲中手动清理。
        </div>
      ) : null}

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-2 text-xs text-rose-700">
          {error}
        </div>
      ) : null}

      {generate.isPending ? (
        <div className="py-8 text-center text-sm text-slate-400">
          正在生成大纲…
        </div>
      ) : null}

      {outline ? (
        <div className="space-y-3 max-h-[600px] overflow-auto">
          {outline.map((vol) => (
            <div
              key={vol.sequence_no}
              className="rounded-md border border-indigo-200 bg-white p-3"
            >
              <div className="font-semibold text-sm text-indigo-900">
                第{vol.sequence_no}卷：{vol.title}
              </div>
              {vol.goal ? (
                <div className="mt-1 text-xs text-slate-500">
                  目标：{vol.goal}
                </div>
              ) : null}
              {vol.summary ? (
                <div className="mt-1 text-xs text-slate-500">{vol.summary}</div>
              ) : null}

              {vol.chapters.map((ch) => (
                <div
                  key={ch.sequence_no}
                  className="ml-3 mt-2 border-l-2 border-slate-200 pl-3"
                >
                  <div className="font-medium text-sm text-slate-800">
                    第{ch.sequence_no}章：{ch.title}
                  </div>
                  {ch.goal ? (
                    <div className="text-xs text-slate-500">
                      目标：{ch.goal}
                    </div>
                  ) : null}
                  {ch.summary ? (
                    <div className="text-xs text-slate-500">{ch.summary}</div>
                  ) : null}

                  {ch.scenes.map((sc) => (
                    <div
                      key={sc.sequence_no}
                      className="ml-3 mt-1 border-l border-slate-100 pl-3"
                    >
                      <div className="text-xs font-medium text-slate-700">
                        场景{sc.sequence_no}：{sc.title}
                      </div>
                      <div className="text-xs text-slate-400 space-y-0.5 mt-0.5">
                        {sc.goal ? <div>目标：{sc.goal}</div> : null}
                        {sc.conflict ? <div>冲突：{sc.conflict}</div> : null}
                        {sc.turning_point ? (
                          <div>转折：{sc.turning_point}</div>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
