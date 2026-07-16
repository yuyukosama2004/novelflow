import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import type {
  ReviewResult,
  ReviewRun,
  Scene,
  SceneVersion,
} from "../../types/entities";
import { SceneEditor } from "./SceneEditor";
import { SceneApprovalPanel } from "./SceneApprovalPanel";

const { editorMock, editorOptions } = vi.hoisted(() => ({
  editorMock: {
    commands: { setContent: vi.fn() },
    getJSON: vi.fn(),
  },
  editorOptions: {
    current: undefined as
      | { onUpdate?: (event: { editor: unknown }) => void }
      | undefined,
  },
}));

vi.mock("@tiptap/react", () => ({
  EditorContent: () => <div data-testid="editor" />,
  useEditor: (options: { onUpdate?: (event: { editor: unknown }) => void }) => {
    editorOptions.current = options;
    return editorMock;
  },
}));

vi.mock("../../api/client", () => ({
  apiClient: {
    listVersions: vi.fn(),
    createVersion: vi.fn(),
    getWorkingDraft: vi.fn(),
    updateWorkingDraft: vi.fn(),
    approveVersion: vi.fn(),
    runReview: vi.fn(),
  },
}));

function renderWithQuery(
  ui: ReactElement,
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  }),
) {
  return {
    ...render(
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
    ),
    queryClient,
  };
}

const now = "2026-07-11T00:00:00.000Z";

const scene: Scene = {
  id: "scene-1",
  chapter_id: "chapter-1",
  sequence_no: 1,
  title: "测试场景",
  pov_character_id: null,
  time_text: "",
  story_time_order: 1,
  location_id: null,
  goal: "",
  conflict: "",
  turning_point: "",
  ending_hook: "",
  must_include_json: [],
  must_not_reveal_json: [],
  forbidden_actions_json: [],
  status: "reviewing",
  approved_version_id: null,
  is_stale: false,
  created_at: now,
  updated_at: now,
};

function version(reviewStatus: string): SceneVersion {
  return {
    id: "version-1",
    scene_id: scene.id,
    version_no: 1,
    parent_version_id: null,
    branch_name: "main",
    content_json: { type: "doc", content: [{ type: "paragraph" }] },
    content_markdown: "正文",
    content_text: "正文",
    document_schema_version: "novelflow.tiptap.v1",
    document_hash: "0".repeat(64),
    summary: "",
    source_type: "human",
    model_profile_id: null,
    prompt_snapshot_json: {},
    context_manifest_json: {},
    review_status: reviewStatus,
    created_by: "user",
    approved_at: null,
    approval_override_reason: null,
    superseded_at: null,
    superseded_by_version_id: null,
    created_at: now,
    updated_at: now,
  };
}

