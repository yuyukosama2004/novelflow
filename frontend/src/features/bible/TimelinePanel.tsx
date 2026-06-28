import { useQuery } from '@tanstack/react-query';
import { Clock } from 'lucide-react';

import { apiClient } from '../../api/client';

interface Props {
  projectId: string;
}

export function TimelinePanel({ projectId }: Props) {
  // Timeline events are part of memory module; list via project level
  const volumes = useQuery({
    queryKey: ['volumes', projectId],
    queryFn: () => apiClient.listVolumes(projectId),
    enabled: Boolean(projectId),
  });

  if (volumes.isLoading) {
    return <div className="py-8 text-center text-sm text-slate-400">加载中…</div>;
  }

  const hasContent = (volumes.data?.length ?? 0) > 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Clock size={16} className="text-slate-400" />
        <h2 className="text-lg font-semibold text-slate-900">时间线</h2>
      </div>

      {!hasContent ? (
        <div className="rounded-md border border-dashed border-slate-200 px-3 py-8 text-center text-sm text-slate-400">
          暂无内容。在大纲中创建卷和章后，时间线信息将在此汇总。
        </div>
      ) : (
        <div className="space-y-2">
          {volumes.data?.map((v) => (
            <div key={v.id} className="rounded-md border border-slate-200 bg-white p-3">
              <div className="font-medium text-sm text-slate-800">第{v.sequence_no}卷：{v.title}</div>
              {v.summary ? <div className="mt-1 text-xs text-slate-500">{v.summary}</div> : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
