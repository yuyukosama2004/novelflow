import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import axios from "axios";
import {
  Bold,
  Check,
  Heading2,
  Italic,
  List,
  ListOrdered,
  Quote,
  Redo2,
  Save,
  Undo2,
} from "lucide-react";

import { apiClient } from "../../api/client";
import { IconButton } from "../../components/IconButton";
import { StableNodeId } from "../../extensions/StableNodeId";
import { StatusPill } from "../../components/StatusPill";
import type {
  Scene,
  SceneVersion,
  SceneWorkingDraft,
} from "../../types/entities";
import { label, SCENE_STATUS_LABELS } from "../../utils/enumLabels";
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
  targetWordCount?: number;
  onContentChange?: (content: string) => void;
  onDirtyChange?: (dirty: boolean) => void;
  appliedWorkingDraft?: SceneWorkingDraft | null;
}

function selectInitialDocument(
  versions: SceneVersion[] | undefined,
  scene: Scene | null,
): RichTextNode {
  if (!versions || versions.length === 0) {
    return { type: "doc", content: [{ type: "paragraph" }] };
  }
  const approved = scene?.approved_version_id
    ? versions.find((version) => version.id === scene.approved_version_id)
    : undefined;
  return (approved ?? versions[0]).content_json as unknown as RichTextNode;
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

function FormatButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onMouseDown={(event) => event.preventDefault()}
      onClick={onClick}
      className="inline-flex h-8 w-8 items-center justify-center rounded-md text-stone-500 transition hover:bg-brand-50 hover:text-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
    >
      {children}
    </button>
  );
}

export function SceneEditor({
  scene,
  selectedVersionId = "",
  loadSelectedVersion = false,
  onVersionCreated,
  targetWordCount = 1000,
  onContentChange,
  onDirtyChange,
  appliedWorkingDraft = null,
}: SceneEditorProps) {
  const queryClient = useQueryClient();
  const [content, setContent] = useState("");
  const [contentJson, setContentJson] = useState<RichTextNode>({
    type: "doc",
    content: [{ type: "paragraph" }],
  });
  const [dirty, setDirty] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("idle");
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
  const loadedAppliedDraftRef = useRef("");
  const [initializedSceneId, setInitializedSceneId] = useState("");

  const editor = useEditor({
    extensions: [StarterKit, StableNodeId],
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

  const selectedDocument = useMemo(
    () => selectInitialDocument(versions.data, scene),
    [scene, versions.data],
  );
  const wordCount = useMemo(
    () => RichTextCodec.toPlaintext(contentJson).replace(/\s+/g, "").length,
    [contentJson],
  );

  useEffect(() => {
    if (!scene?.id) {
      initializedSceneRef.current = null;
      loadedAppliedDraftRef.current = "";
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
          : selectedDocument;
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
      loadedAppliedDraftRef.current = "";
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
    selectedDocument,
    versions.isLoading,
    workingDraft.data,
    workingDraft.isLoading,
  ]);

  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  useEffect(() => {
    if (
      !editor ||
      !scene?.id ||
      !appliedWorkingDraft ||
      appliedWorkingDraft.scene_id !== scene.id ||
      initializedSceneId !== scene.id
    ) {
      return;
    }
    const key = `${scene.id}:${appliedWorkingDraft.revision}`;
    if (loadedAppliedDraftRef.current === key) {
      return;
    }
    try {
      const document =
        appliedWorkingDraft.content_json as unknown as RichTextNode;
      const markdown = RichTextCodec.toMarkdown(document);
      setContent(markdown);
      onContentChange?.(markdown);
      contentRef.current = markdown;
      setContentJson(document);
      draftRevisionRef.current = appliedWorkingDraft.revision;
      setCodecMessage("");
      setDraftMessage("");
      setDirty(false);
      setSaveState("draft_saved");
      editor.commands.setContent(document, false);
      loadedAppliedDraftRef.current = key;
    } catch (error) {
      setCodecMessage(codecFailureMessage(error));
      setSaveState("error");
    }
  }, [
    appliedWorkingDraft,
    editor,
    initializedSceneId,
    onContentChange,
    scene?.id,
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
      const document = selectedVersion.content_json as unknown as RichTextNode;
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
        {editor ? (
          <div
            aria-label="正文格式工具"
            className="flex flex-wrap items-center gap-0.5 border-b border-stone-100 bg-stone-50 px-3 py-2"
          >
            <FormatButton
              label="撤销"
              onClick={() => editor.chain().focus().undo().run()}
            >
              <Undo2 size={16} />
            </FormatButton>
            <FormatButton
              label="重做"
              onClick={() => editor.chain().focus().redo().run()}
            >
              <Redo2 size={16} />
            </FormatButton>
            <span className="mx-1 h-5 w-px bg-stone-200" aria-hidden="true" />
            <FormatButton
              label="加粗"
              onClick={() => editor.chain().focus().toggleBold().run()}
            >
              <Bold size={16} />
            </FormatButton>
            <FormatButton
              label="斜体"
              onClick={() => editor.chain().focus().toggleItalic().run()}
            >
              <Italic size={16} />
            </FormatButton>
            <FormatButton
              label="二级标题"
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 2 }).run()
              }
            >
              <Heading2 size={16} />
            </FormatButton>
            <FormatButton
              label="引用"
              onClick={() => editor.chain().focus().toggleBlockquote().run()}
            >
              <Quote size={16} />
            </FormatButton>
            <FormatButton
              label="无序列表"
              onClick={() => editor.chain().focus().toggleBulletList().run()}
            >
              <List size={16} />
            </FormatButton>
            <FormatButton
              label="有序列表"
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
            >
              <ListOrdered size={16} />
            </FormatButton>
          </div>
        ) : null}
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
    </section>
  );
}
