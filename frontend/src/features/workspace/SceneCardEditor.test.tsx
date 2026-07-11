import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { Scene } from '../../types/entities';
import { SceneCardEditor } from './SceneCardEditor';

vi.mock('../../api/client', () => ({
  apiClient: { patchScene: vi.fn() },
}));

const scene: Scene = {
  id: 'scene-1',
  chapter_id: 'chapter-1',
  sequence_no: 1,
  title: '场景',
  pov_character_id: null,
  time_text: '',
  story_time_order: 7,
  location_id: null,
  goal: '',
  conflict: '',
  turning_point: '',
  ending_hook: '',
  must_include_json: [],
  must_not_reveal_json: [],
  forbidden_actions_json: [],
  status: 'planned',
  approved_version_id: null,
  created_at: '2026-07-11T00:00:00Z',
  updated_at: '2026-07-11T00:00:00Z',
};

describe('SceneCardEditor', () => {
  it('keeps story time inside the collapsed advanced panel', () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <SceneCardEditor scene={scene} />
      </QueryClientProvider>,
    );

    const summary = screen.getByText('高级设置');
    const details = summary.closest('details');
    expect(details).not.toHaveAttribute('open');

    fireEvent.click(summary);

    expect(details).toHaveAttribute('open');
    expect(screen.getByText('故事时间序号：')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
  });
});
