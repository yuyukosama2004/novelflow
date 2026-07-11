import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, BookOpen, Plus, RefreshCw, Trash2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { apiClient } from "../../api/client";
import { IconButton } from "../../components/IconButton";
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

  return (
    <main className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-emerald-700 text-white">
              <BookOpen size={20} />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-slate-950">
                NovelFlow
              </h1>
              <p className="text-sm text-slate-500">长篇小说创作工作台</p>
            </div>
          </div>
          <StatusPill tone={health?.database === "ok" ? "ok" : "warn"}>
            {health?.database === "ok" ? `API ${health.version}` : "API 未连接"}
          </StatusPill>
          <Link
            to="/quick"
            className="ml-3 rounded-md bg-emerald-700 px-3 py-2 text-sm text-white"
          >
            快速创作
          </Link>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-6 lg:grid-cols-[360px_1fr]">
        <section className="rounded-md border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold text-slate-900">新建小说</h2>
          <div className="mt-4 space-y-3">
            <label className="block text-sm font-medium text-slate-700">
              书名
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-600"
                placeholder="雨夜档案"
              />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              类型
              <input
                value={genre}
                onChange={(event) => setGenre(event.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-600"
              />
            </label>
            <IconButton
              icon={<Plus size={16} />}
              label="创建"
              tone="primary"
              disabled={!title.trim() || isCreating}
              onClick={() => {
                onCreate(title.trim(), genre.trim());
                setTitle("");
              }}
              className="w-full"
            />
          </div>
        </section>

        <section className="rounded-md border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <h2 className="text-base font-semibold text-slate-900">小说项目</h2>
            {isLoading ? (
              <RefreshCw size={16} className="animate-spin text-slate-500" />
            ) : null}
          </div>
          {error ? (
            <p className="px-4 py-3 text-sm text-rose-700">{error}</p>
          ) : null}
          <div className="divide-y divide-slate-100">
            {projects.length === 0 && !isLoading ? (
              <p className="px-4 py-8 text-sm text-slate-500">暂无项目</p>
            ) : null}
            {projects.map((project) => (
              <div
                key={project.id}
                className="flex items-center justify-between px-4 py-4 transition hover:bg-slate-50"
              >
                <Link to={`/projects/${project.id}`} className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="truncate text-base font-semibold text-slate-950">
                      {project.title}
                    </h3>
                    <StatusPill>
                      {label(PROJECT_STATUS_LABELS, project.status)}
                    </StatusPill>
                    {project.genre ? (
                      <StatusPill tone="ok">{project.genre}</StatusPill>
                    ) : null}
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm text-slate-500">
                    {project.summary || project.tone || "未填写简介"}
                  </p>
                </Link>
                <div className="ml-4 flex shrink-0 items-center gap-2">
                  {project.status !== "archived" ? (
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        if (confirm(`确定要归档项目「${project.title}」吗？`)) {
                          onArchive(project.id);
                        }
                      }}
                      className="rounded p-1.5 text-rose-400 hover:bg-rose-50 hover:text-rose-600"
                      title="归档"
                    >
                      <Trash2 size={16} />
                    </button>
                  ) : null}
                  <Link
                    to={`/projects/${project.id}`}
                    className="text-slate-400"
                  >
                    <ArrowRight size={18} />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
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
