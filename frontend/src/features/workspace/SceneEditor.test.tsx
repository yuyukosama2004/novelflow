import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import type {
  ReviewResult,
  ReviewRun,
  Scene,
  SceneVersion,
} from '../../types/entities';
import { SceneEditor } from './SceneEditor';

const { editorMock } = vi.hoisted(() => ({
  editorMock: { commands: { setContent: vi.fn() } },
}));

vi.mock('@tiptap/react', () => ({
  EditorContent: () => <div data-testid="editor" />,
  useEditor: () => editorMock,
}));

vi.mock('../../api/client', () => ({
  apiClient: {
    listVersions: vi.fn(),
    createVersion: vi.fn(),
    approveVersion: vi.fn(),
    runReview: vi.fn(),
  },
}));

function renderWithQuery(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

const now = '2026-07-11T00:00:00.000Z';

const scene: Scene = {
  id: 'scene-1',
  chapter_id: 'chapter-1',
  sequence_no: 1,
  title: '测试场景',
  pov_character_id: null,
  time_text: '',
  timeline_order: 0,
  location_id: null,
  goal: '',
  conflict: '',
  turning_point: '',
  ending_hook: '',
  must_include_json: [],
  must_not_reveal_json: [],
  forbidden_actions_json: [],
  status: 'reviewing',
  approved_version_id: null,
  created_at: now,
  updated_at: now,
};

function version(reviewStatus: string): SceneVersion {
  return {
    id: 'version-1',
    scene_id: scene.id,
    version_no: 1,
    parent_version_id: null,
    branch_name: 'main',
    content_markdown: '正文',
    summary: '',
    source_type: 'human',
    model_profile_id: null,
    prompt_snapshot_json: {},
    context_manifest_json: {},
    review_status: reviewStatus,
    created_by: 'user',
    approved_at: null,
    approval_override_reason: null,
    created_at: now,
    updated_at: now,
  };
}

const completedRun: ReviewRun = {
  id: 'run-1',
  scene_version_id: 'version-1',
  model_profile_id: null,
  provider: 'fake',
  model: 'fake-model',
  status: 'completed',
  prompt_snapshot_json: {},
  started_at: now,
  completed_at: now,
  summary: '未发现问题',
  created_at: now,
  updated_at: now,
};

const reviewResult: ReviewResult = { run: completedRun, issues: [] };

function apiError(reason: string) {
  return {
    isAxiosError: true,
    response: { data: { details: { reason } } },
  };
}

describe('SceneEditor approval gate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    vi.spyOn(window, 'prompt').mockReturnValue('作者确认这是有意安排');
    vi.mocked(apiClient.createVersion).mockResolvedValue(
      version('not_reviewed'),
    );
    vi.mocked(apiClient.runReview).mockResolvedValue(reviewResult);
    vi.mocked(apiClient.approveVersion).mockResolvedValue({
      ...scene,
      approved_version_id: 'version-1',
      status: 'canonicalizing',
    });
  });

  it('normalizes legacy HTML before loading and saving a version', async () => {
    vi.mocked(apiClient.listVersions).mockResolvedValue([
      {
        ...version('not_reviewed'),
        content_markdown: '<p><strong>重点</strong><br>下一行</p>',
      },
    ]);
    renderWithQuery(<SceneEditor scene={scene} />);

    await waitFor(() => {
      expect(editorMock.commands.setContent).toHaveBeenCalledWith(
        {
          type: 'doc',
          content: [
            {
              type: 'paragraph',
              content: [
                { type: 'text', text: '重点', marks: [{ type: 'bold' }] },
                { type: 'hardBreak' },
                { type: 'text', text: '下一行', marks: [] },
              ],
            },
          ],
        },
        false,
      );
    });

    fireEvent.click(screen.getByRole('button', { name: '保存版本' }));

    await waitFor(() => {
      expect(apiClient.createVersion).toHaveBeenCalledWith(scene.id, {
        content_markdown: '**重点**  \n下一行',
        summary: scene.title,
        source_type: 'human_revised',
      });
    });
  });

  it('guides an unreviewed version through review before approval', async () => {
    vi.mocked(apiClient.listVersions).mockResolvedValue([
      version('not_reviewed'),
    ]);
    renderWithQuery(<SceneEditor scene={scene} />);

    fireEvent.click(await screen.findByRole('button', { name: '先审查' }));

    await waitFor(() => {
      expect(apiClient.runReview).toHaveBeenCalledWith('version-1');
    });
    expect(apiClient.approveVersion).not.toHaveBeenCalled();
  });

  it('uses the selected model profile for approval review', async () => {
    vi.mocked(apiClient.listVersions).mockResolvedValue([
      version('not_reviewed'),
    ]);
    renderWithQuery(<SceneEditor scene={scene} modelProfileId="profile-1" />);

    fireEvent.click(await screen.findByRole('button', { name: '先审查' }));

    await waitFor(() => {
      expect(apiClient.runReview).toHaveBeenCalledWith('version-1', 'profile-1');
    });
  });

  it('approves a completed review without an override', async () => {
    vi.mocked(apiClient.listVersions).mockResolvedValue([version('completed')]);
    renderWithQuery(<SceneEditor scene={scene} />);

    fireEvent.click(await screen.findByRole('button', { name: '批准' }));

    await waitFor(() => {
      expect(apiClient.approveVersion).toHaveBeenCalledWith(
        scene.id,
        'version-1',
        undefined,
      );
    });
  });

  it('collects a reason before forcing approval with blocking issues', async () => {
    vi.mocked(apiClient.listVersions).mockResolvedValue([version('completed')]);
    vi.mocked(apiClient.approveVersion)
      .mockRejectedValueOnce(apiError('BLOCKING_REVIEW_ISSUES'))
      .mockResolvedValueOnce({
        ...scene,
        approved_version_id: 'version-1',
        status: 'canonicalizing',
      });
    renderWithQuery(<SceneEditor scene={scene} />);

    fireEvent.click(await screen.findByRole('button', { name: '批准' }));

    await waitFor(() => {
      expect(apiClient.approveVersion).toHaveBeenLastCalledWith(
        scene.id,
        'version-1',
        '作者确认这是有意安排',
      );
    });
  });

  it('shows a clear message when historical replacement is unavailable', async () => {
    vi.mocked(apiClient.listVersions).mockResolvedValue([version('completed')]);
    vi.mocked(apiClient.approveVersion).mockRejectedValue(
      apiError('HISTORICAL_REPLACEMENT_NOT_READY'),
    );
    renderWithQuery(<SceneEditor scene={scene} />);

    fireEvent.click(await screen.findByRole('button', { name: '批准' }));

    expect(
      await screen.findByText('历史正式稿替换尚未开放，请保留当前正式稿。'),
    ).toBeInTheDocument();
  });
});
