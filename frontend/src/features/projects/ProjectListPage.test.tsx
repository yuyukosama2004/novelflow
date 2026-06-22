import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

import { ProjectListView } from './ProjectListPage';
import type { NovelProject } from '../../types/entities';

const now = new Date('2026-06-13T00:00:00.000Z').toISOString();

const project: NovelProject = {
  id: 'project-1',
  created_at: now,
  updated_at: now,
  title: '雨夜档案',
  summary: '旧案阴影中的调查故事',
  genre: '悬疑',
  theme_json: {},
  target_word_count: null,
  pov_type: '第三人称限知',
  tone: '克制',
  status: 'active',
  language: 'zh-CN',
  current_timeline_position: 0,
};

it('renders projects and health status', () => {
  render(
    <BrowserRouter>
      <ProjectListView
        health={{ status: 'ok', database: 'ok', version: '0.1.0', models: {} }}
        projects={[project]}
        isLoading={false}
        onCreate={() => undefined}
        isCreating={false}
      />
    </BrowserRouter>,
  );

  expect(screen.getByText('NovelFlow')).toBeInTheDocument();
  expect(screen.getByText('雨夜档案')).toBeInTheDocument();
  expect(screen.getByText('API 0.1.0')).toBeInTheDocument();
});
