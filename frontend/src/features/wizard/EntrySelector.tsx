import {
  BookOpen,
  Globe2,
  Lightbulb,
  ListChecks,
  PenLine,
  UserPlus,
} from "lucide-react";

interface Props {
  onSelect: (entryType: string) => void;
  disabled?: boolean;
}

const ENTRIES = [
  {
    key: "idea",
    title: "我只有一个点子",
    description: "从一句话创意出发，LLM 通过提问帮你扩展成完整的故事概念",
    icon: Lightbulb,
    color: "text-amber-600 bg-amber-50 border-amber-200 hover:bg-amber-100",
  },
  {
    key: "world",
    title: "我想先做世界观",
    description: "从世界规则出发，LLM 帮你挖掘冲突、代价和故事可能性",
    icon: Globe2,
    color: "text-indigo-600 bg-indigo-50 border-indigo-200 hover:bg-indigo-100",
  },
  {
    key: "character",
    title: "我想先做人设",
    description: "从人物欲望和恐惧出发，LLM 帮你构建人物关系和成长弧线",
    icon: UserPlus,
    color:
      "text-emerald-600 bg-emerald-50 border-emerald-200 hover:bg-emerald-100",
  },
  {
    key: "outline",
    title: "我已有大纲",
    description: "LLM 帮你检查因果链、信息节奏和高潮设计是否合理",
    icon: ListChecks,
    color: "text-rose-600 bg-rose-50 border-rose-200 hover:bg-rose-100",
  },
  {
    key: "direct",
    title: "我想直接写正文",
    description: "快速确认基本信息后直接进入写作工作台",
    icon: PenLine,
    color: "text-slate-600 bg-slate-50 border-slate-200 hover:bg-slate-100",
  },
];

export function EntrySelector({ onSelect, disabled }: Props) {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <BookOpen size={32} className="mx-auto text-emerald-700" />
        <h2 className="mt-3 text-xl font-semibold text-slate-900">
          选择创作入口
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          不同的创作习惯对应不同的访谈方向。选择最符合你当前阶段的入口。
        </p>
      </div>

      <div className="grid gap-3">
        {ENTRIES.map((entry) => (
          <button
            key={entry.key}
            onClick={() => onSelect(entry.key)}
            disabled={disabled}
            className={`flex items-start gap-4 rounded-lg border p-4 text-left transition ${entry.color} disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <entry.icon size={22} className="mt-0.5 shrink-0" />
            <div>
              <div className="font-semibold text-sm">{entry.title}</div>
              <div className="mt-1 text-xs opacity-70">{entry.description}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
