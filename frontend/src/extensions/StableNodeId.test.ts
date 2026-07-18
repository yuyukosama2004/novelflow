import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { describe, expect, it } from "vitest";

import { StableNodeId } from "./StableNodeId";

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

describe("StableNodeId", () => {
  it("preserves existing identities and assigns unique IDs to new blocks", () => {
    const existingId = "13a4b02a-4a2e-4a7b-a88e-6e47d6c8184f";
    const editor = new Editor({
      extensions: [StarterKit, StableNodeId],
      content: "",
    });
    editor.commands.setContent({
      type: "doc",
      content: [
        {
          type: "paragraph",
          attrs: { nodeId: existingId },
          content: [{ type: "text", text: "existing" }],
        },
        {
          type: "paragraph",
          content: [{ type: "text", text: "missing" }],
        },
      ],
    });

    const initial = editor.getJSON();
    const initialIds = initial.content?.map((node) => node.attrs?.nodeId);
    expect(initialIds?.[0]).toBe(existingId);
    expect(initialIds?.[1]).toMatch(UUID_PATTERN);

    editor.commands.insertContentAt(editor.state.doc.content.size, {
      type: "paragraph",
      content: [{ type: "text", text: "new" }],
    });
    const updatedIds = editor
      .getJSON()
      .content?.map((node) => String(node.attrs?.nodeId));

    expect(updatedIds?.slice(0, 2)).toEqual(initialIds);
    expect(updatedIds?.[2]).toMatch(UUID_PATTERN);
    expect(new Set(updatedIds).size).toBe(3);
    editor.destroy();
  });
});
