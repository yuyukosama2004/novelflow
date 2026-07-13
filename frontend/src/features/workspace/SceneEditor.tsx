import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import axios from "axios";
import { Check, Save } from "lucide-react";

import { apiClient } from "../../api/client";
import { IconButton } from "../../components/IconButton";
import { StatusPill } from "../../components/StatusPill";
import type { Scene, SceneVersion } from "../../types/entities";
import {
  label,
  SCENE_STATUS_LABELS,
  SOURCE_TYPE_LABELS,
} from "../../utils/enumLabels";
import {
  RichTextCodec,
  RichTextCodecError,
  type RichTextNode,
} from "../../utils/richTextCodec";

type SaveState = "idle" | "saving" | "draft_saved" | "version_saved" | "error";

interface SceneEditorProps {
  scene: Scene | null;
  selectedVersionId?: string;
  loadSelectedVersion?: boolean;
  onVersionCreated?: (version: SceneVersion) => void;
  modelProfileId?: string;
  targetWordCount?: number;
  onContentChange?: (content: string) => void;
}

function selectInitialContent(
  versions: SceneVersion[] | undefined,
  scene: Scene | null,
): string {
  if (!versions || versions.length === 0) {
    return "";
  }
  const approved = scene?.approved_version_id
    ? versions.find((version) => version.id === scene.approved_version_id)
    : undefined;
  return (approved ?? versions[0]).content_markdown;
}

function saveStateLabel(
  saveState: SaveState,
  dirty: boolean,
  sceneStatus: string,
): string {
  if (saveState === "saving") return "保存中";
  if (saveState === "draft_saved") return "草稿已保存";
  if (saveState === "version_saved") return "版本已保存";
  if (saveState === "error") return "保存失败";
  if (dirty) return "未保存";
  return sceneStatus;
}

function approvalFailureReason(error: unknown): string | undefined {
  if (!axios.isAxiosError(error)) {
    return undefined;
  }
  const data = error.response?.data as
    | { details?: { reason?: string } }
    | undefined;
  return data?.details?.reason;
}

function approvalFailureMessage(reason: string | undefined): string {
  if (reason === "VERSION_REVIEW_REQUIRED") {
    return "该版本尚未完成审查，请先执行审查。";
  }
  if (reason === "EMPTY_VERSION_CONTENT") {
    return "正文为空，不能批准为正式稿。";
  }
  if (reason === "HISTORICAL_REPLACEMENT_NOT_READY") {
    return "历史正式稿替换尚未开放，请保留当前正式稿。";
  }
  return "批准失败，请刷新后重试。";
}

function codecFailureMessage(error: unknown): string {
  return error instanceof RichTextCodecError
    ? error.message
    : "正文格式转换失败，请检查内容后重试。";
}

function draftFailureReason(error: unknown): string | undefined {
  if (!axios.isAxiosError(error)) {
    return undefined;
  }
  const data = error.response?.data as
    | { details?: { reason?: string } }
    | undefined;
  return data?.details?.reason;
}

function draftFailureMessage(error: unknown): string {
  return draftFailureReason(error) === "DRAFT_REVISION_CONFLICT"
    ? "草稿已在别处更新，请刷新页面后继续编辑。"
    : "草稿保存失败，请稍后重试。";
}

