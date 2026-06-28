import { useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ArrowRight, MessageSquare, Sparkles } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

import { apiClient } from '../../api/client';
import type { InterviewMessage, StoryCandidateEntity } from '../../types/entities';
import { CandidateCard } from './CandidateCard';
import { EntrySelector } from './EntrySelector';
import { InterviewChat } from './InterviewChat';

type Step = 'entry' | 'interview';

export function CreationWizardPage() {
  const { projectId = '' } = useParams();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>('entry');
  const [sessionId, setSessionId] = useState<string>('');
  const [messages, setMessages] = useState<InterviewMessage[]>([]);

  // ── 加载项目信息 ──
  const project = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => apiClient.getProject(projectId),
    enabled: Boolean(projectId),
  });

  // ── 载入已有会话 ──
  const sessionQuery = useQuery({
    queryKey: ['interview-session', sessionId],
    queryFn: () => apiClient.getInterviewSession(sessionId),
    enabled: Boolean(sessionId),
  });

  // ── 候选列表 ──
  const candidatesQuery = useQuery({
    queryKey: ['story-candidates', sessionId],
    queryFn: () => apiClient.listStoryCandidates(sessionId),
    enabled: Boolean(sessionId),
  });

  // ── 操作 Mutations ──
  const startSession = useMutation({
    mutationFn: (entryType: string) =>
      apiClient.startInterview(projectId, entryType),
    onSuccess: (data) => {
      setSessionId(data.id);
      setMessages(data.messages);
      setStep('interview');
    },
  });

  const sendMessage = useMutation({
    mutationFn: (content: string) =>
      apiClient.sendInterviewMessage(sessionId, content),
    onSuccess: (data) => {
      setMessages(data.messages);
    },
  });

  const extractCandidates = useMutation({
    mutationFn: () => apiClient.extractStoryCandidates(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['story-candidates', sessionId] });
    },
  });

  const approveCandidate = useMutation({
    mutationFn: (id: string) =>
      apiClient.updateStoryCandidate(id, { status: 'approved' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['story-candidates', sessionId] });
    },
  });

  const rejectCandidate = useMutation({
    mutationFn: (id: string) =>
      apiClient.updateStoryCandidate(id, { status: 'rejected' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['story-candidates', sessionId] });
    },
  });

  const editCandidate = useMutation({
    mutationFn: ({ id, contentJson }: { id: string; contentJson: Record<string, unknown> }) =>
      apiClient.updateStoryCandidate(id, { content_json: contentJson }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['story-candidates', sessionId] });
    },
  });

  const applyCandidate = useMutation({
    mutationFn: (id: string) => apiClient.applyCandidate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['story-candidates', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['characters', projectId] });
      queryClient.invalidateQueries({ queryKey: ['world', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });

  const handleSelectEntry = useCallback(
    (entryType: string) => {
      startSession.mutate(entryType);
    },
    [startSession],
  );

  const handleSend = useCallback(
    (content: string) => {
      sendMessage.mutate(content);
    },
    [sendMessage],
  );

  const candidates = candidatesQuery.data ?? [];
  const pendingCount = candidates.filter((c) => c.status === 'pending').length;
  const approvedCount = candidates.filter((c) => c.status === 'approved').length;
  const isUpdating =
    approveCandidate.isPending ||
    rejectCandidate.isPending ||
    editCandidate.isPending ||
    applyCandidate.isPending;

  return (
    <main className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-5 py-3">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"
            >
              <ArrowLeft size={15} />
              返回项目列表
            </Link>
            <div className="min-w-0">
              <h1 className="truncate text-xl font-semibold text-slate-950">
                {project.data?.title ?? '加载中…'} · 创作向导
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to={`/projects/${projectId}/bible`}
              className="rounded-md border border-amber-200 bg-white px-3 py-2 text-sm font-medium text-amber-700 hover:bg-amber-50"
            >
              故事圣经
            </Link>
            <Link
              to={`/projects/${projectId}`}
              className="inline-flex items-center gap-2 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
            >
              进入工作台
              <ArrowRight size={15} />
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1600px] gap-4 px-5 py-4 lg:grid-cols-[260px_minmax(0,1fr)_260px]">
        {/* 左侧：步骤导航 + 候选数统计 */}
        <aside className="space-y-4">
          <section className="rounded-md border border-slate-200 bg-white p-3">
            <h2 className="text-sm font-semibold text-slate-900">创作步骤</h2>
            <div className="mt-3 space-y-1">
              <div className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
                step === 'entry' ? 'bg-indigo-50 text-indigo-800 font-medium' : 'text-slate-600'
              }`}>
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-200 text-xs">
                  1
                </span>
                选择入口
              </div>
              <div className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
                step === 'interview' ? 'bg-indigo-50 text-indigo-800 font-medium' : 'text-slate-600'
              }`}>
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-200 text-xs">
                  2
                </span>
                访谈对话
              </div>
            </div>
          </section>

          {sessionId ? (
            <section className="rounded-md border border-slate-200 bg-white p-3">
              <h2 className="text-sm font-semibold text-slate-900">候选设定</h2>
              <div className="mt-2 space-y-1 text-xs text-slate-600">
                <div className="flex justify-between">
                  <span>待确认</span>
                  <span className="font-medium text-amber-700">{pendingCount}</span>
                </div>
                <div className="flex justify-between">
                  <span>已确认</span>
                  <span className="font-medium text-emerald-700">{approvedCount}</span>
                </div>
              </div>
            </section>
          ) : null}
        </aside>

        {/* 中间：主要内容 */}
        <section className="min-h-[500px] rounded-md border border-slate-200 bg-white p-6 flex flex-col">
          {step === 'entry' ? (
            <EntrySelector
              onSelect={handleSelectEntry}
              disabled={startSession.isPending}
            />
          ) : (
            <div className="flex-1 flex flex-col min-h-0">
              <InterviewChat
                messages={messages}
                onSend={handleSend}
                onExtract={() => extractCandidates.mutate()}
                isSending={sendMessage.isPending}
                isExtracting={extractCandidates.isPending}
              />
            </div>
          )}
          {startSession.isPending ? (
            <div className="flex items-center justify-center py-12 text-sm text-slate-400">
              <Sparkles size={16} className="mr-2 animate-pulse" />
              正在准备访谈…
            </div>
          ) : null}
        </section>

        {/* 右侧：候选详情 */}
        <aside className="space-y-3">
          {sessionId ? (
            <>
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <MessageSquare size={14} />
                提取的候选
              </div>
              {candidates.length === 0 ? (
                <p className="rounded-md border border-dashed border-slate-200 px-3 py-6 text-center text-xs text-slate-400">
                  在访谈中积累足够的讨论后，点击「提取候选设定」让 LLM 整理可确认的设定条目。
                </p>
              ) : (
                <div className="max-h-[600px] space-y-2 overflow-auto">
                  {candidates.map((c: StoryCandidateEntity) => (
                    <CandidateCard
                      key={c.id}
                      candidate={c}
                      onApprove={(id) => approveCandidate.mutate(id)}
                      onReject={(id) => rejectCandidate.mutate(id)}
                      onEdit={(id, contentJson) =>
                        editCandidate.mutate({ id, contentJson })
                      }
                      onApply={(id) => applyCandidate.mutate(id)}
                      isUpdating={isUpdating}
                    />
                  ))}
                </div>
              )}
            </>
          ) : null}
        </aside>
      </div>
    </main>
  );
}
