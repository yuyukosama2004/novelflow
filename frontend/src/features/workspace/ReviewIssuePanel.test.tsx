import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import type { ReviewIssue, ReviewIssueStatus } from '../../types/entities';
import { ReviewIssuePanel } from './ReviewIssuePanel';

vi.mock('../../api/client', () => ({
  apiClient: {
    listIssues: vi.fn(),
    runReview: vi.fn(),
    updateIssue: vi.fn(),
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

const issue: ReviewIssue = {
  id: 'issue-1',
  scene_version_id: 'sv-1',
  issue_type: 'timeline_conflict',
  severity: 'high',
  evidence_json: '{"line":42}',
  conflict_rule: 'The scene reveals a secret too early.',
  suggestion: 'Move the reveal to a later scene.',
  confidence: 0.92,
  status: 'open',
  created_at: now,
  updated_at: now,
};

const issueActions: Array<{
  status: Exclude<ReviewIssueStatus, 'open'>;
  buttonLabel: string;
  statusLabel: string;
}> = [
  { status: 'accepted', buttonLabel: '接受问题', statusLabel: '已接受' },
  { status: 'ignored', buttonLabel: '忽略问题', statusLabel: '已忽略' },
  {
    status: 'false_positive',
    buttonLabel: '标记为误报',
    statusLabel: '误报',
  },
];

describe('ReviewIssuePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.listIssues).mockResolvedValue([]);
    vi.mocked(apiClient.runReview).mockResolvedValue([]);
    vi.mocked(apiClient.updateIssue).mockResolvedValue({ ...issue, status: 'accepted' });
  });

  it('loads an empty review state for a scene version', async () => {
    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    await waitFor(() => {
      expect(apiClient.listIssues).toHaveBeenCalledWith('sv-1');
    });
    expect(
      await screen.findByText('暂无审查问题，请对当前版本执行审查。'),
    ).toBeInTheDocument();
  });

  it('runs continuity review from the panel', async () => {
    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    fireEvent.click(screen.getByRole('button', { name: '执行审查' }));

    await waitFor(() => {
      expect(apiClient.runReview).toHaveBeenCalledWith('sv-1');
    });
  });

  it('lists review issues and accepts an open issue', async () => {
    vi.mocked(apiClient.listIssues).mockResolvedValue([issue]);

    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    // "timeline_conflict" is not in ISSUE_TYPE_LABELS, so label() returns the raw value
    expect(await screen.findByText('timeline_conflict')).toBeInTheDocument();
    expect(screen.getByText('The scene reveals a secret too early.')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('接受问题'));

    await waitFor(() => {
      expect(apiClient.updateIssue).toHaveBeenCalledWith('issue-1', 'accepted');
    });
  });

  it('targets the provided sceneVersionId for listing and review', async () => {
    const targetId = 'sv-target-42';
    renderWithQuery(<ReviewIssuePanel sceneVersionId={targetId} />);

    await waitFor(() => {
      expect(apiClient.listIssues).toHaveBeenCalledWith(targetId);
    });

    fireEvent.click(screen.getByRole('button', { name: '执行审查' }));

    await waitFor(() => {
      expect(apiClient.runReview).toHaveBeenCalledWith(targetId);
    });
  });

  it('runs review, invalidates, and refetches to show new issues', async () => {
    vi.mocked(apiClient.listIssues)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([issue]);
    vi.mocked(apiClient.runReview).mockResolvedValue([issue]);

    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    await screen.findByText('暂无审查问题，请对当前版本执行审查。');

    fireEvent.click(screen.getByRole('button', { name: '执行审查' }));

    await waitFor(() => {
      expect(apiClient.runReview).toHaveBeenCalledWith('sv-1');
    });
    expect(await screen.findByText('timeline_conflict')).toBeInTheDocument();
    expect(apiClient.listIssues).toHaveBeenLastCalledWith('sv-1');
  });

  it('refreshes and refetches issues for the selected version', async () => {
    vi.mocked(apiClient.listIssues)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([issue]);

    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    await screen.findByText('暂无审查问题，请对当前版本执行审查。');

    fireEvent.click(screen.getByRole('button', { name: '刷新' }));

    expect(await screen.findByText('timeline_conflict')).toBeInTheDocument();
    expect(apiClient.listIssues).toHaveBeenLastCalledWith('sv-1');
  });

  it.each(issueActions)(
    '$status updates an open issue and refetches the selected version',
    async ({ status, buttonLabel, statusLabel }) => {
      vi.mocked(apiClient.listIssues)
        .mockResolvedValueOnce([issue])
        .mockResolvedValueOnce([{ ...issue, status }]);
      vi.mocked(apiClient.updateIssue).mockResolvedValue({ ...issue, status });

      renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

      await screen.findByText('timeline_conflict');

      fireEvent.click(screen.getByLabelText(buttonLabel));

      await waitFor(() => {
        expect(apiClient.updateIssue).toHaveBeenCalledWith('issue-1', status);
      });
      expect(await screen.findByText(statusLabel)).toBeInTheDocument();
      expect(apiClient.listIssues).toHaveBeenLastCalledWith('sv-1');
      expect(screen.queryByLabelText('接受问题')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('忽略问题')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('标记为误报')).not.toBeInTheDocument();
    },
  );

  it('does not call APIs when sceneVersionId is empty', () => {
    renderWithQuery(<ReviewIssuePanel sceneVersionId="" />);

    expect(screen.getByRole('button', { name: '执行审查' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '刷新' })).toBeDisabled();
    expect(
      screen.getByText('请先保存、生成或批准场景版本，再进行审查。'),
    ).toBeInTheDocument();
    expect(apiClient.listIssues).not.toHaveBeenCalled();
    expect(apiClient.runReview).not.toHaveBeenCalled();
  });

  it('displays error state when run review fails', async () => {
    vi.mocked(apiClient.runReview).mockRejectedValue(new Error('Network error'));

    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    await screen.findByText('暂无审查问题，请对当前版本执行审查。');

    fireEvent.click(screen.getByRole('button', { name: '执行审查' }));

    expect(
      await screen.findByText('审查操作失败，请刷新后重试。'),
    ).toBeInTheDocument();
  });
});
