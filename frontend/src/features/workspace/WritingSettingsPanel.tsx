import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../../api/client";
import type { NovelProject } from "../../types/entities";

const STYLE_OPTIONS = [
  ["general_web", "通用网络小说"],
  ["light_novel", "轻小说"],
  ["male_web", "男频成长冒险"],
  ["female_web", "女频情感成长"],
  ["suspense", "悬疑推理"],
  ["literary", "文学现实主义"],
  ["historical", "古风历史"],
  ["scifi", "科幻幻想"],
  ["custom", "自定义文风"],
] as const;

interface Props {
  project: NovelProject | null;
}

export function WritingSettingsPanel({ project }: Props) {
  const queryClient = useQueryClient();
  const [povType, setPovType] = useState("third_person_limited");
  const [stylePreset, setStylePreset] = useState("general_web");
  const [customStyle, setCustomStyle] = useState("");
  const [defaultWordCount, setDefaultWordCount] = useState(1000);

  useEffect(() => {
    setPovType(project?.pov_type || "third_person_limited");
    setStylePreset(project?.writing_style_preset || "general_web");
    setCustomStyle(project?.writing_style_custom || "");
    setDefaultWordCount(project?.default_scene_word_count || 1000);
  }, [project]);

  const save = useMutation({
    mutationFn: () =>
      apiClient.patchProject(project?.id ?? "", {
        pov_type: povType,
        writing_style_preset: stylePreset,
        writing_style_custom: customStyle,
        default_scene_word_count: defaultWordCount,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["project", updated.id], updated);
    },
  });

  return (
    <section className="rounded-md border border-slate-200 bg-white p-3 text-xs space-y-2">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">全书写作设置</h3>
        <p className="mt-1 text-slate-500">
          影响后续 AI 生成，不会改写已有版本。
        </p>
      </div>
      <label className="block">
        <span className="font-medium text-slate-600">叙述视角</span>
        <select
          value={povType}
          onChange={(event) => setPovType(event.target.value)}
          className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
        >
          <option value="first_person">第一人称</option>
          <option value="third_person_limited">第三人称限知</option>
          <option value="third_person_omniscient">第三人称全知</option>
        </select>
      </label>
      <label className="block">
        <span className="font-medium text-slate-600">文风预设</span>
        <select
          value={stylePreset}
          onChange={(event) => setStylePreset(event.target.value)}
          className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
        >
          {STYLE_OPTIONS.map(([value, name]) => (
            <option key={value} value={value}>
              {name}
            </option>
          ))}
        </select>
      </label>
      <label className="block">
        <span className="font-medium text-slate-600">自定义文风与禁忌</span>
        <textarea
          value={customStyle}
          onChange={(event) => setCustomStyle(event.target.value)}
          rows={3}
          placeholder="例如：句子偏短，避免网络热梗，角色对话克制。"
          className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
        />
      </label>
      <label className="block">
        <span className="font-medium text-slate-600">默认单场目标字数</span>
        <input
          type="number"
          min="300"
          max="10000"
          step="100"
          value={defaultWordCount}
          onChange={(event) => setDefaultWordCount(Number(event.target.value))}
          className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
        />
      </label>
      <button
        onClick={() => save.mutate()}
        disabled={save.isPending}
        className="rounded bg-emerald-600 px-3 py-1.5 text-white hover:bg-emerald-700 disabled:opacity-50"
      >
        {save.isPending ? "保存中…" : "保存全书设置"}
      </button>
    </section>
  );
}