const completedRun: ReviewRun = {
  id: "run-1",
  scene_version_id: "version-1",
  model_profile_id: null,
  provider: "fake",
  model: "fake-model",
  status: "completed",
  prompt_snapshot_json: {},
  started_at: now,
  completed_at: now,
  summary: "未发现问题",
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

describe("SceneEditor approval gate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(window, "prompt").mockReturnValue("作者确认这是有意安排");
    vi.mocked(apiClient.createVersion).mockResolvedValue(
      version("not_reviewed"),
    );
    vi.mocked(apiClient.getWorkingDraft).mockResolvedValue({
      scene_id: scene.id,
      content_json: { type: "doc", content: [{ type: "paragraph" }] },
      content_markdown: "",
      revision: 0,
      updated_at: null,
    });
    vi.mocked(apiClient.updateWorkingDraft).mockResolvedValue({
      scene_id: scene.id,
      content_json: { type: "doc", content: [{ type: "paragraph" }] },
      content_markdown: "新草稿",
      revision: 1,
      updated_at: now,
    });
    vi.mocked(apiClient.runReview).mockResolvedValue(reviewResult);
    vi.mocked(apiClient.approveVersion).mockResolvedValue({
      ...scene,
      approved_version_id: "version-1",
      status: "canonicalizing",
    });
  });

  it("normalizes legacy HTML before loading and saving a version", async () => {
    vi.mocked(apiClient.listVersions).mockResolvedValue([
      {
        ...version("not_reviewed"),
        content_markdown: "<p><strong>重点</strong><br>下一行</p>",
      },
    ]);
    renderWithQuery(<SceneEditor scene={scene} />);

    await waitFor(() => {
      expect(editorMock.commands.setContent).toHaveBeenCalledWith(
        {
          type: "doc",
          content: [
            {
              type: "paragraph",
              content: [
                { type: "text", text: "重点", marks: [{ type: "bold" }] },
                { type: "hardBreak" },
                { type: "text", text: "下一行", marks: [] },
              ],
            },
          ],
        },
        false,
      );
    });
    expect(screen.getByText("5 字")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "保存版本" }));

    await waitFor(() => {
      expect(apiClient.createVersion).toHaveBeenCalledWith(scene.id, {
        content_markdown: "**重点**  \n下一行",
        content_json: {
          type: "doc",
          content: [
            {
              type: "paragraph",
              content: [
                { type: "text", text: "重点", marks: [{ type: "bold" }] },
                { type: "hardBreak" },
                { type: "text", text: "下一行", marks: [] },
              ],
            },
          ],
        },
        summary: scene.title,
        source_type: "human_revised",
      });
    });
  });

  it("autosaves only the working draft without creating a version", async () => {
    vi.mocked(apiClient.listVersions).mockResolvedValue([]);
    renderWithQuery(<SceneEditor scene={scene} />);

    await waitFor(() => {
      expect(editorMock.commands.setContent).toHaveBeenCalled();
    });

    const document = {
      type: "doc",
      content: [
        { type: "paragraph", content: [{ type: "text", text: "新草稿" }] },
      ],
    };
    editorMock.getJSON.mockReturnValue(document);
    vi.useFakeTimers();
    act(() => {
      editorOptions.current?.onUpdate?.({ editor: editorMock });
    });
    act(() => {
      vi.advanceTimersByTime(1600);
    });
    await act(async () => Promise.resolve());
    vi.useRealTimers();

    expect(apiClient.updateWorkingDraft).toHaveBeenCalledWith(scene.id, {
      revision: 0,
      content_markdown: "新草稿",
      content_json: document,
    });
    expect(apiClient.createVersion).not.toHaveBeenCalled();
  });

  it("loads an explicitly selected newly generated version into the editor", async () => {
    const first = {
      ...version("not_reviewed"),
      id: "version-1",
      content_markdown: "旧版本",
    };
    const second = {
      ...version("not_reviewed"),
      id: "version-2",
      version_no: 2,
      content_markdown: "新生成版本",
    };
    vi.mocked(apiClient.listVersions).mockResolvedValue([first, second]);

    const rendered = renderWithQuery(
      <SceneEditor scene={scene} selectedVersionId="version-1" />,
    );
    await waitFor(() => {
      expect(editorMock.commands.setContent).toHaveBeenCalledWith(
        expect.objectContaining({ content: expect.any(Array) }),
        false,
      );
    });

    rendered.rerender(
      <QueryClientProvider client={rendered.queryClient}>
        <SceneEditor
          scene={scene}
          selectedVersionId="version-2"
          loadSelectedVersion
        />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(editorMock.commands.setContent).toHaveBeenLastCalledWith(
        {
          type: "doc",
          content: [
            {
              type: "paragraph",
              content: [{ type: "text", text: "新生成版本" }],
            },
          ],
        },
        false,
      );
    });
  });

  it("saves a pending draft before manually creating a version", async () => {
    vi.mocked(apiClient.listVersions).mockResolvedValue([]);
    renderWithQuery(<SceneEditor scene={scene} />);

    await waitFor(() => {
      expect(editorMock.commands.setContent).toHaveBeenCalled();
    });
    const document = {
      type: "doc",
      content: [
        { type: "paragraph", content: [{ type: "text", text: "立即保存" }] },
      ],
    };
    editorMock.getJSON.mockReturnValue(document);
    act(() => {
      editorOptions.current?.onUpdate?.({ editor: editorMock });
    });

    fireEvent.click(screen.getByRole("button", { name: "保存版本" }));

    await waitFor(() => {
      expect(apiClient.createVersion).toHaveBeenCalled();
    });
    expect(apiClient.updateWorkingDraft).toHaveBeenCalledWith(scene.id, {
      revision: 0,
      content_markdown: "立即保存",
      content_json: document,
    });
    expect(
      vi.mocked(apiClient.updateWorkingDraft).mock.invocationCallOrder[0],
    ).toBeLessThan(
      vi.mocked(apiClient.createVersion).mock.invocationCallOrder[0],
    );
  });

  it("guides an unreviewed version through review before approval", async () => {
    renderWithQuery(
      <SceneApprovalPanel scene={scene} versions={[version("not_reviewed")]} />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "先审查" }));

    await waitFor(() => {
      expect(apiClient.runReview).toHaveBeenCalledWith("version-1");
    });
    expect(apiClient.approveVersion).not.toHaveBeenCalled();
  });

  it("uses the selected model profile for approval review", async () => {
    renderWithQuery(
      <SceneApprovalPanel
        scene={scene}
        versions={[version("not_reviewed")]}
        modelProfileId="profile-1"
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "先审查" }));

    await waitFor(() => {
      expect(apiClient.runReview).toHaveBeenCalledWith(
        "version-1",
        "profile-1",
      );
    });
  });

  it("approves a completed review without an override", async () => {
    renderWithQuery(
      <SceneApprovalPanel scene={scene} versions={[version("completed")]} />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "批准" }));

    await waitFor(() => {
      expect(apiClient.approveVersion).toHaveBeenCalledWith(
        scene.id,
        "version-1",
        undefined,
      );
    });
  });

  it("collects a reason before forcing approval with blocking issues", async () => {
    vi.mocked(apiClient.approveVersion)
      .mockRejectedValueOnce(apiError("BLOCKING_REVIEW_ISSUES"))
      .mockResolvedValueOnce({
        ...scene,
        approved_version_id: "version-1",
        status: "canonicalizing",
      });
    renderWithQuery(
      <SceneApprovalPanel scene={scene} versions={[version("completed")]} />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "批准" }));

    await waitFor(() => {
      expect(apiClient.approveVersion).toHaveBeenLastCalledWith(
        scene.id,
        "version-1",
        "作者确认这是有意安排",
      );
    });
  });

  it("shows a clear message when historical replacement is unavailable", async () => {
    vi.mocked(apiClient.approveVersion).mockRejectedValue(
      apiError("HISTORICAL_REPLACEMENT_NOT_READY"),
    );
    renderWithQuery(
      <SceneApprovalPanel scene={scene} versions={[version("completed")]} />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "批准" }));

    expect(
      await screen.findByText("历史正式稿替换尚未开放，请保留当前正式稿。"),
    ).toBeInTheDocument();
  });
});
