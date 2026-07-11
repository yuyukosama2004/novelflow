import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SceneVersion } from "../../types/entities";
import { SceneVersionSelector } from "./SceneVersionSelector";

const now = new Date("2026-06-13T00:00:00.000Z").toISOString();

function makeVersion(
  overrides: Partial<SceneVersion> & { id: string; version_no: number },
): SceneVersion {
  return {
    scene_id: "scene-1",
    parent_version_id: null,
    branch_name: "main",
    content_json: { type: "doc", content: [{ type: "paragraph" }] },
    content_markdown: "<p>Sample content for version.</p>",
    summary: "",
    source_type: "human_revised",
    model_profile_id: null,
    prompt_snapshot_json: {},
    context_manifest_json: {},
    review_status: "none",
    created_by: "author",
    approved_at: null,
    approval_override_reason: null,
    superseded_at: null,
    superseded_by_version_id: null,
    created_at: now,
    updated_at: now,
    ...overrides,
  };
}

const versionOne = makeVersion({
  id: "v1",
  version_no: 1,
  summary: "First draft",
});
const versionTwo = makeVersion({
  id: "v2",
  version_no: 2,
  source_type: "ai_generated",
  summary: "AI generated draft",
  review_status: "pending",
});
const versionThree = makeVersion({
  id: "v3",
  version_no: 3,
  source_type: "human_revised",
  summary: "Revised draft with fixes",
  review_status: "completed",
});

describe("SceneVersionSelector", () => {
  let onSelect: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onSelect = vi.fn();
  });

  it("renders empty state when no versions are available", () => {
    render(
      <SceneVersionSelector
        versions={[]}
        approvedVersionId={null}
        selectedVersionId={null}
        onSelect={onSelect}
      />,
    );

    expect(screen.getByText("场景版本")).toBeInTheDocument();
    expect(
      screen.getByText("暂无版本，请生成或保存草稿以创建版本。"),
    ).toBeInTheDocument();
  });

  it("renders version options sorted by version_no descending", () => {
    render(
      <SceneVersionSelector
        versions={[versionOne, versionTwo, versionThree]}
        approvedVersionId={null}
        selectedVersionId={null}
        onSelect={onSelect}
      />,
    );

    const select = screen.getByRole("combobox", {
      name: "选择用于审查和记忆操作的场景版本",
    }) as HTMLSelectElement;
    const optionTexts = Array.from(select.options).map(
      (option) => option.textContent,
    );

    expect(optionTexts[0]).toContain("v3");
    expect(optionTexts[1]).toContain("v2");
    expect(optionTexts[2]).toContain("v1");
  });

  it("includes version metadata in option labels", () => {
    render(
      <SceneVersionSelector
        versions={[versionOne, versionTwo, versionThree]}
        approvedVersionId="v2"
        selectedVersionId="v2"
        onSelect={onSelect}
      />,
    );

    const select = screen.getByRole("combobox") as HTMLSelectElement;
    const options = Array.from(select.options);

    // human_revised → "人工修订"
    expect(
      options.find((option) => option.value === "v3")?.textContent,
    ).toContain("人工修订 / completed");
    // ai_generated → "AI 生成", approved → "正式"
    expect(
      options.find((option) => option.value === "v2")?.textContent,
    ).toContain("AI 生成 / 正式 / pending");
    expect(
      options.find((option) => option.value === "v1")?.textContent,
    ).toContain("First draft");
  });

  it("fires onSelect when the user picks a different version", () => {
    render(
      <SceneVersionSelector
        versions={[versionOne, versionTwo, versionThree]}
        approvedVersionId={null}
        selectedVersionId="v1"
        onSelect={onSelect}
      />,
    );

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "v3" } });

    expect(onSelect).toHaveBeenCalledWith("v3");
  });

  it("shows the selected version detail card with metadata", () => {
    render(
      <SceneVersionSelector
        versions={[versionOne, versionTwo, versionThree]}
        approvedVersionId="v2"
        selectedVersionId="v2"
        onSelect={onSelect}
      />,
    );

    // AI 生成（正式）
    expect(screen.getByText(/AI 生成（正式）/)).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText("AI generated draft")).toBeInTheDocument();
  });

  it("uses a readable metadata label instead of raw manuscript when summary is absent", () => {
    const noSummary = makeVersion({
      id: "v4",
      version_no: 4,
      content_markdown: "<p>This is the full content of the scene version.</p>",
      summary: "",
    });

    render(
      <SceneVersionSelector
        versions={[noSummary]}
        approvedVersionId={null}
        selectedVersionId="v4"
        onSelect={onSelect}
      />,
    );

    expect(screen.getByText("人工修订正文 · 38 字")).toBeInTheDocument();
    expect(
      screen.queryByText("This is the full content of the scene version."),
    ).not.toBeInTheDocument();
  });

  it("handles empty content gracefully", () => {
    const emptyVersion = makeVersion({
      id: "v5",
      version_no: 5,
      content_markdown: "",
      summary: "",
    });

    render(
      <SceneVersionSelector
        versions={[emptyVersion]}
        approvedVersionId={null}
        selectedVersionId="v5"
        onSelect={onSelect}
      />,
    );

    expect(screen.getByText("人工修订正文 · 0 字")).toBeInTheDocument();
  });

  it("falls back to the first rendered option when the selected id is missing", () => {
    render(
      <SceneVersionSelector
        versions={[versionOne, versionTwo]}
        approvedVersionId={null}
        selectedVersionId="missing"
        onSelect={onSelect}
      />,
    );

    expect((screen.getByRole("combobox") as HTMLSelectElement).value).toBe(
      "v2",
    );
  });
});
