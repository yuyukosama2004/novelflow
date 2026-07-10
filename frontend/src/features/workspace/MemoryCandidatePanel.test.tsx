import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import type {
  MemoryCandidate,
  MemoryCandidateStatus,
  MemoryExtractionRun,
  Scene,
} from '../../types/entities';
import { MemoryCandidatePanel } from './MemoryCandidatePanel';

vi.mock('../../api/client', () => ({
  apiClient: {
    listCandidates: vi.fn(),
    listMemoryExtractionRuns: vi.fn(),
    extractMemories: vi.fn(),
    updateCandidate: vi.fn(),
    completeScene: vi.fn(),
  },
}));

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderWithQuery(ui: ReactElement, queryClient = createQueryClient()) {
  return {
    queryClient,
    ...render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>),
  };
}

const now = new Date('2026-06-13T00:00:00.000Z').toISOString();

const candidate: MemoryCandidate = {
  id: 'candidate-1',
  extraction_run_id: 'run-1',
  scene_version_id: 'sv-1',
  candidate_type: 'character_knowledge',
  target_entity_type: 'character',
  target_entity_id: 'char-1',
  content_json: {
    fact_key: 'knows_secret',
    knowledge_status: 'confirmed',
  },
  evidence: 'The protagonist sees the hidden letter.',
  confidence: 0.88,
  status: 'pending',
  created_at: now,
  updated_at: now,
};

const completedRun: MemoryExtractionRun = {
  id: 'run-1',
  scene_version_id: 'sv-1',
  model_profile_id: null,
  provider: 'fake',
  model: 'fake-model',
  status: 'completed',
  prompt_snapshot_json: {},
  started_at: now,
  completed_at: now,
  created_at: now,
  updated_at: now,
};

const candidateActions: Array<{
  status: Extract<MemoryCandidateStatus, 'approved' | 'rejected'>;
  buttonLabel: string;
}> = [
  { status: 'approved', buttonLabel: '批准记忆候选' },
  { status: 'rejected', buttonLabel: '拒绝记忆候选' },
];

