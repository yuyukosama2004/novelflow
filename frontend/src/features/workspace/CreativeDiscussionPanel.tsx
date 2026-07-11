import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Lightbulb, MessageCircle, Send, Sparkles } from "lucide-react";

import { apiClient } from "../../api/client";
import type {
  InterviewSession,
  StoryCandidateEntity,
} from "../../types/entities";

interface Props {
  projectId: string;
  sceneId: string;
  modelProfileId?: string;
  onApplyRewriteInstruction: (instruction: string) => void;
}

export function CreativeDiscussionPanel({
  projectId,
  sceneId,
  modelProfileId = "",
  onApplyRewriteInstruction,
}: Props) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [message, setMessage] = useState("");

  const discussions = useQuery({
    queryKey: ["creative-discussions", projectId, sceneId],
    queryFn: () => apiClient.listCreativeDiscussions(projectId, sceneId),
    enabled: Boolean(projectId),
  });
  const candidates = useQuery({
    queryKey: ["discussion-candidates", session?.id],
    queryFn: () => apiClient.listStoryCandidates(session?.id ?? ""),
    enabled: Boolean(session?.id),
  });

  useEffect(() => {
    if (!session && discussions.data?.[0]) setSession(discussions.data[0]);
  }, [discussions.data, session]);

  const start = useMutation({
    mutationFn: () =>
      apiClient.startCreativeDiscussion(projectId, {
        scene_id: sceneId || undefined,
        model_profile_id: modelProfileId || undefined,
      }),
    onSuccess: (nextSession) => {
      setSession(nextSession);
      queryClient.invalidateQueries({
        queryKey: ["creative-discussions", projectId, sceneId],
      });
    },
  });
  const send = useMutation({
    mutationFn: () =>
      apiClient.sendInterviewMessage(session?.id ?? "", message),
    onSuccess: (nextSession) => {
      setSession((current) =>
        current
          ? {
              ...current,
              ...nextSession,
              entry_type: current.entry_type,
              title: current.title,
              status: current.status,
              project_id: current.project_id,
            }
          : nextSession,
      );
      setMessage("");
    },
  });
  const extract = useMutation({
    mutationFn: () => apiClient.extractStoryCandidates(session?.id ?? ""),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["discussion-candidates", session?.id],
      }),
  });
  const applyCanonical = useMutation({
    mutationFn: async (candidate: StoryCandidateEntity) => {
      await apiClient.updateStoryCandidate(candidate.id, {
        status: "approved",
      });
      return apiClient.applyCandidate(candidate.id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["scene", sceneId] });
      queryClient.invalidateQueries({ queryKey: ["scenes"] });
      queryClient.invalidateQueries({
        queryKey: ["discussion-candidates", session?.id],
      });
    },
  });
  const acceptRewrite = useMutation({
    mutationFn: (candidate: StoryCandidateEntity) =>
      apiClient.updateStoryCandidate(candidate.id, { status: "approved" }),
    onSuccess: (_, candidate) => {
      const instruction = String(
        candidate.content_json.instruction ?? "",
      ).trim();
      if (instruction) onApplyRewriteInstruction(instruction);
      queryClient.invalidateQueries({
        queryKey: ["discussion-candidates", session?.id],
      });
    },
  });

  const visibleMessages = session?.messages.filter(
    (item) => item.role !== "system",
  );

  return (
    <section className="rounded-lg border border-indigo-100 bg-white p-3 text-xs shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
            <MessageCircle size={15} className="text-indigo-600" /> 创作讨论
          </h2>
          <p className="mt-1 leading-5 text-slate-500">
            围绕当前场景讨论。建议不会自动写入正史，须由你确认应用。
          </p>
        </div>
        <button
          onClick={() => start.mutate()}
          disabled={start.isPending}
          className="shrink-0 rounded border border-indigo-200 px-2 py-1 text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
        >
          新讨论
        </button>
      </div>

      {!session ? (
        <button
          onClick={() => start.mutate()}
          disabled={start.isPending}
          className="mt-3 flex w-full items-center justify-center gap-1 rounded bg-indigo-600 px-3 py-2 text-white disabled:opacity-50"
        >
          <Sparkles size={14} /> {start.isPending ? "准备中…" : "开始讨论"}
        </button>
      ) : (
        <>
          <div className="mt-3 max-h-72 space-y-2 overflow-auto rounded border border-slate-100 bg-slate-50 p-2">
            {visibleMessages?.map((item, index) => (
              <div
                key={`${item.timestamp ?? index}-${item.role}`}
                className={`rounded px-2 py-1.5 leading-5 ${
                  item.role === "user"
                    ? "ml-5 bg-indigo-600 text-white"
                    : "mr-3 bg-white text-slate-700 shadow-sm"
                }`}
              >
                {item.content}
              </div>
            ))}
          </div>
          <div className="mt-2 flex gap-2">
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                  event.preventDefault();
                  if (message.trim() && !send.isPending) send.mutate();
                }
              }}
              rows={3}
              placeholder="例如：这个转折是否太突兀？我想让气氛更压迫。"
              className="min-w-0 flex-1 rounded border border-slate-300 px-2 py-1.5 outline-none focus:border-indigo-500"
            />
            <button
              onClick={() => send.mutate()}
              disabled={!message.trim() || send.isPending}
              className="self-end rounded bg-indigo-600 p-2 text-white disabled:opacity-50"
              aria-label="发送讨论消息"
            >
              <Send size={14} />
            </button>
          </div>
          <div className="mt-2 flex items-center justify-between gap-2">
            <span className="text-slate-400">Ctrl / ⌘ + Enter 发送</span>
            <button
              onClick={() => extract.mutate()}
              disabled={extract.isPending || (visibleMessages?.length ?? 0) < 2}
              className="flex items-center gap-1 rounded border border-amber-200 px-2 py-1 text-amber-800 hover:bg-amber-50 disabled:opacity-50"
            >
              <Lightbulb size={13} />{" "}
              {extract.isPending ? "整理中…" : "提取可应用建议"}
            </button>
          </div>
        </>
      )}

      {candidates.data?.length ? (
        <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
          <p className="font-medium text-slate-700">候选建议（需确认）</p>
          {candidates.data.map((candidate) => {
            const applied = Boolean(candidate.applied_entity_id);
            const isRewrite =
              candidate.candidate_type === "rewrite_instruction";
            return (
              <article
                key={candidate.id}
                className="rounded border border-slate-200 bg-slate-50 p-2"
              >
                <p className="font-medium text-slate-800">{candidate.title}</p>
                {candidate.proposal ? (
                  <p className="mt-1 text-slate-500">{candidate.proposal}</p>
                ) : null}
                {isRewrite ? (
                  <p className="mt-1 rounded bg-white p-1.5 text-slate-600">
                    {String(candidate.content_json.instruction ?? "")}
                  </p>
                ) : null}
                <div className="mt-2">
                  {isRewrite ? (
                    <button
                      onClick={() => acceptRewrite.mutate(candidate)}
                      disabled={acceptRewrite.isPending}
                      className="rounded border border-indigo-200 bg-white px-2 py-1 text-indigo-700 disabled:opacity-50"
                    >
                      填入重写要求
                    </button>
                  ) : (
                    <button
                      onClick={() => applyCanonical.mutate(candidate)}
                      disabled={applied || applyCanonical.isPending}
                      className="rounded border border-emerald-200 bg-white px-2 py-1 text-emerald-700 disabled:opacity-50"
                    >
                      {applied ? "已应用" : "确认并应用"}
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
