import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, BookOpen, CheckCircle } from 'lucide-react';

import { apiClient } from '../../api/client';

interface Props {
  sceneId: string;
}

interface ContextData {
  previous_scene: { title: string; content_preview: string } | null;
  characters: {
    name: string;
    role: string;
    forbidden_behaviors: string[];
    knowledge_known: string[];
    knowledge_unknown: string[];
    knowledge_future_locked: string[];
  }[];
  world_facts: { name: string; entry_type: string; summary: string }[];
  manifest: Record<string, unknown>;
}

export function WritingAssistant({ sceneId }: Props) {
  const ctx = useQuery({
    queryKey: ['context', sceneId],
    queryFn: async () => {
      const data = await apiClient.getSceneContext(sceneId);
      return data as unknown as ContextData;
    },
    enabled: Boolean(sceneId),
    staleTime: 30000,
  });

  if (!sceneId) {
    return (
      <div className="rounded-md border border-dashed border-slate-200 bg-white p-3 text-xs text-slate-400 text-center">
        <BookOpen size={14} className="mx-auto mb-1" />
        选择场景后显示写作辅助信息
      </div>
    );
  }

  if (ctx.isLoading) {
    return <div className="rounded-md border border-slate-200 bg-white p-3 text-xs text-slate-400">加载中…</div>;
  }

  const data = ctx.data;
  if (!data) return null;

  const constraints: string[] = [];
  data.characters.forEach((ch) => {
    if (ch.forbidden_behaviors.length > 0) {
      constraints.push(`${ch.name} 禁止：${ch.forbidden_behaviors.join('、')}`);
    }
    if (ch.knowledge_unknown.length > 0) {
      constraints.push(`${ch.name} 不应知道：${ch.knowledge_unknown.join('、')}`);
    }
    if (ch.knowledge_future_locked.length > 0) {
      constraints.push(
        `${ch.name} 不得提前获知：${ch.knowledge_future_locked.join('、')}`,
      );
    }
  });

  return (
    <div className="rounded-md border border-indigo-200 bg-white p-3 text-xs space-y-2">
      {/* Token 估算 */}
      <div className="flex items-center justify-between">
        <span className="font-semibold text-indigo-900 flex items-center gap-1">
          <BookOpen size={13} /> 写作辅助
        </span>
        {data.manifest.token_estimate ? (
          <span className="text-slate-400">上下文 ~{data.manifest.token_estimate as number} tokens</span>
        ) : null}
      </div>

      {/* 前一场景 */}
      {data.previous_scene ? (
        <div className="rounded bg-slate-50 px-2 py-1.5">
          <span className="font-medium text-slate-600">← 前一场景：</span>
          <span className="text-slate-500">{data.previous_scene.title}</span>
        </div>
      ) : null}

      {/* 约束条件 */}
      {constraints.length > 0 ? (
        <div className="space-y-1">
          <div className="flex items-center gap-1 text-amber-700 font-medium">
            <AlertTriangle size={12} /> 写作约束
          </div>
          {constraints.map((c, i) => (
            <div key={i} className="rounded bg-amber-50 px-2 py-1 text-amber-800">{c}</div>
          ))}
        </div>
      ) : null}

      {/* 可用信息 */}
      <div className="space-y-1">
        <div className="flex items-center gap-1 text-emerald-700 font-medium">
          <CheckCircle size={12} /> 可用信息
        </div>
        {data.characters.map((ch) => (
          <div key={ch.name} className="rounded bg-emerald-50 px-2 py-1">
            <span className="font-medium text-emerald-800">{ch.name}</span>
            <span className="text-emerald-600">（{ch.role}）</span>
            {ch.knowledge_known.length > 0 ? (
              <span className="text-emerald-600"> 已知：{ch.knowledge_known.join('、')}</span>
            ) : null}
          </div>
        ))}
        {data.world_facts.slice(0, 3).map((wf) => (
          <div key={wf.name} className="rounded bg-emerald-50 px-2 py-1">
            <span className="font-medium text-emerald-800">[{wf.entry_type}] {wf.name}</span>
            <span className="text-emerald-600"> {wf.summary}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
