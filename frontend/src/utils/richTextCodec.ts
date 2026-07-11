export interface RichTextMark {
  type: string;
  attrs?: Record<string, unknown>;
}

export interface RichTextNode {
  type: string;
  attrs?: Record<string, unknown>;
  content?: RichTextNode[];
  marks?: RichTextMark[];
  text?: string;
}

export class RichTextCodecError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RichTextCodecError';
  }
}

const BLOCK_TAGS = new Set([
  'P',
  'H1',
  'H2',
  'H3',
  'H4',
  'H5',
  'H6',
  'BLOCKQUOTE',
  'PRE',
  'UL',
  'OL',
  'HR',
]);

function asNode(value: unknown): RichTextNode {
  if (!value || typeof value !== 'object' || !('type' in value)) {
    throw new RichTextCodecError('富文本内容不是有效的 Tiptap JSON。');
  }
  return value as RichTextNode;
}

function unsupported(node: RichTextNode): never {
  throw new RichTextCodecError(`暂不支持富文本节点：${node.type}`);
}

function escapeMarkdown(text: string): string {
  return text.replace(/([\\`*_[\]~])/g, '\\$1');
}

function serializeInline(nodes: RichTextNode[] = []): string {
  return nodes
    .map((node) => {
      if (node.type === 'hardBreak') return '  \n';
      if (node.type !== 'text') return unsupported(node);
      const marks = node.marks ?? [];
      const hasCode = marks.some((mark) => mark.type === 'code');
      let text = hasCode ? (node.text ?? '') : escapeMarkdown(node.text ?? '');
      const wrappers: Record<string, [string, string]> = {
        code: ['`', '`'],
        bold: ['**', '**'],
        italic: ['*', '*'],
        strike: ['~~', '~~'],
      };
      for (const mark of marks) {
        const wrapper = wrappers[mark.type];
        if (!wrapper) {
          throw new RichTextCodecError(`暂不支持富文本标记：${mark.type}`);
        }
        text = wrapper[0] + text + wrapper[1];
      }
      return text;
    })
    .join('');
}

function serializeList(node: RichTextNode, ordered: boolean): string {
  const start = Number(node.attrs?.start ?? 1);
  return (node.content ?? [])
    .map((item, index) => {
      if (item.type !== 'listItem') return unsupported(item);
      const blocks = item.content ?? [];
      const first = blocks[0];
      if (!first || first.type !== 'paragraph') {
        throw new RichTextCodecError('列表项必须以段落开始。');
      }
      const marker = ordered ? `${start + index}. ` : '- ';
      const lines = [marker + serializeInline(first.content)];
      for (const child of blocks.slice(1)) {
        const rendered = serializeBlock(child)
          .split('\n')
          .map((line) => `  ${line}`)
          .join('\n');
        lines.push(rendered);
      }
      return lines.join('\n');
    })
    .join('\n');
}

function serializeBlock(node: RichTextNode): string {
  if (node.type === 'paragraph') return serializeInline(node.content);
  if (node.type === 'heading') {
    const level = Math.min(6, Math.max(1, Number(node.attrs?.level ?? 1)));
    return `${'#'.repeat(level)} ${serializeInline(node.content)}`;
  }
  if (node.type === 'blockquote') {
    return serializeBlocks(node.content)
      .split('\n')
      .map((line) => `> ${line}`.trimEnd())
      .join('\n');
  }
  if (node.type === 'codeBlock') {
    const language = String(node.attrs?.language ?? '');
    const code = (node.content ?? []).map((child) => child.text ?? '').join('');
    return `\`\`\`${language}\n${code}\n\`\`\``;
  }
  if (node.type === 'bulletList') return serializeList(node, false);
  if (node.type === 'orderedList') return serializeList(node, true);
  if (node.type === 'horizontalRule') return '---';
  return unsupported(node);
}

function serializeBlocks(nodes: RichTextNode[] = []): string {
  return nodes.map(serializeBlock).join('\n\n');
}

function inlinePlaintext(nodes: RichTextNode[] = []): string {
  return nodes
    .map((node) => {
      if (node.type === 'text') return node.text ?? '';
      if (node.type === 'hardBreak') return '\n';
      return unsupported(node);
    })
    .join('');
}

function blockPlaintext(node: RichTextNode): string {
  if (node.type === 'paragraph' || node.type === 'heading') {
    return inlinePlaintext(node.content);
  }
  if (node.type === 'blockquote') return plaintextBlocks(node.content);
  if (node.type === 'codeBlock') {
    return (node.content ?? []).map((child) => child.text ?? '').join('');
  }
  if (node.type === 'bulletList' || node.type === 'orderedList') {
    return (node.content ?? [])
      .map((item) => {
        if (item.type !== 'listItem') return unsupported(item);
        return plaintextBlocks(item.content);
      })
      .join('\n');
  }
  if (node.type === 'horizontalRule') return '';
  return unsupported(node);
}

function plaintextBlocks(nodes: RichTextNode[] = []): string {
  return nodes.map(blockPlaintext).filter(Boolean).join('\n');
}

function marked(nodes: RichTextNode[], mark: RichTextMark): RichTextNode[] {
  return nodes.map((node) => {
    if (node.type !== 'text') return node;
    return { ...node, marks: [...(node.marks ?? []), mark] };
  });
}

function parseInline(text: string): RichTextNode[] {
  const nodes: RichTextNode[] = [];
  let index = 0;
  let plain = '';

  function flush() {
    if (plain) {
      nodes.push({ type: 'text', text: plain });
      plain = '';
    }
  }

  while (index < text.length) {
    if (text[index] === '\\' && index + 1 < text.length) {
      plain += text[index + 1];
      index += 2;
      continue;
    }
    const candidates: Array<[string, string, string]> = [
      ['**', '**', 'bold'],
      ['~~', '~~', 'strike'],
      ['`', '`', 'code'],
      ['*', '*', 'italic'],
      ['_', '_', 'italic'],
    ];
    const active = candidates.find(([open]) => text.startsWith(open, index));
    if (!active) {
      plain += text[index];
      index += 1;
      continue;
    }
    const [open, close, type] = active;
    const closeIndex = text.indexOf(close, index + open.length);
    if (closeIndex < 0 || closeIndex === index + open.length) {
      plain += open;
      index += open.length;
      continue;
    }
    flush();
    const inner = text.slice(index + open.length, closeIndex);
    const children = type === 'code' ? [{ type: 'text', text: inner }] : parseInline(inner);
    nodes.push(...marked(children, { type }));
    index = closeIndex + close.length;
  }
  flush();
  return nodes;
}

function parseParagraphLines(lines: string[]): RichTextNode[] {
  const content: RichTextNode[] = [];
  lines.forEach((line, index) => {
    const hardBreak = / {2,}$/.test(line);
    content.push(...parseInline(line.replace(/ {2,}$/, '')));
    if (index < lines.length - 1) {
      content.push(hardBreak ? { type: 'hardBreak' } : { type: 'text', text: ' ' });
    }
  });
  return content;
}

function isBlockStart(line: string): boolean {
  return (
    /^```/.test(line) ||
    /^#{1,6}\s+/.test(line) ||
    /^\s*(?:[-*_]\s*){3,}$/.test(line) ||
    /^>\s?/.test(line) ||
    /^\s*[-+*]\s+/.test(line) ||
    /^\s*\d+\.\s+/.test(line)
  );
}

function parseMarkdownBlocks(lines: string[]): RichTextNode[] {
  const blocks: RichTextNode[] = [];
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }
    const fence = line.match(/^```([^\s`]*)\s*$/);
    if (fence) {
      const code: string[] = [];
      index += 1;
      while (index < lines.length && !/^```\s*$/.test(lines[index])) {
        code.push(lines[index]);
        index += 1;
      }
      if (index >= lines.length) {
        throw new RichTextCodecError('代码块缺少结束标记。');
      }
      index += 1;
      blocks.push({
        type: 'codeBlock',
        attrs: fence[1] ? { language: fence[1] } : {},
        content: code.length ? [{ type: 'text', text: code.join('\n') }] : [],
      });
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      blocks.push({
        type: 'heading',
        attrs: { level: heading[1].length },
        content: parseInline(heading[2]),
      });
      index += 1;
      continue;
    }
    if (/^\s*(?:[-*_]\s*){3,}$/.test(line)) {
      blocks.push({ type: 'horizontalRule' });
      index += 1;
      continue;
    }
    if (/^>\s?/.test(line)) {
      const quoted: string[] = [];
      while (index < lines.length && /^>\s?/.test(lines[index])) {
        quoted.push(lines[index].replace(/^>\s?/, ''));
        index += 1;
      }
      blocks.push({ type: 'blockquote', content: parseMarkdownBlocks(quoted) });
      continue;
    }
    const listMatch = line.match(/^\s*(?:(\d+)\.|([-+*]))\s+(.+)$/);
    if (listMatch) {
      const ordered = Boolean(listMatch[1]);
      const start = ordered ? Number(listMatch[1]) : 1;
      const items: RichTextNode[] = [];
      while (index < lines.length) {
        const itemMatch = lines[index].match(/^\s*(?:(\d+)\.|([-+*]))\s+(.+)$/);
        if (!itemMatch || Boolean(itemMatch[1]) !== ordered) break;
        items.push({
          type: 'listItem',
          content: [
            {
              type: 'paragraph',
              content: parseInline(itemMatch[3]),
            },
          ],
        });
        index += 1;
      }
      blocks.push({
        type: ordered ? 'orderedList' : 'bulletList',
        attrs: ordered ? { start } : {},
        content: items,
      });
      continue;
    }
    const paragraph: string[] = [line];
    index += 1;
    while (
      index < lines.length &&
      lines[index].trim() &&
      !isBlockStart(lines[index])
    ) {
      paragraph.push(lines[index]);
      index += 1;
    }
    blocks.push({ type: 'paragraph', content: parseParagraphLines(paragraph) });
  }
  return blocks;
}

function inlineFromDom(node: Node, marks: RichTextMark[] = []): RichTextNode[] {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.textContent ? [{ type: 'text', text: node.textContent, marks }] : [];
  }
  if (!(node instanceof Element)) return [];
  if (node.tagName === 'BR') return [{ type: 'hardBreak' }];
  const markTypes: Record<string, string> = {
    STRONG: 'bold',
    B: 'bold',
    EM: 'italic',
    I: 'italic',
    S: 'strike',
    DEL: 'strike',
    STRIKE: 'strike',
    CODE: 'code',
  };
  const mark = markTypes[node.tagName];
  const nextMarks = mark ? [...marks, { type: mark }] : marks;
  return Array.from(node.childNodes).flatMap((child) => inlineFromDom(child, nextMarks));
}

function listItemFromDom(element: Element): RichTextNode {
  const content: RichTextNode[] = [];
  const inlineNodes: RichTextNode[] = [];
  for (const child of Array.from(element.childNodes)) {
    if (child instanceof Element && (child.tagName === 'UL' || child.tagName === 'OL')) {
      if (inlineNodes.length) {
        content.push({ type: 'paragraph', content: [...inlineNodes] });
        inlineNodes.length = 0;
      }
      content.push(blockFromDom(child));
    } else if (child instanceof Element && BLOCK_TAGS.has(child.tagName)) {
      if (inlineNodes.length) {
        content.push({ type: 'paragraph', content: [...inlineNodes] });
        inlineNodes.length = 0;
      }
      content.push(blockFromDom(child));
    } else {
      inlineNodes.push(...inlineFromDom(child));
    }
  }
  if (inlineNodes.length || content.length === 0) {
    content.unshift({ type: 'paragraph', content: inlineNodes });
  }
  return { type: 'listItem', content };
}

function blockFromDom(element: Element): RichTextNode {
  if (element.tagName === 'P') {
    return { type: 'paragraph', content: inlineFromDom(element) };
  }
  const heading = element.tagName.match(/^H([1-6])$/);
  if (heading) {
    return {
      type: 'heading',
      attrs: { level: Number(heading[1]) },
      content: inlineFromDom(element),
    };
  }
  if (element.tagName === 'BLOCKQUOTE') {
    return { type: 'blockquote', content: blocksFromDom(element) };
  }
  if (element.tagName === 'PRE') {
    const code = element.querySelector('code');
    return {
      type: 'codeBlock',
      content: code?.textContent ? [{ type: 'text', text: code.textContent }] : [],
    };
  }
  if (element.tagName === 'UL' || element.tagName === 'OL') {
    const children = Array.from(element.children)
      .filter((child) => child.tagName === 'LI')
      .map(listItemFromDom);
    return {
      type: element.tagName === 'OL' ? 'orderedList' : 'bulletList',
      attrs:
        element.tagName === 'OL'
          ? { start: Number(element.getAttribute('start') ?? 1) }
          : {},
      content: children,
    };
  }
  if (element.tagName === 'HR') return { type: 'horizontalRule' };
  return {
    type: 'paragraph',
    content: element.textContent ? [{ type: 'text', text: element.textContent }] : [],
  };
}

function blocksFromDom(parent: ParentNode): RichTextNode[] {
  const blocks: RichTextNode[] = [];
  for (const child of Array.from(parent.childNodes)) {
    if (child.nodeType === Node.TEXT_NODE) {
      if (child.textContent?.trim()) {
        blocks.push({ type: 'paragraph', content: [{ type: 'text', text: child.textContent }] });
      }
      continue;
    }
    if (child instanceof Element) blocks.push(blockFromDom(child));
  }
  return blocks;
}

function parseHtml(html: string): RichTextNode {
  if (typeof DOMParser === 'undefined') {
    throw new RichTextCodecError('当前环境无法导入旧 HTML。');
  }
  const document = new DOMParser().parseFromString(html, 'text/html');
  return { type: 'doc', content: blocksFromDom(document.body) };
}

export const RichTextCodec = {
  toMarkdown(value: unknown): string {
    const document = asNode(value);
    if (document.type !== 'doc') {
      throw new RichTextCodecError('富文本根节点必须是 doc。');
    }
    return serializeBlocks(document.content).trim();
  },

  toPlaintext(value: unknown): string {
    const document = asNode(value);
    if (document.type !== 'doc') {
      throw new RichTextCodecError('富文本根节点必须是 doc。');
    }
    return plaintextBlocks(document.content).trim();
  },

  toTiptapJson(value: string): RichTextNode {
    const source = value.trim();
    if (!source) return { type: 'doc', content: [{ type: 'paragraph' }] };
    if (/^<[a-z][\s\S]*>/i.test(source)) return parseHtml(source);
    return {
      type: 'doc',
      content: parseMarkdownBlocks(source.replace(/\r\n?/g, '\n').split('\n')),
    };
  },
};
