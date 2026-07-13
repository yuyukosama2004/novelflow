import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter } from "react-router-dom";

const StoryBiblePage = lazy(() =>
  import("./features/bible/StoryBiblePage").then((module) => ({
    default: module.StoryBiblePage,
  })),
);
const ProjectListPage = lazy(() =>
  import("./features/projects/ProjectListPage").then((module) => ({
    default: module.ProjectListPage,
  })),
);
const QuickCreationPage = lazy(() =>
  import("./features/quick/QuickCreationPage").then((module) => ({
    default: module.QuickCreationPage,
  })),
);
const ModelSettingsPage = lazy(() =>
  import("./features/settings/ModelSettingsPage").then((module) => ({
    default: module.ModelSettingsPage,
  })),
);
const CreationWizardPage = lazy(() =>
  import("./features/wizard/CreationWizardPage").then((module) => ({
    default: module.CreationWizardPage,
  })),
);
const WorkspacePage = lazy(() =>
  import("./features/workspace/WorkspacePage").then((module) => ({
    default: module.WorkspacePage,
  })),
);

function withLoading(page: ReactNode) {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center bg-stone-50 text-sm text-stone-500">
          正在打开工作区…
        </main>
      }
    >
      {page}
    </Suspense>
  );
}

export const router = createBrowserRouter([
  {
    path: "/quick",
    element: withLoading(<QuickCreationPage />),
  },
  {
    path: "/",
    element: withLoading(<ProjectListPage />),
  },
  {
    path: "/projects/:projectId",
    element: withLoading(<WorkspacePage />),
  },
  {
    path: "/projects/:projectId/wizard",
    element: withLoading(<CreationWizardPage />),
  },
  {
    path: "/projects/:projectId/bible",
    element: withLoading(<StoryBiblePage />),
  },
  {
    path: "/settings/models",
    element: withLoading(<ModelSettingsPage />),
  },
]);
