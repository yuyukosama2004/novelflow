import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { describe, expect, it } from "vitest";

import type { ChangeOperation } from "../types/entities";
import { ChangeSetPreview } from "./ChangeSetPreview";
import { StableNodeId } from "./StableNodeId";

const now = "2026-07-20T09:00:00.000Z";
const firstNodeId = "11111111-1111-4111-8111-111111111111";
const secondNodeId = "22222222-2222-4222-8222-222222222222";
const thirdNodeId = "33333333-3333-4333-8333-333333333333";

function operation(
  id: string,
  sequenceNo: number,
  operationType: ChangeOperation["operation_type"],
  fields: Partial<ChangeOperation>,
): ChangeOperation {
  return {
    id,
    change_set_id: "change-set-1",
    sequence_no: sequenceNo,
    operation_type: operationType,
    target_node_id: null,
    anchor_before_node_id: null,
    anchor_after_node_id: null,
    original_json: {},
    proposed_json: {},
    original_hash: "",
    status: "pending",
    accepted_draft_revision: null,
    conflict_reason: "",
    application_mode: "",
    created_at: now,
    updated_at: now,
    ...fields,
  };
}

describe("ChangeSetPreview", () => {
  it("renders pending operations in place without changing the document", () => {
    const editor = new Editor({
      extensions: [StarterKit, StableNodeId, ChangeSetPreview],
      content: {
        type: "doc",
        content: [
          {
            type: "paragraph",
            attrs: { nodeId: firstNodeId },
            content: [{ type: "text", text: "第一段" }],
          },
          {
            type: "paragraph",
            attrs: { nodeId: secondNodeId },
            content: [{ type: "text", text: "第二段" }],
          },
          {
            type: "paragraph",
            attrs: { nodeId: thirdNodeId },
            content: [{ type: "text", text: "第三段" }],
          },
        ],
      },
    });
    const before = editor.getJSON();

    editor.commands.setChangeSetPreview([
      operation("replace", 1, "replace_block", {
        target_node_id: firstNodeId,
        proposed_json: {
          type: "paragraph",
          content: [{ type: "text", text: "新的第一段" }],
        },
      }),
      operation("before", 2, "insert_before", {
        anchor_after_node_id: secondNodeId,
        proposed_json: {
          type: "paragraph",
          content: [{ type: "text", text: "插入第二段之前" }],
        },
      }),
      operation("after", 3, "insert_after", {
        anchor_before_node_id: secondNodeId,
        proposed_json: {
          type: "paragraph",
          content: [{ type: "text", text: "插入第二段之后" }],
        },
      }),
      operation("delete", 4, "delete_block", {
        target_node_id: thirdNodeId,
      }),
      operation("resolved", 5, "replace_block", {
        target_node_id: secondNodeId,
        status: "rejected",
        proposed_json: {
          type: "paragraph",
          content: [{ type: "text", text: "不应显示" }],
        },
      }),
    ]);

    expect(editor.getJSON()).toEqual(before);
    expect(
      editor.view.dom.querySelector(
        '[data-change-operation-id="replace"][data-change-preview-role="original"]',
      ),
    ).toHaveClass("changeset-preview-replace");
    expect(
      editor.view.dom.querySelector(
        '[data-change-operation-id="delete"][data-change-preview-role="original"]',
      ),
    ).toHaveClass("changeset-preview-delete");
    expect(
      editor.view.dom.querySelector(
        '[data-change-operation-id="replace"][data-change-preview-role="proposal"]',
      ),
    ).toHaveTextContent("建议替换新的第一段");
    expect(
      editor.view.dom.querySelector(
        '[data-change-operation-id="before"][data-change-preview-role="proposal"]',
      ),
    ).toHaveTextContent("建议前插插入第二段之前");
    expect(
      editor.view.dom.querySelector(
        '[data-change-operation-id="after"][data-change-preview-role="proposal"]',
      ),
    ).toHaveTextContent("建议后插插入第二段之后");
    expect(
      editor.view.dom.querySelector('[data-change-operation-id="resolved"]'),
    ).not.toBeInTheDocument();
    expect(
      Array.from(
        editor.view.dom.querySelectorAll("[data-change-preview-role]"),
        (element) =>
          `${element.getAttribute("data-change-operation-id")}:${element.getAttribute("data-change-preview-role")}`,
      ),
    ).toEqual([
      "replace:original",
      "replace:proposal",
      "before:proposal",
      "after:proposal",
      "delete:original",
    ]);

    editor.commands.setChangeSetPreview([]);

    expect(
      editor.view.dom.querySelector("[data-change-preview-role]"),
    ).not.toBeInTheDocument();
    expect(editor.getJSON()).toEqual(before);
    editor.destroy();
  });
});
