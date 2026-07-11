import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import type { Character, Scene, WorldEntry } from '../../types/entities';
import { SceneCardEditor } from './SceneCardEditor';

vi.mock('../../api/client', () => ({
  apiClient: {
    patchScene: vi.fn(),
    getSceneContextLinks: vi.fn().mockResolvedValue({
      character_ids: [],
      world_entry_ids: [],
    }),
    replaceSceneContextLinks: vi.fn(),
  },
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
  is_stale: false,
  created_at: '2026-07-11T00:00:00Z',
  updated_at: '2026-07-11T00:00:00Z',
};

const character: Character = {
  id: 'character-1',
  project_id: 'project-1',
  name: '林默',
  aliases_json: [],
  role: '记者',
  age_text: '',
  appearance: '',
  background: '',
  public_identity: '',
  secret_identity: '',
  core_desire: '',
  core_fear: '',
  values_json: [],
  decision_pattern: '',
  stress_response: '',
  speech_style: '',
  moral_boundaries_json: [],
  ability_limits_json: {},
  forbidden_behaviors_json: [],
  arc_plan: '',
  status: 'active',
  version: 1,
  created_at: scene.created_at,
  updated_at: scene.updated_at,
};

const worldEntry: WorldEntry = {
  id: 'world-1',
  project_id: 'project-1',
  entry_type: 'location',
  name: '旧医院',
  summary: '',
  content: '',
  tags_json: [],
  canon_status: 'approved',
  version: 1,
  created_at: scene.created_at,
  updated_at: scene.updated_at,
};

describe('SceneCardEditor', () => {
  it('keeps story time inside the collapsed advanced panel', () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <SceneCardEditor
          scene={scene}
          characters={[character]}
          worldEntries={[worldEntry]}
        />
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

  it('updates explicit character links from advanced settings', async () => {
    vi.mocked(apiClient.replaceSceneContextLinks).mockResolvedValue({
      character_ids: [character.id],
      world_entry_ids: [],
    });
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <SceneCardEditor scene={scene} characters={[character]} />
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByText('高级设置'));
    fireEvent.click(await screen.findByRole('checkbox', { name: character.name }));

    await waitFor(() => {
      expect(apiClient.replaceSceneContextLinks).toHaveBeenCalledWith(scene.id, {
        character_ids: [character.id],
        world_entry_ids: [],
      });
    });
  });
});
