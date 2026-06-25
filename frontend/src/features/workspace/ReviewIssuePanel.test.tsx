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
  { status: 'accepted', buttonLabel: 'Accept issue', statusLabel: 'Accepted' },
  { status: 'ignored', buttonLabel: 'Ignore issue', statusLabel: 'Ignored' },
  {
    status: 'false_positive',
    buttonLabel: 'Mark issue false positive',
    statusLabel: 'False positive',
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
      await screen.findByText('No review issues yet. Run a review to check this version.'),
    ).toBeInTheDocument();
  });

  it('runs continuity review from the panel', async () => {
    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    fireEvent.click(screen.getByRole('button', { name: 'Run review' }));

    await waitFor(() => {
      expect(apiClient.runReview).toHaveBeenCalledWith('sv-1');
    });
  });

  it('lists review issues and accepts an open issue', async () => {
    vi.mocked(apiClient.listIssues).mockResolvedValue([issue]);

    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    expect(await screen.findByText('timeline conflict')).toBeInTheDocument();
    expect(screen.getByText('The scene reveals a secret too early.')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Accept issue'));

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

    fireEvent.click(screen.getByRole('button', { name: 'Run review' }));

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

    await screen.findByText('No review issues yet. Run a review to check this version.');

    fireEvent.click(screen.getByRole('button', { name: 'Run review' }));

    await waitFor(() => {
      expect(apiClient.runReview).toHaveBeenCalledWith('sv-1');
    });
    expect(await screen.findByText('timeline conflict')).toBeInTheDocument();
    expect(apiClient.listIssues).toHaveBeenLastCalledWith('sv-1');
  });

  it('refreshes and refetches issues for the selected version', async () => {
    vi.mocked(apiClient.listIssues)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([issue]);

    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    await screen.findByText('No review issues yet. Run a review to check this version.');

    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));

    expect(await screen.findByText('timeline conflict')).toBeInTheDocument();
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

      await screen.findByText('timeline conflict');

      fireEvent.click(screen.getByLabelText(buttonLabel));

      await waitFor(() => {
        expect(apiClient.updateIssue).toHaveBeenCalledWith('issue-1', status);
      });
      expect(await screen.findByText(statusLabel)).toBeInTheDocument();
      expect(apiClient.listIssues).toHaveBeenLastCalledWith('sv-1');
      expect(screen.queryByLabelText('Accept issue')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Ignore issue')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Mark issue false positive')).not.toBeInTheDocument();
    },
  );

  it('does not call APIs when sceneVersionId is empty', () => {
    renderWithQuery(<ReviewIssuePanel sceneVersionId="" />);

    expect(screen.getByRole('button', { name: 'Run review' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeDisabled();
    expect(
      screen.getByText('Save, generate, or approve a scene version before running review.'),
    ).toBeInTheDocument();
    expect(apiClient.listIssues).not.toHaveBeenCalled();
    expect(apiClient.runReview).not.toHaveBeenCalled();
  });

  it('displays error state when run review fails', async () => {
    vi.mocked(apiClient.runReview).mockRejectedValue(new Error('Network error'));

    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    await screen.findByText('No review issues yet. Run a review to check this version.');

    fireEvent.click(screen.getByRole('button', { name: 'Run review' }));

    expect(
      await screen.findByText('Review action failed. Please refresh and try again.'),
    ).toBeInTheDocument();
  });
});