describe('MemoryCandidatePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.listCandidates).mockResolvedValue([]);
    vi.mocked(apiClient.listMemoryExtractionRuns).mockResolvedValue([]);
    vi.mocked(apiClient.extractMemories).mockResolvedValue({
      run: completedRun,
      candidates: [],
    });
    vi.mocked(apiClient.updateCandidate).mockResolvedValue({
      ...candidate,
      status: 'approved',
    });
    vi.mocked(apiClient.completeScene).mockResolvedValue({
      id: 'scene-1',
      status: 'completed',
    } as Scene);
  });

  it('loads an empty memory candidate state for a scene version', async () => {
    renderWithQuery(<MemoryCandidatePanel sceneVersionId="sv-1" />);

    await waitFor(() => {
      expect(apiClient.listCandidates).toHaveBeenCalledWith('sv-1');
    });
    expect(
      await screen.findByText('暂无记忆候选，请先审查草稿后再提取。'),
    ).toBeInTheDocument();
  });

  it('extracts memory candidates from the current version', async () => {
    renderWithQuery(<MemoryCandidatePanel sceneVersionId="sv-1" />);

    fireEvent.click(screen.getByRole('button', { name: '提取记忆' }));

    await waitFor(() => {
      expect(apiClient.extractMemories).toHaveBeenCalledWith('sv-1');
    });
  });

  it('passes the selected model profile to extraction', async () => {
    renderWithQuery(
      <MemoryCandidatePanel sceneVersionId="sv-1" modelProfileId="profile-1" />,
    );

    fireEvent.click(screen.getByRole('button', { name: '提取记忆' }));

    await waitFor(() => {
      expect(apiClient.extractMemories).toHaveBeenCalledWith('sv-1', 'profile-1');
    });
  });

  it('lists candidates and approves a pending candidate', async () => {
    vi.mocked(apiClient.listCandidates).mockResolvedValue([candidate]);

    renderWithQuery(<MemoryCandidatePanel sceneVersionId="sv-1" />);

    // "character_knowledge" → "人物知识" via CANDIDATE_TYPE_LABELS
    expect(await screen.findByText('人物知识')).toBeInTheDocument();
    expect(screen.getByText('The protagonist sees the hidden letter.')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('批准记忆候选'));

    await waitFor(() => {
      expect(apiClient.updateCandidate).toHaveBeenCalledWith('candidate-1', 'approved');
    });
  });

  it('does not show resolve buttons for an approved candidate', async () => {
    vi.mocked(apiClient.listCandidates).mockResolvedValue([
      {
        ...candidate,
        status: 'approved',
      },
    ]);

    renderWithQuery(<MemoryCandidatePanel sceneVersionId="sv-1" />);

    // "approved" → "已批准" via MEMORY_CANDIDATE_STATUS_LABELS
    expect(await screen.findByText('已批准')).toBeInTheDocument();
    expect(screen.queryByLabelText('批准记忆候选')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('拒绝记忆候选')).not.toBeInTheDocument();
  });

  it('targets the provided sceneVersionId for listing and extraction', async () => {
    const targetId = 'sv-target-99';
    renderWithQuery(<MemoryCandidatePanel sceneVersionId={targetId} />);

    await waitFor(() => {
      expect(apiClient.listCandidates).toHaveBeenCalledWith(targetId);
    });

    fireEvent.click(screen.getByRole('button', { name: '提取记忆' }));

    await waitFor(() => {
      expect(apiClient.extractMemories).toHaveBeenCalledWith(targetId);
    });
  });

  it('extracts candidates, invalidates, and refetches to show new candidates', async () => {
    vi.mocked(apiClient.listCandidates)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([candidate]);
    vi.mocked(apiClient.extractMemories).mockResolvedValue({
      run: completedRun,
      candidates: [candidate],
    });

    renderWithQuery(<MemoryCandidatePanel sceneVersionId="sv-1" />);

    await screen.findByText('暂无记忆候选，请先审查草稿后再提取。');

    fireEvent.click(screen.getByRole('button', { name: '提取记忆' }));

    await waitFor(() => {
      expect(apiClient.extractMemories).toHaveBeenCalledWith('sv-1');
    });
    expect(await screen.findByText('人物知识')).toBeInTheDocument();
    expect(apiClient.listCandidates).toHaveBeenLastCalledWith('sv-1');
  });

  it('refreshes and refetches candidates for the selected version', async () => {
    vi.mocked(apiClient.listCandidates)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([candidate]);

    renderWithQuery(<MemoryCandidatePanel sceneVersionId="sv-1" />);

    await screen.findByText('暂无记忆候选，请先审查草稿后再提取。');

    fireEvent.click(screen.getByRole('button', { name: '刷新' }));

    expect(await screen.findByText('人物知识')).toBeInTheDocument();
    expect(apiClient.listCandidates).toHaveBeenLastCalledWith('sv-1');
  });

  it.each(candidateActions)(
    '$status updates a pending candidate, refetches, and invalidates context',
    async ({ status, buttonLabel }) => {
      vi.mocked(apiClient.listCandidates)
        .mockResolvedValueOnce([candidate])
        .mockResolvedValueOnce([{ ...candidate, status }]);
      vi.mocked(apiClient.updateCandidate).mockResolvedValue({ ...candidate, status });
      const queryClient = createQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      renderWithQuery(<MemoryCandidatePanel sceneVersionId="sv-1" />, queryClient);

      await screen.findByText('人物知识');

      fireEvent.click(screen.getByLabelText(buttonLabel));

      await waitFor(() => {
        expect(apiClient.updateCandidate).toHaveBeenCalledWith('candidate-1', status);
      });
      // After update, status changes from "pending" to the new status label
      const statusLabels: Record<string, string> = {
        approved: '已批准',
        rejected: '已拒绝',
      };
      expect(await screen.findByText(statusLabels[status])).toBeInTheDocument();
      expect(apiClient.listCandidates).toHaveBeenLastCalledWith('sv-1');
      expect(screen.queryByLabelText('批准记忆候选')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('拒绝记忆候选')).not.toBeInTheDocument();
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['memory-candidates', 'sv-1'],
      });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['context'] });
    },
  );

  it('does not call APIs when sceneVersionId is empty', () => {
    renderWithQuery(<MemoryCandidatePanel sceneVersionId="" />);

    expect(screen.getByRole('button', { name: '提取记忆' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '刷新' })).toBeDisabled();
    expect(
      screen.getByText('请先保存、生成或批准场景版本，再进行记忆提取。'),
    ).toBeInTheDocument();
    expect(apiClient.listCandidates).not.toHaveBeenCalled();
    expect(apiClient.extractMemories).not.toHaveBeenCalled();
  });

  it('displays error state when extraction fails', async () => {
    vi.mocked(apiClient.extractMemories).mockRejectedValue(
      new Error('Extraction failed'),
    );

    renderWithQuery(<MemoryCandidatePanel sceneVersionId="sv-1" />);

    await screen.findByText('暂无记忆候选，请先审查草稿后再提取。');

    fireEvent.click(screen.getByRole('button', { name: '提取记忆' }));

    expect(
      await screen.findByText('记忆操作失败，请刷新后重试。'),
    ).toBeInTheDocument();
  });

  it('allows preview and rejection for draft candidates but blocks approval', async () => {
    vi.mocked(apiClient.listCandidates).mockResolvedValue([candidate]);

    renderWithQuery(
      <MemoryCandidatePanel
        sceneId="scene-1"
        sceneVersionId="sv-1"
        approvedVersionId="sv-approved"
      />,
    );

    expect(await screen.findByText(/这是草稿版本/)).toBeInTheDocument();
    expect(await screen.findByLabelText('批准记忆候选')).toBeDisabled();
    expect(screen.getByLabelText('拒绝记忆候选')).toBeEnabled();
  });

  it('completes a scene after extraction when no candidates remain pending', async () => {
    vi.mocked(apiClient.listMemoryExtractionRuns).mockResolvedValue([completedRun]);

    renderWithQuery(
      <MemoryCandidatePanel
        sceneId="scene-1"
        sceneVersionId="sv-1"
        approvedVersionId="sv-1"
      />,
    );

    const completeButton = await screen.findByRole('button', { name: '完成场景' });
    await waitFor(() => expect(completeButton).toBeEnabled());
    fireEvent.click(completeButton);

    await waitFor(() => {
      expect(apiClient.completeScene).toHaveBeenCalledWith('scene-1');
    });
    expect(await screen.findByText('场景已完成。')).toBeInTheDocument();
  });
});
