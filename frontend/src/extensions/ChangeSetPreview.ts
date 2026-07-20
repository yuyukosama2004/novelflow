import { Extension } from "@tiptap/core";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";

import type { ChangeOperation } from "../types/entities";
import { RichTextCodec, type RichTextNode } from "../utils/richTextCodec";

const previewPluginKey = new PluginKey<readonly ChangeOperation[]>(
  "changeSetPreview",
);

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    changeSetPreview: {
      setChangeSetPreview: (
        operations: readonly ChangeOperation[],
      ) => ReturnType;
    };
  }
}

interface LocatedBlock {
  node: ProseMirrorNode;
  position: number;
}

function proposedText(operation: ChangeOperation): string {
  if (!operation.proposed_json.type) {
    return "（空内容）";
  }
  try {
    return RichTextCodec.toPlaintext({
      type: "doc",
      content: [operation.proposed_json as unknown as RichTextNode],
    });
  } catch {
    return "（建议内容无法预览）";
  }
}

function previewWidget(operation: ChangeOperation, label: string): HTMLElement {
  const element = document.createElement("aside");
  element.className = "changeset-preview-widget";
  element.contentEditable = "false";
  element.dataset.changeOperationId = operation.id;
  element.dataset.changePreviewRole = "proposal";

  const badge = document.createElement("span");
  badge.className = "changeset-preview-badge";
  badge.textContent = label;

  const content = document.createElement("span");
  content.className = "changeset-preview-content";
  content.textContent = proposedText(operation);

  element.append(badge, content);
  return element;
}

function locateTopLevelBlocks(
  documentNode: ProseMirrorNode,
): Map<string, LocatedBlock> {
  const blocks = new Map<string, LocatedBlock>();
  documentNode.forEach((node, position) => {
    const nodeId = String(node.attrs.nodeId ?? "");
    if (nodeId && !blocks.has(nodeId)) {
      blocks.set(nodeId, { node, position });
    }
  });
  return blocks;
}

function createPreviewDecorations(
  documentNode: ProseMirrorNode,
  operations: readonly ChangeOperation[],
): DecorationSet {
  const blocks = locateTopLevelBlocks(documentNode);
  const decorations: Decoration[] = [];

  for (const operation of operations) {
    if (operation.status !== "pending") continue;

    if (
      operation.operation_type === "replace_block" ||
      operation.operation_type === "delete_block"
    ) {
      const target = blocks.get(operation.target_node_id ?? "");
      if (!target) continue;
      decorations.push(
        Decoration.node(
          target.position,
          target.position + target.node.nodeSize,
          {
            class:
              operation.operation_type === "delete_block"
                ? "changeset-preview-original changeset-preview-delete"
                : "changeset-preview-original changeset-preview-replace",
            "data-change-operation-id": operation.id,
            "data-change-preview-role": "original",
            title:
              operation.operation_type === "delete_block"
                ? "建议删除此段落"
                : "建议替换此段落",
          },
          { key: `${operation.id}:original` },
        ),
      );
      if (operation.operation_type === "replace_block") {
        decorations.push(
          Decoration.widget(
            target.position + target.node.nodeSize,
            () => previewWidget(operation, "建议替换"),
            {
              key: `${operation.id}:proposal`,
              side: -3000 + operation.sequence_no,
              stopEvent: () => true,
              ignoreSelection: true,
            },
          ),
        );
      }
      continue;
    }

    const isBefore = operation.operation_type === "insert_before";
    const anchorId = isBefore
      ? operation.anchor_after_node_id
      : operation.anchor_before_node_id;
    const anchor = blocks.get(anchorId ?? "");
    if (!anchor) continue;
    decorations.push(
      Decoration.widget(
        isBefore ? anchor.position : anchor.position + anchor.node.nodeSize,
        () => previewWidget(operation, isBefore ? "建议前插" : "建议后插"),
        {
          key: `${operation.id}:proposal`,
          side: isBefore
            ? -1000 + operation.sequence_no
            : -2000 + operation.sequence_no,
          stopEvent: () => true,
          ignoreSelection: true,
        },
      ),
    );
  }

  return DecorationSet.create(documentNode, decorations);
}

export const ChangeSetPreview = Extension.create({
  name: "changeSetPreview",

  addCommands() {
    return {
      setChangeSetPreview:
        (operations) =>
        ({ tr, dispatch }) => {
          if (dispatch) {
            dispatch(
              tr
                .setMeta(previewPluginKey, [...operations])
                .setMeta("addToHistory", false)
                .setMeta("preventUpdate", true),
            );
          }
          return true;
        },
    };
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: previewPluginKey,
        state: {
          init: () => [],
          apply: (transaction, previous) =>
            transaction.getMeta(previewPluginKey) ?? previous,
        },
        props: {
          decorations: (state) =>
            createPreviewDecorations(
              state.doc,
              previewPluginKey.getState(state) ?? [],
            ),
        },
      }),
    ];
  },
});
