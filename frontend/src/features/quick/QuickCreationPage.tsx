import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowLeft,
  ChevronDown,
  FileText,
  Sparkles,
  WandSparkles,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { apiClient } from "../../api/client";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Panel } from "../../components/ui/panel";
import { Spinner } from "../../components/ui/spinner";
import { Textarea } from "../../components/ui/textarea";
import { cn } from "../../utils/cn";
import { buildQuickBrief, type QuickBrief } from "./quickBrief";

const styleOptions = [
  ["general_web", "通用网文"],
  ["light_novel", "轻小说"],
  ["male_web", "男频成长冒险"],
  ["female_web", "女频情感成长"],
  ["suspense", "悬疑推理"],
  ["literary", "文学现实主义"],
  ["historical", "古风历史"],
  ["scifi", "科幻幻想"],
] as const;

const briefFields: readonly {
  key: Exclude<keyof QuickBrief, "titleCandidates">;
  label: string;
  multiline?: boolean;
}[] = [
  { key: "summary", label: "故事简介", multiline: true },
  { key: "protagonist", label: "主角" },
  { key: "genre", label: "类型" },
  { key: "tone", label: "基调" },
  { key: "sceneTitle", label: "场景标题" },
  { key: "goal", label: "场景目标", multiline: true },
  { key: "conflict", label: "核心冲突", multiline: true },
  { key: "turningPoint", label: "场景转折", multiline: true },
  { key: "ending", label: "结尾倾向", multiline: true },
  { key: "targetLength", label: "预计篇幅" },
];

function mutationErrorMessage(error: Error | null) {
  return error?.message || "请求失败，请检查模型与网络后重试。";
}

