import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import type { MemoryCandidate } from '../../types/entities';
import { MemoryCandidatePanel } from './MemoryCandidatePanel';

vi.mock('../../api/client', () => ({
  apiClient: {
    listCandidates: vi.fn(),
    extractMemories: vi.fn(),
    updateCandidate: vi.fn(),
  },
}));

function renderWithQuery(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const now = new Date('2026-06-13T00:00:00.000Z').toISOString();

const candidate: MemoryCandidate = {
  id: 'candidate-1',
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

describe('MemoryCandidatePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.listCandidates).mockResolvedValue([]);
    vi.mocked(apiClient.extractMemories).mockResolvedValue([]);
    vi.mocked(apiClient.updateCandidate).mockResolvedValue({
      ...candidate,
      status: 'approved',
    });
  });

  it('loads an empty memory candidate state for a scene version', async () => {
    renderWithQuery(<MemoryCandidatePanel sceneVersionId="sv-1" />);

    await waitFor(() => {
      expect(apiClient.listCandidates).toHaveBeenCalledWith('sv-1');
    });
    expect(
      await screen.findByText('No memory candidates yet. Extract candidates after reviewing the draft.'),
    ).toBeInTheDocument();
  });

  it('extracts memory candidates from the current version', async () => {
    renderWithQuery(<MemoryCandidatePanel sceneVersionId="sv-1" />);

    fireEvent.click(screen.getByRole('button', { name: 'Extract' }));

    await waitFor(() => {
      expect(apiClient.extractMemories).toHaveBeenCalledWith('sv-1');
    });
  });

  it('lists candidates and approves a pending candidate', async () => {
    vi.mocked(apiClient.listCandidates).mockResolvedValue([candidate]);

    renderWithQuery(<MemoryCandidatePanel sceneVersionId="sv-1" />);

    expect(await screen.findByText('character knowledge')).toBeInTheDocument();
    expect(screen.getByText('The protagonist sees the hidden letter.')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Approve memory candidate'));

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

    expect(await screen.findByText('approved')).toBeInTheDocument();
    expect(screen.queryByLabelText('Approve memory candidate')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Reject memory candidate')).not.toBeInTheDocument();
  });

  it('disables extraction when no version exists', () => {
    renderWithQuery(<MemoryCandidatePanel sceneVersionId="" />);

    expect(screen.getByRole('button', { name: 'Extract' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeDisabled();
    expect(apiClient.listCandidates).not.toHaveBeenCalled();
  });
});