export function SceneEditor({
  scene,
  selectedVersionId = "",
  loadSelectedVersion = false,
  onVersionCreated,
  modelProfileId = "",
  targetWordCount = 1000,
  onContentChange,
}: SceneEditorProps) {
  const queryClient = useQueryClient();
  const [content, setContent] = useState("");
  const [contentJson, setContentJson] = useState<RichTextNode>({
    type: "doc",
    content: [{ type: "paragraph" }],
  });
  const [dirty, setDirty] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [approvalMessage, setApprovalMessage] = useState("");
  const [codecMessage, setCodecMessage] = useState("");
  const [draftMessage, setDraftMessage] = useState("");

  const versions = useQuery({
    queryKey: ["scene-versions", scene?.id],
    queryFn: () => apiClient.listVersions(scene?.id ?? ""),
    enabled: Boolean(scene?.id),
  });

  const workingDraft = useQuery({
    queryKey: ["scene-working-draft", scene?.id],
    queryFn: () => apiClient.getWorkingDraft(scene?.id ?? ""),
    enabled: Boolean(scene?.id),
  });

  const draftRevisionRef = useRef(0);
  const contentRef = useRef("");
  const initializedSceneRef = useRef<string | null>(null);
  const loadedExplicitVersionRef = useRef("");
  const [initializedSceneId, setInitializedSceneId] = useState("");

  const editor = useEditor({
    extensions: [StarterKit],
    content: "",
    editorProps: {
      attributes: {
        class: "tiptap max-w-none px-5 py-6 sm:px-8 sm:py-8",
      },
    },
    onUpdate: ({ editor: activeEditor }) => {
      try {
        const document = activeEditor.getJSON() as RichTextNode;
        const markdown = RichTextCodec.toMarkdown(document);
        setContent(markdown);
        onContentChange?.(markdown);
        contentRef.current = markdown;
        setContentJson(document);
        setCodecMessage("");
        setDirty(true);
        setSaveState("idle");
      } catch (error) {
        setCodecMessage(codecFailureMessage(error));
        setSaveState("error");
      }
    },
  });

  const selectedContent = useMemo(
    () => selectInitialContent(versions.data, scene),
    [scene, versions.data],
  );
  const wordCount = useMemo(
    () => RichTextCodec.toPlaintext(contentJson).replace(/\s+/g, "").length,
    [contentJson],
  );

  useEffect(() => {
    if (!scene?.id) {
      initializedSceneRef.current = null;
      setInitializedSceneId("");
      return;
    }
    if (
      !editor ||
      versions.isLoading ||
      workingDraft.isLoading ||
      initializedSceneRef.current === scene.id
    ) {
      return;
    }
    try {
      const draft = workingDraft.data;
      const document =
        draft && draft.revision > 0
          ? (draft.content_json as unknown as RichTextNode)
          : RichTextCodec.toTiptapJson(selectedContent);
      const markdown = RichTextCodec.toMarkdown(document);
      setContent(markdown);
      onContentChange?.(markdown);
      contentRef.current = markdown;
      setContentJson(document);
      draftRevisionRef.current = draft?.revision ?? 0;
      setCodecMessage("");
      setDraftMessage("");
      setDirty(false);
      setSaveState("idle");
      editor.commands.setContent(document, false);
      initializedSceneRef.current = scene.id;
      loadedExplicitVersionRef.current = "";
      setInitializedSceneId(scene.id);
    } catch (error) {
      setContent("");
      onContentChange?.("");
      contentRef.current = "";
      setCodecMessage(codecFailureMessage(error));
      setDirty(false);
      setSaveState("error");
      initializedSceneRef.current = scene.id;
      setInitializedSceneId(scene.id);
    }
  }, [
    editor,
    onContentChange,
    scene?.id,
    selectedContent,
    versions.isLoading,
    workingDraft.data,
    workingDraft.isLoading,
  ]);

  useEffect(() => {
    if (
      !editor ||
      !scene?.id ||
      !loadSelectedVersion ||
      !selectedVersionId ||
      initializedSceneId !== scene.id
    ) {
      return;
    }
    const selectedVersion = versions.data?.find(
      (version) => version.id === selectedVersionId,
    );
    const key = `${scene.id}:${selectedVersionId}`;
    if (!selectedVersion || loadedExplicitVersionRef.current === key) {
      return;
    }
    try {
      const document = RichTextCodec.toTiptapJson(
        selectedVersion.content_markdown,
      );
      const markdown = RichTextCodec.toMarkdown(document);
      setContent(markdown);
      onContentChange?.(markdown);
      contentRef.current = markdown;
      setContentJson(document);
      setCodecMessage("");
      setDraftMessage("");
      setDirty(false);
      setSaveState("idle");
      editor.commands.setContent(document, false);
      loadedExplicitVersionRef.current = key;
    } catch (error) {
      setCodecMessage(codecFailureMessage(error));
      setSaveState("error");
    }
  }, [
    editor,
    initializedSceneId,
    loadSelectedVersion,
    onContentChange,
    scene?.id,
    selectedVersionId,
    versions.data,
  ]);

  const updateDraft = useMutation({
    mutationFn: (payload: {
      content_markdown: string;
      content_json: RichTextNode;
    }) =>
      apiClient.updateWorkingDraft(scene?.id ?? "", {
        revision: draftRevisionRef.current,
        content_markdown: payload.content_markdown,
        content_json: payload.content_json as unknown as Record<
          string,
          unknown
        >,
      }),
    onSuccess: (draft, payload) => {
      draftRevisionRef.current = draft.revision;
      setDraftMessage("");
      if (contentRef.current === payload.content_markdown) {
        setDirty(false);
        setSaveState("draft_saved");
      }
      queryClient.setQueryData(["scene-working-draft", scene?.id], draft);
    },
    onError: (error) => {
      setDraftMessage(draftFailureMessage(error));
      setSaveState("error");
    },
  });

  const createVersion = useMutation({
    mutationFn: (payload: {
      content_markdown: string;
      content_json: RichTextNode;
      summary?: string;
    }) =>
      apiClient.createVersion(scene?.id ?? "", {
        content_markdown: payload.content_markdown,
        content_json: payload.content_json as unknown as Record<
          string,
          unknown
        >,
        summary: payload.summary ?? "",
        source_type: "human_revised",
      }),
    onSuccess: (version) => {
      setDirty(false);
      setSaveState("version_saved");
      queryClient.invalidateQueries({
        queryKey: ["scene-versions", scene?.id],
      });
      onVersionCreated?.(version);
    },
    onError: () => setSaveState("error"),
  });

  const approveVersion = useMutation({
    mutationFn: ({
      versionId,
      overrideReason,
    }: {
      versionId: string;
      overrideReason?: string;
    }) => apiClient.approveVersion(scene?.id ?? "", versionId, overrideReason),
    onSuccess: () => {
      setApprovalMessage("");
      queryClient.invalidateQueries({ queryKey: ["scene", scene?.id] });
      queryClient.invalidateQueries({
        queryKey: ["scene-versions", scene?.id],
      });
      queryClient.invalidateQueries({ queryKey: ["scenes"] });
      queryClient.invalidateQueries({ queryKey: ["impact-reports"] });
    },
  });

  const reviewForApproval = useMutation({
    mutationFn: (versionId: string) =>
      modelProfileId
        ? apiClient.runReview(versionId, modelProfileId)
        : apiClient.runReview(versionId),
    onSuccess: (result) => {
      setApprovalMessage("审查已完成，请确认审查问题后再次批准。");
      queryClient.setQueryData(["review-run", result.run.id], result);
      queryClient.invalidateQueries({
        queryKey: ["review-runs", result.run.scene_version_id],
      });
      queryClient.invalidateQueries({
        queryKey: ["scene-versions", scene?.id],
      });
    },
    onError: () => {
      setApprovalMessage("审查失败，请稍后重试。");
    },
  });

  const clearStale = useMutation({
    mutationFn: () => apiClient.clearSceneStale(scene?.id ?? ""),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scene", scene?.id] });
      queryClient.invalidateQueries({ queryKey: ["scenes"] });
    },
  });

  async function saveVersion() {
    if (dirty) {
      try {
        await updateDraft.mutateAsync({
          content_markdown: content,
          content_json: contentJson,
        });
      } catch {
        return;
      }
    }
    createVersion.mutate({
      content_markdown: content,
      content_json: contentJson,
      summary: scene?.title ?? "",
    });
  }

  async function requestApproval(version: SceneVersion) {
    setApprovalMessage("");
    if (version.review_status !== "completed") {
      if (!window.confirm("该版本尚未完成审查，是否现在执行审查？")) {
        return;
      }
      await reviewForApproval.mutateAsync(version.id).catch(() => undefined);
      return;
    }

    if (
      scene?.approved_version_id &&
      scene.approved_version_id !== version.id &&
      !window.confirm(
        "替换正式稿会使后续场景标记为“需复查”，并使旧版本产生的记忆失效。确认继续吗？",
      )
    ) {
      return;
    }

    try {
      await approveVersion.mutateAsync({ versionId: version.id });
    } catch (error) {
      const reason = approvalFailureReason(error);
      if (reason !== "BLOCKING_REVIEW_ISSUES") {
        setApprovalMessage(approvalFailureMessage(reason));
        return;
      }
      if (!window.confirm("存在阻断问题。是否填写理由并强制批准？")) {
        return;
      }
      const overrideReason = window.prompt("请输入强制批准理由：", "")?.trim();
      if (!overrideReason) {
        setApprovalMessage("强制批准必须填写理由。");
        return;
      }
      try {
        await approveVersion.mutateAsync({
          versionId: version.id,
          overrideReason,
        });
      } catch (overrideError) {
        setApprovalMessage(
          approvalFailureMessage(approvalFailureReason(overrideError)),
        );
      }
    }
  }

  // 使用 ref 持有 mutate 引用，避免 useEffect 依赖不稳定
  const updateDraftRef = useRef(updateDraft.mutate);
  updateDraftRef.current = updateDraft.mutate;

  // 自动保存 debounce
  useEffect(() => {
    if (!scene?.id || !dirty || !content.trim() || updateDraft.isPending) {
      return;
    }
    const timer = window.setTimeout(() => {
      setSaveState("saving");
      updateDraftRef.current({
        content_markdown: content,
        content_json: contentJson,
      });
    }, 1600);
    return () => window.clearTimeout(timer);
  }, [content, contentJson, dirty, scene?.id, updateDraft.isPending]);

  if (!scene) {
    return (
      <section className="flex min-h-[520px] flex-col items-center justify-center rounded-2xl border border-dashed border-stone-300 bg-white px-6 text-center shadow-panel">
        <p className="text-sm font-medium text-stone-700">选择或创建一个场景</p>
        <p className="mt-1 text-xs text-stone-500">
          正文、版本和审查结果会在这里集中管理。
        </p>
      </section>
    );
  }

  return (
    <section className="min-w-0">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium tracking-[0.14em] text-brand-700">
            正在撰写
          </p>
          <h2 className="mt-1 truncate text-xl font-semibold text-stone-950">
            {scene.title}
          </h2>
          <p className="mt-1 text-sm text-stone-500">
            {scene.time_text || "未设定时间"}
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <div className="min-w-[172px] rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs shadow-sm">
            <div className="flex items-center justify-between gap-3 text-stone-600">
              <span>{wordCount} 字</span>
              <span>目标 {targetWordCount} 字</span>
            </div>
            <div
              className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-stone-100"
              role="progressbar"
              aria-label="本场字数进度"
              aria-valuemin={0}
              aria-valuemax={targetWordCount}
              aria-valuenow={Math.min(wordCount, targetWordCount)}
            >
              <div
                className="h-full rounded-full bg-brand-600 transition-[width]"
                style={{
                  width: `${Math.min(
                    100,
                    Math.round(
                      (wordCount / Math.max(targetWordCount, 1)) * 100,
                    ),
                  )}%`,
                }}
              />
            </div>
          </div>
          <StatusPill
            tone={
              saveState === "error"
                ? "warn"
                : saveState === "draft_saved" || saveState === "version_saved"
                  ? "ok"
                  : "neutral"
            }
          >
            {saveStateLabel(
              saveState,
              dirty,
              label(SCENE_STATUS_LABELS, scene.status),
            )}
          </StatusPill>
          {scene.is_stale ? (
            <IconButton
              icon={<Check size={16} />}
              label="已检查，清除需复查标记"
              disabled={clearStale.isPending}
              onClick={() => clearStale.mutate()}
            />
          ) : null}
          <IconButton
            icon={<Save size={16} />}
            label="保存版本"
            tone="primary"
            disabled={
              !content.trim() ||
              createVersion.isPending ||
              updateDraft.isPending
            }
            onClick={() => void saveVersion()}
          />
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-panel">
        <EditorContent editor={editor} />
      </div>

      {codecMessage ? (
        <p className="mt-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
          {codecMessage}
        </p>
      ) : null}

      {draftMessage ? (
        <p className="mt-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
          {draftMessage}
        </p>
      ) : null}

      {approvalMessage ? (
        <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          {approvalMessage}
        </p>
      ) : null}

      <details className="mt-4 rounded-xl border border-stone-200 bg-white text-xs shadow-panel">
        <summary className="cursor-pointer px-4 py-3 font-medium text-stone-700">
          版本审批（{versions.data?.length ?? 0}）
        </summary>
        <div className="divide-y divide-slate-100 border-t border-slate-100">
          {versions.data?.map((version) => (
            <div
              key={version.id}
              className="flex items-center justify-between gap-3 px-3 py-2"
            >
              <div className="min-w-0">
                <span className="font-medium text-slate-800">
                  v{version.version_no}
                </span>
                <span className="ml-2 text-slate-500">
                  {version.summary ||
                    `${label(SOURCE_TYPE_LABELS, version.source_type)}正文`}
                </span>
              </div>
              <IconButton
                icon={<Check size={15} />}
                label={
                  version.review_status === "completed" ? "批准" : "先审查"
                }
                disabled={
                  scene.approved_version_id === version.id ||
                  approveVersion.isPending ||
                  reviewForApproval.isPending
                }
                onClick={() => void requestApproval(version)}
              />
            </div>
          ))}
        </div>
      </details>
    </section>
  );
}
