import { useQuery } from '@tanstack/react-query';
import { Cpu } from 'lucide-react';
import { Link } from 'react-router-dom';

import { apiClient } from '../api/client';

interface Props {
  selectedId: string;
  onChange: (id: string) => void;
}

export function ModelSelector({ selectedId, onChange }: Props) {
  const profiles = useQuery({
    queryKey: ['model-profiles'],
    queryFn: () => apiClient.listModelProfiles(),
    staleTime: 60000,
  });

  const list = profiles.data ?? [];
  const selected = list.find((p) => p.id === selectedId);

  if (list.length === 0) {
    return (
      <Link
        to="/settings/models"
        className="flex items-center gap-1 rounded-md border border-dashed border-slate-300 px-3 py-2 text-xs text-slate-400 hover:border-emerald-400 hover:text-emerald-600"
      >
        <Cpu size={14} />
        配置模型
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      <Cpu size={14} className="text-slate-400" />
      <select
        value={selectedId}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-slate-300 bg-white py-1.5 pl-2 pr-6 text-xs text-slate-700 outline-none focus:border-emerald-600"
      >
        {list.filter((p) => p.enabled).map((p) => (
          <option key={p.id} value={p.id}>
            {p.name || p.provider} · {p.model_name || '默认模型'}
          </option>
        ))}
      </select>
      <Link
        to="/settings/models"
        className="text-xs text-slate-400 hover:text-emerald-600"
        title="模型设置"
      >
        设置
      </Link>
    </div>
  );
}
