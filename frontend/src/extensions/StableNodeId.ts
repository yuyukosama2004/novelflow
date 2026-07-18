import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";

const ADDRESSABLE_NODE_TYPES = [
  "paragraph",
  "heading",
  "blockquote",
  "codeBlock",
  "bulletList",
  "orderedList",
  "horizontalRule",
  "listItem",
];

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function createNodeId(): string {
  if (typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0"));
  return [
    hex.slice(0, 4).join(""),
    hex.slice(4, 6).join(""),
    hex.slice(6, 8).join(""),
    hex.slice(8, 10).join(""),
    hex.slice(10).join(""),
  ].join("-");
}

export const StableNodeId = Extension.create({
  name: "stableNodeId",

  onCreate() {
    this.editor.view.dispatch(
      this.editor.state.tr
        .setMeta("preventUpdate", true)
        .setMeta("addToHistory", false),
    );
  },

  addGlobalAttributes() {
    return [
      {
        types: ADDRESSABLE_NODE_TYPES,
        attributes: {
          nodeId: {
            default: null,
            parseHTML: (element) => element.getAttribute("data-node-id"),
            renderHTML: (attributes) =>
              attributes.nodeId
                ? { "data-node-id": String(attributes.nodeId) }
                : {},
          },
        },
      },
    ];
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey("stableNodeId"),
        appendTransaction: (transactions, _oldState, newState) => {
          const seen = new Set<string>();
          let transaction = newState.tr;
          let changed = false;
          newState.doc.descendants((node, position) => {
            if (!ADDRESSABLE_NODE_TYPES.includes(node.type.name)) return;
            const candidate = String(node.attrs.nodeId ?? "");
            const nodeId =
              UUID_PATTERN.test(candidate) && !seen.has(candidate)
                ? candidate
                : createNodeId();
            seen.add(nodeId);
            if (nodeId !== candidate) {
              transaction = transaction.setNodeMarkup(position, undefined, {
                ...node.attrs,
                nodeId,
              });
              changed = true;
            }
          });
          if (!changed) return null;
          transaction.setMeta("addToHistory", false);
          if (
            transactions.some((item) => item.getMeta("preventUpdate") === true)
          ) {
            transaction.setMeta("preventUpdate", true);
          }
          return transaction;
        },
      }),
    ];
  },
});
