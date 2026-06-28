import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Check, Save } from 'lucide-react';

import { apiClient } from '../../api/client';
import { IconButton } from '../../components/IconButton';
import { StatusPill } from '../../components/StatusPill';
import type { Scene, SceneVersion } from '../../types/entities';
import { label, SOURCE_TYPE_LABELS } from '../../utils/enumLabels';

interface SceneEditorProps {
  scene: Scene | null;
  onVersionCreated?: (version: SceneVersion) => void;
}

function selectInitialContent(versions: SceneVersion[] | undefined, scene: Scene | null): string {
  if (!versions || versions.length === 0) {
    return '';
  }
  const approved = scene?.approved_version_id
    ? versions.find((version) => version.id === scene.approved_version_id)
    : undefined;
  return (approved ?? versions[0]).content_markdown;
}

function saveStateLabel(
  saveState: 'idle' | 'saving' | 'saved' | 'error',
  dirty: boolean,
  sceneStatus: string,
): string {
  if (saveState === 'saving') return '保存中';
  if (saveState === 'saved') return '已保存';
  if (saveState === 'error') return '保存失败';
  if (dirty) return '未保存';
  return sceneStatus;
}

export function SceneEditor({ scene, onVersionCreated }: SceneEditorProps) {
  const queryClient = useQueryClient();
  const [content, setContent] = useState('');
  const [dirty, setDirty] = useState(false);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  const versions = useQuery({
    queryKey: ['scene-versions', scene?.id],
    queryFn: () => apiClient.listVersions(scene?.id ?? ''),
    enabled: Boolean(scene?.id),
  });

  const editor = useEditor({
    extensions: [StarterKit],
    content: '',
    editorProps: {
      attributes: {
        class:
          'prose prose-slate max-w-none rounded-md border border-slate-200 bg-white p-4 text-[15px] leading-7',
      },
    },
    onUpdate: ({ editor: activeEditor }) => {
      setContent(activeEditor.getHTML());
      setDirty(true);
      setSaveState('idle');
    },
  });

  const selectedContent = useMemo(
    () => selectInitialContent(versions.data, scene),
    [scene, versions.data],
  );

  useEffect(() => {
    setContent(selectedContent);
    setDirty(false);
    setSaveState('idle');
    editor?.commands.setContent(selectedContent, false);
  }, [editor, selectedContent]);

  const createVersion = useMutation({
    mutationFn: (payload: { content_markdown: string; summary?: string }) =>
      apiClient.createVersion(scene?.id ?? '', {
        content_markdown: payload.content_markdown,
        summary: payload.summary ?? '',
        source_type: 'human_revised',
      }),
    onSuccess: (version) => {
      setDirty(false);
      setSaveState('saved');
      queryClient.invalidateQueries({ queryKey: ['scene-versions', scene?.id] });
      onVersionCreated?.(version);
    },
    onError: () => setSaveState('error'),
  });

  const approveVersion = useMutation({
    mutationFn: (versionId: string) => apiClient.approveVersion(scene?.id ?? '', versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scene', scene?.id] });
      queryClient.invalidateQueries({ queryKey: ['scene-versions', scene?.id] });
      queryClient.invalidateQueries({ queryKey: ['scenes'] });
    },
  });

  // 使用 ref 持有 mutate 引用，避免 useEffect 依赖不稳定
  const mutateRef = useRef(createVersion.mutate);
  mutateRef.current = createVersion.mutate;

  // 自动保存 debounce
  useEffect(() => {
    if (!scene?.id || !dirty || !content.trim()) {
      return;
    }
    const timer = window.setTimeout(() => {
      setSaveState('saving');
      mutateRef.current({ content_markdown: content, summary: scene.title });
    }, 1600);
    return () => window.clearTimeout(timer);
  }, [content, dirty, scene?.id, scene?.title]);

  if (!scene) {
    return (
      <section className="flex min-h-[520px] items-center justify-center rounded-md border border-dashed border-slate-300 bg-white text-sm text-slate-500">
        选择或创建一个场景
      </section>
    );
  }

  return (
    <section className="min-w-0">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold text-slate-950">{scene.title}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {scene.time_text || '未设定时间'} · 时间线 {scene.timeline_order}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusPill
            tone={
              saveState === 'error'
                ? 'warn'
                : saveState === 'saved'
                  ? 'ok'
                  : 'neutral'
            }
          >
            {saveStateLabel(saveState, dirty, scene.status)}
          </StatusPill>
          <IconButton
            icon={<Save size={16} />}
            label="保存版本"
            tone="primary"
            disabled={!content.trim() || createVersion.isPending}
            onClick={() =>
              createVersion.mutate({ content_markdown: content, summary: scene.title })
            }
          />
        </div>
      </div>

      <EditorContent editor={editor} />

      <div className="mt-4 rounded-md border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2">
          <h3 className="text-sm font-semibold text-slate-900">版本历史</h3>
          <span className="text-xs text-slate-500">{versions.data?.length ?? 0} 个版本</span>
        </div>
        <div className="max-h-72 divide-y divide-slate-100 overflow-auto">
          {versions.data?.map((version) => (
            <div
              key={version.id}
              className="flex items-center justify-between gap-3 px-3 py-3"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-slate-900">
                    v{version.version_no}
                  </span>
                  <StatusPill
                    tone={scene.approved_version_id === version.id ? 'ok' : 'neutral'}
                  >
                    {scene.approved_version_id === version.id
                      ? '正式稿'
                      : label(SOURCE_TYPE_LABELS, version.source_type)}
                  </StatusPill>
                </div>
                <p className="mt-1 truncate text-xs text-slate-500">
                  {version.summary ||
                    version.content_markdown.replace(/<[^>]+>/g, '').slice(0, 80)}
                </p>
              </div>
              <IconButton
                icon={<Check size={15} />}
                label="批准"
                disabled={
                  scene.approved_version_id === version.id || approveVersion.isPending
                }
                onClick={() => approveVersion.mutate(version.id)}
              />
            </div>
          ))}
          {versions.data?.length === 0 ? (
            <p className="px-3 py-6 text-sm text-slate-500">暂无版本</p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
