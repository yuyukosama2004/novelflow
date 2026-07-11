import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  KeyRound,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
  X,
} from "lucide-react";
import { Link } from "react-router-dom";

import { apiClient } from "../../api/client";
import type { ModelProfile } from "../../types/entities";

const PROVIDER_LABELS: Record<string, string> = {
  deepseek: "DeepSeek",
  ollama: "Ollama",
  openai_compatible: "OpenAI 兼容",
};

export function ModelSettingsPage() {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [testResult, setTestResult] = useState("");

  const [form, setForm] = useState<Record<string, unknown>>({
    name: "",
    provider: "deepseek",
    base_url: "",
    api_key: "",
    model_name: "",
    temperature: 0.7,
    max_output_tokens: 4096,
    timeout_seconds: 120,
    is_default: false,
    enabled: true,
  });

  const profiles = useQuery({
    queryKey: ["model-profiles"],
    queryFn: () => apiClient.listModelProfiles(),
  });

  const save = useMutation({
    mutationFn: (p: Record<string, unknown>) =>
      editingId
        ? apiClient.patchModelProfile(editingId, p)
        : apiClient.createModelProfile(p),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["model-profiles"] });
      setEditingId(null);
      setAdding(false);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiClient.deleteModelProfile(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["model-profiles"] }),
  });

  const clearApiKey = useMutation({
    mutationFn: (id: string) => apiClient.clearModelProfileApiKey(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["model-profiles"] }),
  });

  const testProfile = useMutation({
    mutationFn: (id: string) => apiClient.testModelProfile(id),
    onSuccess: (data) =>
      setTestResult(
        data.connected ? "✅ 连接成功" : `❌ ${data.error || "连接失败"}`,
      ),
    onError: (err: Error) => setTestResult(`❌ ${err.message}`),
  });

  function startAdd() {
    setForm({
      name: "",
      provider: "deepseek",
      base_url: "",
      api_key: "",
      model_name: "",
      temperature: 0.7,
      max_output_tokens: 4096,
      timeout_seconds: 120,
      is_default: false,
      enabled: true,
    });
    setAdding(true);
    setEditingId(null);
  }

  function startEdit(p: ModelProfile) {
    setForm({
      name: p.name,
      provider: p.provider,
      base_url: p.base_url,
      api_key: "",
      model_name: p.model_name,
      temperature: p.temperature,
      max_output_tokens: p.max_output_tokens,
      timeout_seconds: p.timeout_seconds,
      is_default: p.is_default,
      enabled: p.enabled,
    });
    setEditingId(p.id);
    setAdding(false);
  }

  return (
    <main className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-5 py-3">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"
            >
              <ArrowLeft size={15} /> 返回
            </Link>
            <h1 className="text-lg font-semibold text-slate-950">模型设置</h1>
          </div>
          <button
            onClick={startAdd}
            disabled={adding}
            className="flex items-center gap-1 rounded-md bg-emerald-600 px-3 py-2 text-sm text-white hover:bg-emerald-700"
          >
            <Plus size={14} /> 添加配置
          </button>
        </div>
      </header>

      <div className="mx-auto max-w-3xl space-y-4 px-5 py-4">
        {profiles.data?.map((p) => (
          <div
            key={p.id}
            className={`rounded-md border bg-white p-4 ${p.is_default ? "border-emerald-300" : "border-slate-200"}`}
          >
            {editingId === p.id ? (
              <ProfileForm
                form={form}
                setForm={setForm}
                onSave={() =>
                  save.mutate({ ...form, api_key: form.api_key || undefined })
                }
                onCancel={() => setEditingId(null)}
                isSaving={save.isPending}
              />
            ) : (
              <div className="flex items-start justify-between">
                <div className="text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-900">
                      {p.name || "未命名"}
                    </span>
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
                      {PROVIDER_LABELS[p.provider] ?? p.provider}
                    </span>
                    {p.is_default ? (
                      <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs text-emerald-700">
                        默认
                      </span>
                    ) : null}
                    {!p.enabled ? (
                      <span className="rounded bg-rose-100 px-1.5 py-0.5 text-xs text-rose-700">
                        已禁用
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-1 text-slate-500">
                    模型：{p.model_name || "未设定"} · Key：
                    {p.api_key_configured ? "已配置" : "未配置"}
                    {p.base_url ? ` · ${p.base_url}` : ""}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => testProfile.mutate(p.id)}
                    className="rounded p-1.5 text-slate-400 hover:bg-slate-100"
                    title="测试连接"
                  >
                    <RefreshCw
                      size={14}
                      className={testProfile.isPending ? "animate-spin" : ""}
                    />
                  </button>
                  <button
                    onClick={() => startEdit(p)}
                    className="rounded p-1.5 text-slate-400 hover:bg-slate-100"
                    title="编辑"
                  >
                    <Pencil size={14} />
                  </button>
                  {p.api_key_configured ? (
                    <button
                      onClick={() => {
                        if (confirm("确定清除这个配置的 API Key？"))
                          clearApiKey.mutate(p.id);
                      }}
                      className="rounded p-1.5 text-amber-500 hover:bg-amber-50"
                      title="清除 API Key"
                    >
                      <KeyRound size={14} />
                    </button>
                  ) : null}
                  <button
                    onClick={() => {
                      if (confirm("确定删除？")) remove.mutate(p.id);
                    }}
                    className="rounded p-1.5 text-rose-400 hover:bg-rose-50"
                    title="删除"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}

        {adding ? (
          <div className="rounded-md border border-indigo-200 bg-white p-4">
            <ProfileForm
              form={form}
              setForm={setForm}
              onSave={() => save.mutate(form)}
              onCancel={() => setAdding(false)}
              isSaving={save.isPending}
            />
          </div>
        ) : null}

        {testResult ? (
          <div className="rounded-md border border-slate-200 bg-white p-3 text-sm text-slate-700">
            {testResult}
          </div>
        ) : null}

        {profiles.data?.length === 0 && !adding ? (
          <div className="rounded-md border border-dashed border-slate-200 bg-white p-8 text-center text-sm text-slate-400">
            暂无模型配置，点击「添加配置」创建。
          </div>
        ) : null}
      </div>
    </main>
  );
}

function ProfileForm({
  form,
  setForm,
  onSave,
  onCancel,
  isSaving,
}: {
  form: Record<string, unknown>;
  setForm: (f: Record<string, unknown>) => void;
  onSave: () => void;
  onCancel: () => void;
  isSaving: boolean;
}) {
  return (
    <div className="space-y-3 text-sm">
      <label className="block">
        <span className="font-medium text-slate-700">名称</span>
        <input
          value={String(form.name ?? "")}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="如：DeepSeek-正式写作"
          className="mt-1 w-full rounded border px-3 py-1.5 outline-none focus:border-emerald-600"
        />
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="font-medium text-slate-700">Provider</span>
          <select
            value={String(form.provider ?? "deepseek")}
            onChange={(e) => setForm({ ...form, provider: e.target.value })}
            className="mt-1 w-full rounded border px-3 py-1.5 outline-none focus:border-emerald-600"
          >
            {Object.entries(PROVIDER_LABELS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="font-medium text-slate-700">模型名</span>
          <input
            value={String(form.model_name ?? "")}
            onChange={(e) => setForm({ ...form, model_name: e.target.value })}
            placeholder="如：deepseek-v4-flash"
            className="mt-1 w-full rounded border px-3 py-1.5 outline-none focus:border-emerald-600"
          />
        </label>
      </div>
      <label className="block">
        <span className="font-medium text-slate-700">Base URL</span>
        <input
          value={String(form.base_url ?? "")}
          onChange={(e) => setForm({ ...form, base_url: e.target.value })}
          placeholder="留空使用默认"
          className="mt-1 w-full rounded border px-3 py-1.5 outline-none focus:border-emerald-600"
        />
      </label>
      <label className="block">
        <span className="font-medium text-slate-700">API Key</span>
        <input
          type="password"
          value={String(form.api_key ?? "")}
          onChange={(e) => setForm({ ...form, api_key: e.target.value })}
          placeholder="留空不修改"
          className="mt-1 w-full rounded border px-3 py-1.5 outline-none focus:border-emerald-600"
        />
      </label>
      <div className="grid grid-cols-3 gap-3">
        <label className="block">
          <span className="font-medium text-slate-700">温度</span>
          <input
            type="number"
            min="0"
            max="2"
            step="0.1"
            value={Number(form.temperature ?? 0.7)}
            onChange={(e) =>
              setForm({ ...form, temperature: Number(e.target.value) })
            }
            className="mt-1 w-full rounded border px-3 py-1.5 outline-none focus:border-emerald-600"
          />
        </label>
        <label className="block">
          <span className="font-medium text-slate-700">最大输出</span>
          <input
            type="number"
            min="1"
            value={Number(form.max_output_tokens ?? 4096)}
            onChange={(e) =>
              setForm({ ...form, max_output_tokens: Number(e.target.value) })
            }
            className="mt-1 w-full rounded border px-3 py-1.5 outline-none focus:border-emerald-600"
          />
        </label>
        <label className="block">
          <span className="font-medium text-slate-700">超时（秒）</span>
          <input
            type="number"
            min="1"
            value={Number(form.timeout_seconds ?? 120)}
            onChange={(e) =>
              setForm({ ...form, timeout_seconds: Number(e.target.value) })
            }
            className="mt-1 w-full rounded border px-3 py-1.5 outline-none focus:border-emerald-600"
          />
        </label>
      </div>
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={Boolean(form.is_default)}
            onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
          />
          <span className="text-slate-700">设为默认</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={Boolean(form.enabled)}
            onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
          />
          <span className="text-slate-700">启用</span>
        </label>
      </div>
      <div className="flex gap-2">
        <button
          onClick={onSave}
          disabled={isSaving}
          className="flex items-center gap-1 rounded bg-emerald-600 px-3 py-1.5 text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          <Check size={14} /> 保存
        </button>
        <button
          onClick={onCancel}
          className="rounded border px-3 py-1.5 hover:bg-slate-100"
        >
          <X size={14} /> 取消
        </button>
      </div>
    </div>
  );
}
