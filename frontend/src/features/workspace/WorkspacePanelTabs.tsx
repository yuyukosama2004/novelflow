export type WorkspacePanelTab =
  | "ai"
  | "changes"
  | "review"
  | "memory"
  | "history"
  | "discussion"
  | "advanced";

const TAB_GROUPS: readonly {
  label: string;
  tabs: readonly [WorkspacePanelTab, string][];
}[] = [
  {
    label: "创作",
    tabs: [
      ["ai", "AI 续写"],
      ["discussion", "创作讨论"],
    ],
  },
  {
    label: "检查",
    tabs: [
      ["changes", "改动审阅"],
      ["review", "一致性审查"],
      ["memory", "记忆候选"],
    ],
  },
  {
    label: "资料",
    tabs: [
      ["history", "版本历史"],
      ["advanced", "设定与场景卡"],
    ],
  },
];

interface Props {
  value: WorkspacePanelTab;
  onChange: (value: WorkspacePanelTab) => void;
}

export function WorkspacePanelTabs({ value, onChange }: Props) {
  return (
    <nav
      aria-label="创作辅助功能"
      className="space-y-3 rounded-xl border border-stone-200 bg-white p-3 shadow-panel"
    >
      {TAB_GROUPS.map((group) => (
        <section key={group.label} aria-label={group.label}>
          <p className="mb-1.5 px-1 text-[11px] font-semibold tracking-[0.14em] text-stone-400">
            {group.label}
          </p>
          <div className="grid grid-cols-2 gap-1 rounded-lg bg-stone-50 p-1">
            {group.tabs.map(([key, text]) => (
              <button
                key={key}
                type="button"
                onClick={() => onChange(key)}
                className={`rounded-md px-2 py-2 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${
                  value === key
                    ? "bg-white text-brand-700 shadow-sm"
                    : "text-stone-500 hover:bg-white hover:text-stone-800"
                }`}
              >
                {text}
              </button>
            ))}
          </div>
        </section>
      ))}
    </nav>
  );
}
