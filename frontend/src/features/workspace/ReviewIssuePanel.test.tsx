import type { ReactElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../../api/client";
import type {
  ReviewIssue,
  ReviewResult,
  ReviewRun,
} from "../../types/entities";
import { ReviewIssuePanel } from "./ReviewIssuePanel";

vi.mock("../../api/client", () => ({
  apiClient: {
    listReviewRuns: vi.fn(),
    getReviewRun: vi.fn(),
    runReview: vi.fn(),
    updateIssue: vi.fn(),
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

const now = "2026-07-11T00:00:00.000Z";

const latestRun: ReviewRun = {
  id: "run-latest",
  scene_version_id: "sv-1",
  model_profile_id: null,
  provider: "fake",
  model: "fake-model",
  status: "completed",
  prompt_snapshot_json: {},
  started_at: now,
  completed_at: now,
  summary: "发现 1 个问题",
  created_at: now,
  updated_at: now,
};

const olderRun: ReviewRun = {
  ...latestRun,
  id: "run-older",
  summary: "未发现问题",
  created_at: "2026-07-10T00:00:00.000Z",
  updated_at: "2026-07-10T00:00:00.000Z",
};

const issue: ReviewIssue = {
  id: "issue-1",
  review_run_id: latestRun.id,
  scene_version_id: "sv-1",
  issue_type: "timeline_conflict",
  severity: "high",
  evidence_json: '{"line":42}',
  conflict_rule: "The scene reveals a secret too early.",
  suggestion: "Move the reveal to a later scene.",
  confidence: 0.92,
  source_chunk_index: 0,
  source_start: 0,
  source_end: 20,
  status: "open",
  created_at: now,
  updated_at: now,
};

const latestResult: ReviewResult = { run: latestRun, issues: [issue] };
const olderResult: ReviewResult = { run: olderRun, issues: [] };
const issueActions = [
  {
    status: "accepted" as const,
    buttonLabel: "接受问题",
    statusLabel: "已接受",
  },
  {
    status: "ignored" as const,
    buttonLabel: "忽略问题",
    statusLabel: "已忽略",
  },
  {
    status: "false_positive" as const,
    buttonLabel: "标记为误报",
    statusLabel: "误报",
  },
];

describe("ReviewIssuePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.listReviewRuns).mockResolvedValue([]);
    vi.mocked(apiClient.getReviewRun).mockResolvedValue(latestResult);
    vi.mocked(apiClient.runReview).mockResolvedValue(latestResult);
    vi.mocked(apiClient.updateIssue).mockResolvedValue({
      ...issue,
      status: "accepted",
    });
  });

  it("shows the empty state before any review run exists", async () => {
    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    await waitFor(() => {
      expect(apiClient.listReviewRuns).toHaveBeenCalledWith("sv-1");
    });
    expect(await screen.findByText("尚未执行审查。")).toBeInTheDocument();
  });

  it("starts a new review run for the selected version", async () => {
    vi.mocked(apiClient.listReviewRuns)
      .mockResolvedValueOnce([])
      .mockResolvedValue([latestRun]);
    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    fireEvent.click(screen.getByRole("button", { name: "执行审查" }));

    await waitFor(() => {
      expect(apiClient.runReview).toHaveBeenCalledWith("sv-1");
    });
    expect(await screen.findByText("timeline_conflict")).toBeInTheDocument();
  });

  it("passes the selected model profile to review", async () => {
    renderWithQuery(
      <ReviewIssuePanel sceneVersionId="sv-1" modelProfileId="profile-1" />,
    );

    await screen.findByText("尚未执行审查。");
    fireEvent.click(screen.getByRole("button", { name: "执行审查" }));

    await waitFor(() => {
      expect(apiClient.runReview).toHaveBeenCalledWith("sv-1", "profile-1");
    });
  });

  it("shows the latest run and allows reading an older run", async () => {
    vi.mocked(apiClient.listReviewRuns).mockResolvedValue([
      latestRun,
      olderRun,
    ]);
    vi.mocked(apiClient.getReviewRun).mockImplementation(async (runId) =>
      runId === olderRun.id ? olderResult : latestResult,
    );

    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    expect(await screen.findByText("timeline_conflict")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("审查轮次"), {
      target: { value: olderRun.id },
    });

    expect(await screen.findByText("未发现问题")).toBeInTheDocument();
    expect(apiClient.getReviewRun).toHaveBeenLastCalledWith(olderRun.id);
  });

  it("does not present a failed run as no issues", async () => {
    const failedRun: ReviewRun = {
      ...latestRun,
      id: "run-failed",
      status: "failed",
      summary: "审查执行失败",
    };
    vi.mocked(apiClient.listReviewRuns).mockResolvedValue([failedRun]);
    vi.mocked(apiClient.getReviewRun).mockResolvedValue({
      run: failedRun,
      issues: [],
    });

    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    expect(
      await screen.findByText("本轮审查失败，请重新执行审查。"),
    ).toBeInTheDocument();
    expect(screen.queryByText("未发现问题")).not.toBeInTheDocument();
  });

  it.each(issueActions)(
    "updates an issue to $status in the selected run and refetches it",
    async ({ status, buttonLabel, statusLabel }) => {
      vi.mocked(apiClient.listReviewRuns).mockResolvedValue([latestRun]);
      vi.mocked(apiClient.getReviewRun)
        .mockResolvedValueOnce(latestResult)
        .mockResolvedValueOnce({
          run: latestRun,
          issues: [{ ...issue, status }],
        });
      vi.mocked(apiClient.updateIssue).mockResolvedValue({ ...issue, status });

      renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

      fireEvent.click(await screen.findByLabelText(buttonLabel));

      await waitFor(() => {
        expect(apiClient.updateIssue).toHaveBeenCalledWith("issue-1", status);
      });
      expect(await screen.findByText(statusLabel)).toBeInTheDocument();
    },
  );

  it("refreshes the run list and selected run", async () => {
    vi.mocked(apiClient.listReviewRuns).mockResolvedValue([latestRun]);

    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    await screen.findByText("timeline_conflict");
    fireEvent.click(screen.getByRole("button", { name: "刷新" }));

    await waitFor(() => {
      expect(apiClient.listReviewRuns).toHaveBeenCalledTimes(2);
      expect(apiClient.getReviewRun).toHaveBeenCalledTimes(2);
    });
  });

  it("does not call APIs when sceneVersionId is empty", () => {
    renderWithQuery(<ReviewIssuePanel sceneVersionId="" />);

    expect(screen.getByRole("button", { name: "执行审查" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "刷新" })).toBeDisabled();
    expect(apiClient.listReviewRuns).not.toHaveBeenCalled();
    expect(apiClient.runReview).not.toHaveBeenCalled();
  });

  it("shows a retryable error when starting a review fails", async () => {
    vi.mocked(apiClient.runReview).mockRejectedValue(new Error("network"));
    renderWithQuery(<ReviewIssuePanel sceneVersionId="sv-1" />);

    await screen.findByText("尚未执行审查。");
    fireEvent.click(screen.getByRole("button", { name: "执行审查" }));

    expect(
      await screen.findByText("审查操作失败，请刷新后重试。"),
    ).toBeInTheDocument();
  });
});
