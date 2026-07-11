import { useQuery } from "@tanstack/react-query";
import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";

import { apiClient } from "../../api/client";

interface Props {
  sceneId: string;
}

interface ContextData {
  previous_scene: {
    scene_id: string;
    title: string;
    version_no: number;
    content_preview: string;
  } | null;
  characters: {
    id: string;
    name: string;
    role: string;
    public_identity: string;
    speech_style: string;
    decision_pattern: string;
    core_desire: string;
    core_fear: string;
    forbidden_behaviors: string[];
    current_state: Record<string, unknown> | null;
    knowledge_known: string[];
    knowledge_unknown: string[];
    knowledge_future_locked: string[];
  }[];
  world_facts: {
    id: string;
    name: string;
    entry_type: string;
    summary: string;
    content: string;
  }[];
  manifest: Record<string, unknown>;
}

export default function ContextChecker({ sceneId }: Props) {
  const [open, setOpen] = useState(false);

  const ctx = useQuery({
    queryKey: ["context", sceneId],
    queryFn: async () => {
      const data = await apiClient.getSceneContext(sceneId);
      return data as unknown as ContextData;
    },
    enabled: open,
  });

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800"
      >
        <Eye size={14} />
        查看上下文
      </button>
    );
  }

  const data = ctx.data;

  return (
    <div className="rounded-md border border-indigo-200 bg-white p-3 text-xs">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-indigo-900">
          生成上下文
          {data?.manifest && (
            <span className="ml-2 font-normal text-gray-500">
              ~{data.manifest.token_estimate as number} tokens
            </span>
          )}
        </h4>
        <button
          onClick={() => setOpen(false)}
          className="text-gray-400 hover:text-gray-600"
          title="关闭"
        >
          <EyeOff size={14} />
        </button>
      </div>

      {ctx.isLoading && <p className="text-gray-400">加载上下文…</p>}
      {ctx.isError && <p className="text-red-500">加载上下文失败</p>}

      {data?.previous_scene && (
        <div className="mb-2">
          <p className="font-medium text-gray-700">
            前一场景：{data.previous_scene.title}
          </p>
          <p className="text-gray-500 mt-0.5 line-clamp-3">
            {data.previous_scene.content_preview}
          </p>
        </div>
      )}

      {data?.characters && data.characters.length > 0 && (
        <div className="mb-2">
          <p className="font-medium text-gray-700 mb-1">
            人物（{data.characters.length}）
          </p>
          {data.characters.map((ch) => (
            <details key={ch.id} className="mb-1">
              <summary className="cursor-pointer text-gray-600 hover:text-gray-900">
                {ch.name}（{ch.role}）
              </summary>
              <div className="ml-3 mt-0.5 text-gray-500 space-y-0.5">
                <p>欲望：{ch.core_desire || "无"}</p>
                <p>恐惧：{ch.core_fear || "无"}</p>
                <p>说话风格：{ch.speech_style || "无"}</p>
                {ch.knowledge_known.length > 0 && (
                  <p>已知：{ch.knowledge_known.join("、")}</p>
                )}
                {ch.knowledge_unknown.length > 0 && (
                  <p className="text-red-500">
                    禁止获知：{ch.knowledge_unknown.join("、")}
                  </p>
                )}
                {ch.knowledge_future_locked.length > 0 && (
                  <p className="text-amber-600">
                    后续场景信息（禁止提前泄露）：
                    {ch.knowledge_future_locked.join("、")}
                  </p>
                )}
                {ch.forbidden_behaviors.length > 0 && (
                  <p className="text-orange-600">
                    禁止行为：{ch.forbidden_behaviors.join("、")}
                  </p>
                )}
              </div>
            </details>
          ))}
        </div>
      )}

      {data?.world_facts && data.world_facts.length > 0 && (
        <div className="mb-2">
          <p className="font-medium text-gray-700 mb-1">
            世界观事实（{data.world_facts.length}）
          </p>
          {data.world_facts.map((wf) => (
            <div key={wf.id} className="ml-2 text-gray-500">
              [{wf.entry_type}] {wf.name}：{wf.summary}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
