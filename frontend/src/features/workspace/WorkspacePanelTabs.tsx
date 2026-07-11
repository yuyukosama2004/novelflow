export type WorkspacePanelTab =
  | 'ai'
  | 'review'
  | 'memory'
  | 'history'
  | 'advanced';

const TABS: readonly [WorkspacePanelTab, string][] = [
  ['ai', 'AI 写作'],
  ['review', '审查'],
  ['memory', '记忆'],
  ['history', '历史'],
  ['advanced', '高级'],
];

interface Props {
  value: WorkspacePanelTab;
  onChange: (value: WorkspacePanelTab) => void;
}

export function WorkspacePanelTabs({ value, onChange }: Props) {
  return (
    <nav className="grid grid-cols-5 rounded-md border border-slate-200 bg-white p-1 text-xs">
      {TABS.map(([key, text]) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={`rounded px-1 py-2 ${
            value === key
              ? 'bg-slate-900 text-white'
              : 'text-slate-500 hover:bg-slate-50'
          }`}
        >
          {text}
        </button>
      ))}
    </nav>
  );
}
