import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, Sparkles } from "lucide-react";
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

  const create = useMutation({
    mutationFn: async () => {
      const activeBrief = brief ?? buildQuickBrief(idea, targetLength);
      const project = await apiClient.createProject({
        title: title.trim() || idea.trim().slice(0, 20) || "未命名故事",
        summary: idea.trim(),
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
        title: draftKind === "short" ? "短篇正文" : "开篇场景",
        pov_character_id: protagonist.id,
        goal: activeBrief.conflict,
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
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="故事名（可选）"
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            />
            <textarea
              value={idea}
              onChange={(event) => setIdea(event.target.value)}
              placeholder="例如：一个只能看见别人记忆的侦探，发现自己的记忆被人篡改了……"
              rows={6}
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
              <div className="grid gap-2 rounded-md bg-emerald-50 p-4 text-sm text-emerald-900">
                {(
                  [
                    ["protagonist", "主角"],
                    ["conflict", "核心冲突"],
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
                disabled={!idea.trim()}
                onClick={() => setBrief(buildQuickBrief(idea, targetLength))}
                className="rounded-md border border-emerald-600 px-4 py-2 text-emerald-700 disabled:opacity-40"
              >
                整理创作简报
              </button>
              <button
                disabled={!idea.trim() || create.isPending}
                onClick={() => create.mutate()}
                className="flex items-center gap-2 rounded-md bg-emerald-700 px-4 py-2 text-white disabled:opacity-40"
              >
                <Sparkles size={16} /> 跳过追问，开始写作
              </button>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
