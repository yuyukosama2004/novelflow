import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import type {
  ChangeOperation,
  ChangeSet,
  SceneWorkingDraft,
} from "../../types/entities";
import { ChangeSetReviewPanel } from "./ChangeSetReviewPanel";

vi.mock("../../api/client", () => ({
  apiClient: {
    listChangeSets: vi.fn(),
    getWorkingDraft: vi.fn(),
    applyChangeSet: vi.fn(),
  },
}));

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderWithQuery(ui: ReactElement) {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      {ui}
    </QueryClientProvider>,
  );
}

const now = "2026-07-20T08:00:00.000Z";
const originalBlock = {
  type: "paragraph",
  attrs: { nodeId: "node-1" },
  content: [{ type: "text", text: "他推开旧书店的门。" }],
};
const proposedBlock = {
  type: "paragraph",
  attrs: { nodeId: "node-1" },
  content: [{ type: "text", text: "他在雨声中推开旧书店的门。" }],
};

const operation: ChangeOperation = {
  id: "operation-1",
  change_set_id: "change-set-1",
  sequence_no: 1,
  operation_type: "replace_block",
  target_node_id: "node-1",
  anchor_before_node_id: null,
  anchor_after_node_id: null,
  original_json: originalBlock,
  proposed_json: proposedBlock,
  original_hash: "a".repeat(64),
  status: "pending",
  accepted_draft_revision: null,
  conflict_reason: "",
  created_at: now,
  updated_at: now,
};

const changeSet: ChangeSet = {
  id: "change-set-1",
  scene_id: "scene-1",
  base_working_revision: 3,
  base_document_hash: "b".repeat(64),
  base_version_id: "version-1",
  purpose: "rewrite",
  status: "pending",
  workflow_run_id: null,
  summary: "增强场景开头的氛围。",
  applied_version_id: null,
  operations: [operation],
  created_at: now,
  updated_at: now,
};

const workingDraft: SceneWorkingDraft = {
  scene_id: "scene-1",
  content_json: {
    type: "doc",
    content: [originalBlock],
  },
  content_markdown: "他推开旧书店的门。",
  revision: 3,
  updated_at: now,
};

const appliedDraft: SceneWorkingDraft = {
  ...workingDraft,
  content_json: {
    type: "doc",
    content: [proposedBlock],
  },
  content_markdown: "他在雨声中推开旧书店的门。",
  revision: 4,
};

describe("ChangeSetReviewPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.listChangeSets).mockResolvedValue([changeSet]);
    vi.mocked(apiClient.getWorkingDraft).mockResolvedValue(workingDraft);
    vi.mocked(apiClient.applyChangeSet).mockResolvedValue({
      change_set: {
        ...changeSet,
        status: "accepted",
        operations: [
          {
            ...operation,
            status: "accepted",
            accepted_draft_revision: 4,
          },
        ],
      },
      draft: appliedDraft,
    });
  });

  it("previews original and proposed blocks and applies one decision", async () => {
    const onDraftApplied = vi.fn();
    renderWithQuery(
      <ChangeSetReviewPanel
        sceneId="scene-1"
        onDraftApplied={onDraftApplied}
      />,
    );

    expect(await screen.findByText("他推开旧书店的门。")).toBeInTheDocument();
    expect(screen.getByText("他在雨声中推开旧书店的门。")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "接受" }));

    await waitFor(() => {
      expect(apiClient.applyChangeSet).toHaveBeenCalledWith("change-set-1", {
        expected_draft_revision: 3,
        accept_operation_ids: ["operation-1"],
        reject_operation_ids: [],
      });
    });
    expect(onDraftApplied).toHaveBeenCalledWith(appliedDraft);
    expect(
      await screen.findByText("改动已应用到工作草稿。"),
    ).toBeInTheDocument();
  });

  it("blocks all decisions while the editor has unsaved content", async () => {
    renderWithQuery(
      <ChangeSetReviewPanel
        sceneId="scene-1"
        disabledReason="正文还有未保存改动。"
      />,
    );

    expect(await screen.findByText("正文还有未保存改动。")).toBeInTheDocument();
    await screen.findByText("增强场景开头的氛围。");
    expect(screen.getByRole("button", { name: "接受" })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "接受全部待处理" }),
    ).toBeDisabled();
  });

  it("rejects all pending operations without applying content", async () => {
    vi.mocked(apiClient.applyChangeSet).mockResolvedValue({
      change_set: {
        ...changeSet,
        status: "rejected",
        operations: [{ ...operation, status: "rejected" }],
      },
      draft: null,
    });

    renderWithQuery(<ChangeSetReviewPanel sceneId="scene-1" />);

    await screen.findByText("增强场景开头的氛围。");
    fireEvent.click(screen.getByRole("button", { name: "拒绝全部待处理" }));

    await waitFor(() => {
      expect(apiClient.applyChangeSet).toHaveBeenCalledWith("change-set-1", {
        expected_draft_revision: 3,
        accept_operation_ids: [],
        reject_operation_ids: ["operation-1"],
      });
    });
    expect(await screen.findByText("审阅决定已保存。")).toBeInTheDocument();
  });

  it("refreshes the draft and proposals after a revision conflict", async () => {
    vi.mocked(apiClient.applyChangeSet).mockRejectedValue({
      isAxiosError: true,
      response: {
        status: 409,
        data: { details: { reason: "DRAFT_REVISION_CONFLICT" } },
      },
    });

    renderWithQuery(<ChangeSetReviewPanel sceneId="scene-1" />);

    await screen.findByText("增强场景开头的氛围。");
    fireEvent.click(screen.getByRole("button", { name: "接受" }));

    expect(
      await screen.findByText("草稿已在别处变化，已刷新最新内容，请重新审阅。"),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(apiClient.getWorkingDraft).toHaveBeenCalledTimes(2);
      expect(apiClient.listChangeSets).toHaveBeenCalledTimes(2);
    });
  });
});