export function QuickCreationPage() {
  const navigate = useNavigate();
  const [idea, setIdea] = useState("");
  const [title, setTitle] = useState("");
  const [targetLength, setTargetLength] = useState("3000 字短篇");
  const [draftKind, setDraftKind] = useState<"opening" | "short">("short");
  const [povType, setPovType] = useState("third_person_limited");
  const [stylePreset, setStylePreset] = useState("general_web");
  const [defaultSceneWordCount, setDefaultSceneWordCount] = useState(1000);
  const [brief, setBrief] = useState<QuickBrief | null>(null);

  const organize = useMutation({
    mutationFn: async () => {
      const plan = await apiClient.planQuickCreation({
        idea,
        target_length: targetLength,
        draft_kind: draftKind,
      });
      return {
        titleCandidates: plan.title_candidates,
        summary: plan.summary,
        protagonist: plan.protagonist,
        genre: plan.genre,
        tone: plan.tone,
        sceneTitle: plan.scene.title,
        goal: plan.scene.goal,
        conflict: plan.scene.conflict,
        turningPoint: plan.scene.turning_point,
        ending: plan.scene.ending_hook,
        targetLength,
      } satisfies QuickBrief;
    },
    onSuccess: (nextBrief) => {
      setBrief(nextBrief);
      if (!title.trim()) setTitle(nextBrief.titleCandidates[0] ?? "");
    },
  });

  const create = useMutation({
    mutationFn: async () => {
      const activeBrief = brief ?? buildQuickBrief(idea, targetLength);
      const project = await apiClient.createProject({
        title: title.trim() || activeBrief.titleCandidates[0] || "未命名故事",
        summary: activeBrief.summary || idea.trim(),
        genre: activeBrief.genre,
        tone: activeBrief.tone,
        pov_type: povType,
        writing_style_preset: stylePreset,
        default_scene_word_count: defaultSceneWordCount,
        status: "active",
        language: "zh-CN",
      });
      const protagonist = await apiClient.createCharacter(project.id, {
        name: activeBrief.protagonist,
        role: "主角",
      });
      const volume = await apiClient.createVolume(project.id, {
        sequence_no: 1,
        title: "第一卷",
      });
      const chapter = await apiClient.createChapter(volume.id, {
        sequence_no: 1,
        title: draftKind === "short" ? "完整短篇" : "开篇试读",
      });
      await apiClient.createScene(chapter.id, {
        sequence_no: 1,
        title:
          activeBrief.sceneTitle ||
          (draftKind === "short" ? "短篇正文" : "开篇场景"),
        pov_character_id: protagonist.id,
        goal: activeBrief.goal,
        conflict: activeBrief.conflict,
        turning_point: activeBrief.turningPoint,
        ending_hook: activeBrief.ending,
      });
      return project;
    },
    onSuccess: (project) => navigate(`/projects/${project.id}?entry=quick`),
  });

  const updateBrief = <K extends Exclude<keyof QuickBrief, "titleCandidates">>(
    key: K,
    value: QuickBrief[K],
  ) => {
    if (!brief) return;
    setBrief({ ...brief, [key]: value });
  };

  return (
    <main className="min-h-screen px-4 py-6 sm:px-6 sm:py-10">
      <div className="mx-auto max-w-4xl">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-stone-500 transition hover:text-brand-700"
        >
          <ArrowLeft size={16} aria-hidden="true" />
          返回作品书架
        </Link>

        <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_16rem]">
          <section>
            <p className="text-sm font-medium text-brand-700">快速创作</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight text-stone-950">
              先把一个点子写成故事。
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-stone-500">
              先描述你脑中的画面。AI
              会整理出可修改的作品名和场景卡；它们只是草稿，只有你之后批准的版本才会成为正式稿。
            </p>
          </section>
          <Panel className="border-brand-100 bg-brand-50/60 p-4">
            <p className="text-sm font-semibold text-brand-900">三步完成</p>
            <ol className="mt-3 space-y-2 text-sm leading-6 text-brand-800">
              <li>1. 写下点子</li>
              <li>2. 让 AI 整理</li>
              <li>3. 进入编辑器创作</li>
            </ol>
          </Panel>
        </div>

        <Panel className="mt-7 p-5 sm:p-7">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-stone-950">
                你的故事点子
              </h2>
              <p className="mt-1 text-sm text-stone-500">
                人物、冲突、画面或一句设定都可以。
              </p>
            </div>
            <span className="hidden rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-500 sm:inline">
              可随时修改
            </span>
          </div>

          <Textarea
            value={idea}
            onChange={(event) => setIdea(event.target.value)}
            placeholder="例如：一个只能看见别人记忆的侦探，发现自己的记忆被人篡改了……"
            rows={7}
            className="mt-5 min-h-44 resize-y"
          />

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <label className="text-sm font-medium text-stone-700">
              想写成什么？
              <select
                value={draftKind}
                onChange={(event) =>
                  setDraftKind(
                    event.target.value === "opening" ? "opening" : "short",
                  )
                }
                className="mt-1.5 h-10 w-full rounded-lg border border-stone-300 bg-white px-3 text-sm text-stone-900 shadow-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              >
                <option value="short">完整短篇</option>
                <option value="opening">开篇试读</option>
              </select>
            </label>
            <label className="text-sm font-medium text-stone-700">
              预计篇幅
              <select
                value={targetLength}
                onChange={(event) => setTargetLength(event.target.value)}
                className="mt-1.5 h-10 w-full rounded-lg border border-stone-300 bg-white px-3 text-sm text-stone-900 shadow-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              >
                <option>1500 字开篇</option>
                <option>3000 字短篇</option>
                <option>6000 字短篇</option>
              </select>
            </label>
          </div>

          <details className="group mt-4 rounded-xl border border-stone-200 bg-stone-50/70">
            <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-medium text-stone-700 marker:content-none">
              高级写作设置
              <ChevronDown
                size={17}
                className="text-stone-400 transition group-open:rotate-180"
                aria-hidden="true"
              />
            </summary>
            <div className="grid gap-3 border-t border-stone-200 px-4 py-4 sm:grid-cols-3">
              <label className="text-sm font-medium text-stone-700">
                叙述视角
                <select
                  aria-label="叙述视角"
                  value={povType}
                  onChange={(event) => setPovType(event.target.value)}
                  className="mt-1.5 h-10 w-full rounded-lg border border-stone-300 bg-white px-3 text-sm font-normal text-stone-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                >
                  <option value="first_person">第一人称</option>
                  <option value="third_person_limited">第三人称限知</option>
                  <option value="third_person_omniscient">第三人称全知</option>
                </select>
              </label>
              <label className="text-sm font-medium text-stone-700">
                文风预设
                <select
                  aria-label="文风预设"
                  value={stylePreset}
                  onChange={(event) => setStylePreset(event.target.value)}
                  className="mt-1.5 h-10 w-full rounded-lg border border-stone-300 bg-white px-3 text-sm font-normal text-stone-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                >
                  {styleOptions.map(([value, text]) => (
                    <option key={value} value={value}>
                      {text}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-medium text-stone-700">
                单次目标字数
                <select
                  aria-label="单次目标字数"
                  value={defaultSceneWordCount}
                  onChange={(event) =>
                    setDefaultSceneWordCount(Number(event.target.value))
                  }
                  className="mt-1.5 h-10 w-full rounded-lg border border-stone-300 bg-white px-3 text-sm font-normal text-stone-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                >
                  <option value={1000}>1000 字</option>
                  <option value={2000}>2000 字</option>
                  <option value={3000}>3000 字</option>
                </select>
              </label>
              <p className="sm:col-span-3 text-xs leading-5 text-stone-500">
                这些是全书默认设置，进入工作台后仍可调整；全书设置会优先于单次生成的临时要求。
              </p>
            </div>
          </details>

          {organize.isError ? (
            <div className="mt-4 flex gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
              <AlertCircle size={18} className="mt-0.5 shrink-0" />
              <div>
                <p className="font-medium">AI 整理失败</p>
                <p className="mt-1 leading-6">
                  {mutationErrorMessage(organize.error as Error | null)}
                </p>
              </div>
            </div>
          ) : null}
          {create.isError ? (
            <div className="mt-4 flex gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
              <AlertCircle size={18} className="mt-0.5 shrink-0" />
              <div>
                <p className="font-medium">创建作品失败</p>
                <p className="mt-1 leading-6">
                  {mutationErrorMessage(create.error as Error | null)}
                </p>
              </div>
            </div>
          ) : null}

          <div className="mt-5 flex flex-wrap gap-3">
            <Button
              variant="secondary"
              disabled={!idea.trim() || organize.isPending || create.isPending}
              onClick={() => organize.mutate()}
            >
              {organize.isPending ? <Spinner /> : <WandSparkles size={16} />}
              {organize.isPending ? "AI 正在整理…" : "AI 整理点子"}
            </Button>
            <Button
              variant="primary"
              disabled={!idea.trim() || create.isPending || organize.isPending}
              onClick={() => create.mutate()}
            >
              {create.isPending ? (
                <Spinner className="text-white" />
              ) : (
                <Sparkles size={16} />
              )}
              {create.isPending
                ? "正在创建作品…"
                : brief
                  ? "采用整理结果并开始"
                  : "直接开始创作"}
            </Button>
          </div>
        </Panel>

        {brief ? (
          <Panel className="mt-6 overflow-hidden">
            <div className="flex items-start gap-3 border-b border-brand-100 bg-brand-50/60 px-5 py-4 sm:px-6">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white text-brand-700 shadow-sm">
                <FileText size={18} aria-hidden="true" />
              </span>
              <div>
                <p className="text-sm font-semibold text-brand-950">
                  AI 整理结果
                </p>
                <p className="mt-1 text-sm leading-6 text-brand-800">
                  请确认或修改后再开始。场景卡会随作品创建，但不会自动成为正式稿。
                </p>
              </div>
            </div>
            <div className="space-y-5 p-5 sm:p-6">
              <div>
                <p className="text-sm font-medium text-stone-700">作品名候选</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {brief.titleCandidates.map((candidate) => (
                    <button
                      key={candidate}
                      onClick={() => setTitle(candidate)}
                      className={cn(
                        "rounded-full border px-3 py-1.5 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500",
                        title === candidate
                          ? "border-brand-700 bg-brand-700 text-white"
                          : "border-stone-200 bg-white text-stone-700 hover:border-brand-300 hover:bg-brand-50",
                      )}
                    >
                      {candidate}
                    </button>
                  ))}
                </div>
                <label className="mt-3 block text-sm font-medium text-stone-700">
                  作品名
                  <Input
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    placeholder="从候选中选择，或自行修改"
                    className="mt-1.5"
                  />
                </label>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                {briefFields.map(({ key, label, multiline }) => (
                  <label
                    key={key}
                    className="block text-sm font-medium text-stone-700"
                  >
                    {label}
                    {multiline ? (
                      <Textarea
                        value={brief[key]}
                        onChange={(event) =>
                          updateBrief(key, event.target.value)
                        }
                        className="mt-1.5 min-h-24"
                      />
                    ) : (
                      <Input
                        value={brief[key]}
                        onChange={(event) =>
                          updateBrief(key, event.target.value)
                        }
                        className="mt-1.5"
                      />
                    )}
                  </label>
                ))}
              </div>
            </div>
          </Panel>
        ) : null}
      </div>
    </main>
  );
}
