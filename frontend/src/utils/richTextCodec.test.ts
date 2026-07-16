import { describe, expect, it } from "vitest";

import documentContracts from "../../../contracts/scene-document-v1.json";
import { RichTextCodec, RichTextCodecError } from "./richTextCodec";

describe("RichTextCodec", () => {
  it("matches the shared scene-document contract", () => {
    for (const contract of documentContracts) {
      expect(RichTextCodec.toMarkdown(contract.document), contract.name).toBe(
        contract.markdown,
      );
      expect(RichTextCodec.toPlaintext(contract.document), contract.name).toBe(
        contract.plaintext,
      );
    }
  });

  it("serializes supported Tiptap nodes to Markdown and plaintext", () => {
    const document = {
      type: "doc",
      content: [
        {
          type: "heading",
          attrs: { level: 2 },
          content: [{ type: "text", text: "标题" }],
        },
        {
          type: "paragraph",
          content: [
            { type: "text", text: "粗体", marks: [{ type: "bold" }] },
            { type: "text", text: "、" },
            { type: "text", text: "斜体", marks: [{ type: "italic" }] },
            { type: "text", text: "、" },
            { type: "text", text: "删除", marks: [{ type: "strike" }] },
            { type: "hardBreak" },
            { type: "text", text: "行内代码", marks: [{ type: "code" }] },
          ],
        },
        {
          type: "blockquote",
          content: [
            { type: "paragraph", content: [{ type: "text", text: "引用" }] },
          ],
        },
        {
          type: "codeBlock",
          attrs: { language: "ts" },
          content: [{ type: "text", text: "const answer = 42;" }],
        },
        {
          type: "bulletList",
          content: [
            {
              type: "listItem",
              content: [
                { type: "paragraph", content: [{ type: "text", text: "甲" }] },
              ],
            },
            {
              type: "listItem",
              content: [
                { type: "paragraph", content: [{ type: "text", text: "乙" }] },
              ],
            },
          ],
        },
        {
          type: "orderedList",
          attrs: { start: 3 },
          content: [
            {
              type: "listItem",
              content: [
                {
                  type: "paragraph",
                  content: [{ type: "text", text: "第三项" }],
                },
              ],
            },
          ],
        },
        { type: "horizontalRule" },
      ],
    };

    const markdown = RichTextCodec.toMarkdown(document);
    const plaintext = RichTextCodec.toPlaintext(document);

    expect(markdown).toContain("## 标题");
    expect(markdown).toContain("**粗体**、*斜体*、~~删除~~  \n`行内代码`");
    expect(markdown).toContain("> 引用");
    expect(markdown).toContain("```ts\nconst answer = 42;\n```");
    expect(markdown).toContain("- 甲\n- 乙");
    expect(markdown).toContain("3. 第三项");
    expect(markdown).toContain("\n---");
    expect(markdown).not.toMatch(/<\/?[a-z][^>]*>/i);
    expect(plaintext).toContain("标题\n粗体、斜体、删除\n行内代码");
    expect(plaintext).toContain("甲\n乙");
  });

  it("round-trips supported Markdown through Tiptap JSON", () => {
    const markdown = [
      "# 标题",
      "",
      "段落含 **粗体**、*斜体*、~~删除~~ 和 `代码`。  ",
      "下一行。",
      "",
      "> 引用内容",
      "",
      "- 第一项",
      "- 第二项",
      "",
      "1. 有序项",
      "",
      "---",
      "",
      "```python",
      'print("ok")',
      "```",
    ].join("\n");

    const json = RichTextCodec.toTiptapJson(markdown);
    const normalized = RichTextCodec.toMarkdown(json);

    expect(normalized).toContain("# 标题");
    expect(normalized).toContain("**粗体**");
    expect(normalized).toContain("*斜体*");
    expect(normalized).toContain("~~删除~~");
    expect(normalized).toContain("`代码`");
    expect(normalized).toContain("  \n下一行。");
    expect(normalized).toContain("> 引用内容");
    expect(normalized).toContain("- 第一项\n- 第二项");
    expect(normalized).toContain("1. 有序项");
    expect(normalized).toContain('```python\nprint("ok")\n```');
  });

  it("imports legacy HTML and emits normalized Markdown without tags", () => {
    const json = RichTextCodec.toTiptapJson(
      "<h2>旧标题</h2><p><strong>重点</strong><br>换行</p><ul><li>条目</li></ul>",
    );
    const markdown = RichTextCodec.toMarkdown(json);

    expect(markdown).toBe("## 旧标题\n\n**重点**  \n换行\n\n- 条目");
    expect(markdown).not.toContain("<");
  });

  it("degrades unsupported HTML to readable plain text", () => {
    const json = RichTextCodec.toTiptapJson(
      "<section><u>仍需保留</u></section>",
    );

    expect(RichTextCodec.toPlaintext(json)).toBe("仍需保留");
  });

  it("rejects unsupported Tiptap nodes instead of silently dropping them", () => {
    expect(() =>
      RichTextCodec.toMarkdown({
        type: "doc",
        content: [{ type: "table", content: [] }],
      }),
    ).toThrow(RichTextCodecError);
  });
});
