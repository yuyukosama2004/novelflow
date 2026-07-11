import { createBrowserRouter } from "react-router-dom";

import { StoryBiblePage } from "./features/bible/StoryBiblePage";
import { ProjectListPage } from "./features/projects/ProjectListPage";
import { QuickCreationPage } from "./features/quick/QuickCreationPage";
import { ModelSettingsPage } from "./features/settings/ModelSettingsPage";
import { CreationWizardPage } from "./features/wizard/CreationWizardPage";
import { WorkspacePage } from "./features/workspace/WorkspacePage";

export const router = createBrowserRouter([
  {
    path: "/quick",
    element: <QuickCreationPage />,
  },
  {
    path: "/",
    element: <ProjectListPage />,
  },
  {
    path: "/projects/:projectId",
    element: <WorkspacePage />,
  },
  {
    path: "/projects/:projectId/wizard",
    element: <CreationWizardPage />,
  },
  {
    path: "/projects/:projectId/bible",
    element: <StoryBiblePage />,
  },
  {
    path: "/settings/models",
    element: <ModelSettingsPage />,
  },
]);
