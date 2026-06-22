import { createBrowserRouter } from 'react-router-dom';

import { ProjectListPage } from './features/projects/ProjectListPage';
import { WorkspacePage } from './features/workspace/WorkspacePage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <ProjectListPage />,
  },
  {
    path: '/projects/:projectId',
    element: <WorkspacePage />,
  },
]);
