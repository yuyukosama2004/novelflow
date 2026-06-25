import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import type { ReviewIssue } from '../../types/entities';
import { ReviewIssuePanel } from './ReviewIssuePanel';

vi.mock('../../api/client', () => ({
  apiClient: {
    listIssues: vi.fn(),
    runReview: vi.fn(),
    updateIssue: vi.fn(),
  },
}));

function renderWithQuery(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
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

  it('disables review actions when no version exists', () => {
    renderWithQuery(<ReviewIssuePanel sceneVersionId="" />);

    expect(screen.getByRole('button', { name: 'Run review' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeDisabled();
    expect(apiClient.listIssues).not.toHaveBeenCalled();
  });

  it('targets the provided sceneVersionId for all operations', async () => {
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
});
