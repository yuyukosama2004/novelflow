import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, Sparkles, WandSparkles } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { apiClient } from "../../api/client";
import { buildQuickBrief, type QuickBrief } from "./quickBrief";

export function QuickCreationPage() {
  const navigate = useNavigate();
  const [idea, setIdea] = useState("");
  const [title, setTitle] = useState("");
  const [targetLength, setTargetLength] = useState("3000 字短篇");
  const [draftKind, setDraftKind] = useState<"opening" | "short">("short");
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
        title: draftKind === "short" ? "完整短篇" : "开篇试写",
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

  return (
    <main className="min-h-screen bg-slate-100 px-6 py-8">
      <div className="mx-auto max-w-3xl">
        <Link to="/" className="flex items-center gap-1 text-sm text-slate-500">
          <ArrowLeft size={15} /> 返回项目列表
        </Link>
        <section className="mt-4 rounded-xl border border-slate-200 bg-white p-6">
          <h1 className="text-2xl font-semibold text-slate-950">快速创作</h1>
          <p className="mt-2 text-sm text-slate-500">
            有一个点子就能开始。追问可以跳过，草稿不会自动成为正式稿。
          </p>
          <div className="mt-6 space-y-4">
            <textarea
              value={idea}
              onChange={(event) => setIdea(event.target.value)}
              placeholder="例如：一个只能看见别人记忆的侦探，发现自己的记忆被人篡改了……"
              rows={6}
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            />
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="故事名（可选；AI 整理后会给出候选）"
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <select
                value={targetLength}
                onChange={(event) => setTargetLength(event.target.value)}
                className="rounded-md border border-slate-300 px-3 py-2"
              >
                <option>1500 字开篇</option>
                <option>3000 字短篇</option>
                <option>6000 字短篇</option>
              </select>
              <select
                value={draftKind}
                onChange={(event) =>
                  setDraftKind(
                    event.target.value === "opening" ? "opening" : "short",
                  )
                }
                className="rounded-md border border-slate-300 px-3 py-2"
              >
                <option value="short">完整短篇</option>
                <option value="opening">开篇试写</option>
              </select>
            </div>
            {brief ? (
              <div className="grid gap-2 rounded-md border border-emerald-100 bg-emerald-50 p-4 text-sm text-emerald-900">
                <div>
                  <b>书名候选</b>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {brief.titleCandidates.map((candidate) => (
                      <button
                        key={candidate}
                        onClick={() => setTitle(candidate)}
                        className={`rounded-full border px-3 py-1 text-xs ${
                          title === candidate
                            ? "border-emerald-600 bg-emerald-600 text-white"
                            : "border-emerald-200 bg-white text-emerald-800"
                        }`}
                      >
                        {candidate}
                      </button>
                    ))}
                  </div>
                </div>
                <label className="grid gap-1 sm:grid-cols-[90px_1fr]">
                  <b>书名</b>
                  <input
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    placeholder="可从候选中选择或自行修改"
                    className="rounded border border-emerald-200 bg-white px-2 py-1"
                  />
                </label>
                {(
                  [
                    ["summary", "故事简介"],
                    ["protagonist", "主角"],
                    ["genre", "类型"],
                    ["sceneTitle", "场景标题"],
                    ["goal", "场景目标"],
                    ["conflict", "核心冲突"],
                    ["turningPoint", "场景转折"],
                    ["tone", "基调"],
                    ["ending", "结局倾向"],
                    ["targetLength", "预计篇幅"],
                  ] as const
                ).map(([key, label]) => (
                  <label
                    key={key}
                    className="grid gap-1 sm:grid-cols-[90px_1fr]"
                  >
                    <b>{label}</b>
                    <input
                      value={brief[key]}
                      onChange={(event) =>
                        setBrief({ ...brief, [key]: event.target.value })
                      }
                      className="rounded border border-emerald-200 bg-white px-2 py-1"
                    />
                  </label>
                ))}
              </div>
            ) : null}
            <div className="flex flex-wrap gap-3">
              <button
                disabled={!idea.trim() || organize.isPending}
                onClick={() => organize.mutate()}
                className="rounded-md border border-emerald-600 px-4 py-2 text-emerald-700 disabled:opacity-40"
              >
                <span className="inline-flex items-center gap-1">
                  <WandSparkles size={15} />{" "}
                  {organize.isPending ? "AI 整理中…" : "AI 整理点子"}
                </span>
              </button>
              <button
                disabled={
                  !idea.trim() || create.isPending || organize.isPending
                }
                onClick={() => create.mutate()}
                className="flex items-center gap-2 rounded-md bg-emerald-700 px-4 py-2 text-white disabled:opacity-40"
              >
                <Sparkles size={16} />{" "}
                {brief ? "采用以上候选并开始" : "快速开始（可稍后整理）"}
              </button>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
