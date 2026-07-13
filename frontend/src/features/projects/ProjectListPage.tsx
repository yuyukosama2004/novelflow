import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpen,
  LibraryBig,
  PenLine,
  Plus,
  Settings2,
  Sparkles,
  Trash2,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { apiClient } from "../../api/client";
import { Button } from "../../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { EmptyState } from "../../components/ui/empty-state";
import { Input } from "../../components/ui/input";
import { Panel } from "../../components/ui/panel";
import { Spinner } from "../../components/ui/spinner";
import { StatusPill } from "../../components/StatusPill";
import type { HealthStatus, NovelProject } from "../../types/entities";
import { label, PROJECT_STATUS_LABELS } from "../../utils/enumLabels";

interface ProjectListViewProps {
  health?: HealthStatus;
  projects: NovelProject[];
  isLoading: boolean;
  error?: string;
  onCreate: (title: string, genre: string) => void;
  isCreating: boolean;
  onArchive: (id: string) => void;
}

function formatUpdatedAt(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "最近编辑";
  return `更新于 ${date.toLocaleDateString("zh-CN", {
    month: "numeric",
    day: "numeric",
  })}`;
}

export function ProjectListView({
  health,
  projects,
  isLoading,
  error,
  onCreate,
  isCreating,
  onArchive,
}: ProjectListViewProps) {
  const [title, setTitle] = useState("");
  const [genre, setGenre] = useState("悬疑");
  const [archiveTarget, setArchiveTarget] = useState<NovelProject | null>(null);

  const handleCreate = () => {
    const normalizedTitle = title.trim();
    if (!normalizedTitle) return;
    onCreate(normalizedTitle, genre.trim());
    setTitle("");
  };

  return (
    <main className="min-h-screen bg-transparent text-stone-800">
      <header className="border-b border-stone-200/80 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link to="/" className="flex min-w-0 items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-700 text-white shadow-sm">
              <BookOpen size={20} aria-hidden="true" />
            </span>
            <span className="min-w-0">
              <span className="block text-xl font-semibold tracking-tight text-stone-950">
                NovelFlow
              </span>
              <span className="hidden text-sm text-stone-500 sm:block">
                你的小说创作工作台
              </span>
            </span>
          </Link>
          <div className="flex items-center gap-2">
            <StatusPill tone={health?.database === "ok" ? "ok" : "warn"}>
              {health?.database === "ok"
                ? `服务已连接 · v${health.version}`
                : "API 未连接"}
            </StatusPill>
            <Link
              to="/settings/models"
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-stone-500 transition hover:bg-stone-100 hover:text-stone-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              aria-label="模型设置"
              title="模型设置"
            >
              <Settings2 size={18} />
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-stretch">
          <Panel className="relative overflow-hidden bg-stone-950 px-6 py-7 text-white sm:px-8 sm:py-9">
            <div className="absolute -right-20 -top-24 h-64 w-64 rounded-full bg-brand-500/25 blur-3xl" />
            <div className="relative max-w-2xl">
              <p className="text-sm font-medium text-brand-100">
                从一个想法，开始一段故事
              </p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
                把灵感变成你自己的小说。
              </h1>
              <p className="mt-4 max-w-xl text-sm leading-7 text-stone-300 sm:text-base">
                快速创作会先帮你整理点子并生成开篇；完整创作则从作品设定开始，由你一步步掌握全书方向。
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link to="/quick">
                  <Button
                    variant="primary"
                    size="lg"
                    className="bg-brand-500 hover:bg-brand-600"
                  >
                    <Sparkles size={17} aria-hidden="true" />
                    快速创作
                  </Button>
                </Link>
                <a href="#new-project">
                  <Button
                    variant="secondary"
                    size="lg"
                    className="border-white/20 bg-white/10 text-white hover:border-white/30 hover:bg-white/15 hover:text-white"
                  >
                    <PenLine size={17} aria-hidden="true" />
                    完整创作
                  </Button>
                </a>
              </div>
            </div>
          </Panel>

          <Panel id="new-project" className="p-5 sm:p-6">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
                <Plus size={17} aria-hidden="true" />
              </span>
              <div>
                <h2 className="text-base font-semibold text-stone-900">
                  新建小说
                </h2>
                <p className="text-xs text-stone-500">创建后进入完整设定向导</p>
              </div>
            </div>
            <form
              className="mt-5 space-y-3"
              onSubmit={(event) => {
                event.preventDefault();
                handleCreate();
              }}
            >
              <label className="block text-sm font-medium text-stone-700">
                书名
                <Input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  className="mt-1.5"
                  placeholder="例如：雨夜档案"
                />
              </label>
              <label className="block text-sm font-medium text-stone-700">
                类型
                <Input
                  value={genre}
                  onChange={(event) => setGenre(event.target.value)}
                  className="mt-1.5"
                  placeholder="例如：悬疑"
                />
              </label>
              <Button
                type="submit"
                variant="primary"
                className="mt-1 w-full"
                disabled={!title.trim() || isCreating}
              >
                {isCreating ? (
                  <Spinner className="text-white" />
                ) : (
                  <Plus size={16} />
                )}
                {isCreating ? "正在创建…" : "开始完整创作"}
              </Button>
            </form>
          </Panel>
        </section>

        <section className="mt-8">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-brand-700">作品书架</p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-stone-950">
                继续你的故事
              </h2>
            </div>
            {isLoading ? <Spinner /> : null}
          </div>

          {error ? (
            <div className="mt-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              {error}
            </div>
          ) : null}

          {projects.length === 0 && !isLoading ? (
            <EmptyState
              className="mt-5"
              icon={LibraryBig}
              title="书架还是空的"
              description="从快速创作开始，或创建一本小说后进入完整设定向导。"
              action={
                <Link to="/quick">
                  <Button variant="primary">
                    <Sparkles size={16} aria-hidden="true" />
                    开始快速创作
                  </Button>
                </Link>
              }
            />
          ) : null}

          <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {projects.map((project) => (
              <article
                key={project.id}
                className="group flex min-h-56 flex-col rounded-xl border border-stone-200 bg-white p-5 shadow-panel transition hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-lg"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusPill>
                        {label(PROJECT_STATUS_LABELS, project.status)}
                      </StatusPill>
                      {project.genre ? (
                        <StatusPill tone="ok">{project.genre}</StatusPill>
                      ) : null}
                    </div>
                    <h3 className="mt-3 truncate text-lg font-semibold text-stone-950">
                      {project.title}
                    </h3>
                  </div>
                  {project.status !== "archived" ? (
                    <button
                      onClick={() => setArchiveTarget(project)}
                      className="rounded-lg p-2 text-stone-400 opacity-100 transition hover:bg-rose-50 hover:text-rose-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 sm:opacity-0 sm:group-hover:opacity-100"
                      aria-label={`归档《${project.title}》`}
                      title="归档作品"
                    >
                      <Trash2 size={16} />
                    </button>
                  ) : null}
                </div>
                <p className="mt-3 line-clamp-3 min-h-[4.5rem] text-sm leading-6 text-stone-500">
                  {project.summary || project.tone || "尚未填写作品简介"}
                </p>
                <div className="mt-auto flex items-center justify-between gap-3 border-t border-stone-100 pt-4">
                  <span className="text-xs text-stone-400">
                    {formatUpdatedAt(project.updated_at)}
                  </span>
                  <Link to={`/projects/${project.id}`}>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-brand-700 hover:bg-brand-50 hover:text-brand-800"
                    >
                      继续创作
                      <ArrowRight size={15} aria-hidden="true" />
                    </Button>
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>

      <Dialog
        open={archiveTarget !== null}
        onOpenChange={(open) => {
          if (!open) setArchiveTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold text-stone-950">
              归档这本小说？
            </DialogTitle>
            <DialogDescription className="text-sm leading-6 text-stone-500">
              《{archiveTarget?.title ?? ""}
              》会从当前书架中归档，不会删除作品内容。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setArchiveTarget(null)}>
              取消
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                if (archiveTarget) onArchive(archiveTarget.id);
                setArchiveTarget(null);
              }}
            >
              确认归档
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}

export function ProjectListPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: apiClient.health,
  });
  const projects = useQuery({
    queryKey: ["projects"],
    queryFn: apiClient.listProjects,
  });
  const [mutationError, setMutationError] = useState("");

  const createProject = useMutation({
    mutationFn: ({ title, genre }: { title: string; genre: string }) =>
      apiClient.createProject({
        title,
        genre,
        status: "active",
        language: "zh-CN",
        pov_type: "third_person_limited",
        tone: "克制、现实",
      }),
    onSuccess: (data) => {
      setMutationError("");
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate(`/projects/${data.id}/wizard`);
    },
    onError: (err: Error) => setMutationError(err.message),
  });
  const archiveProject = useMutation({
    mutationFn: (id: string) => apiClient.archiveProject(id),
    onSuccess: () => {
      setMutationError("");
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (err: Error) => setMutationError(err.message),
  });

  return (
    <ProjectListView
      health={health.data}
      projects={projects.data ?? []}
      isLoading={projects.isLoading}
      error={
        mutationError ||
        (projects.error instanceof Error ? projects.error.message : undefined)
      }
      onCreate={(title, genre) => createProject.mutate({ title, genre })}
      isCreating={createProject.isPending}
      onArchive={(id) => archiveProject.mutate(id)}
    />
  );
}
