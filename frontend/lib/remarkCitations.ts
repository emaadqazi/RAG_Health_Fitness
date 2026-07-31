import type { Root, Text } from "mdast";
import type { Parent } from "unist";
import { visit } from "unist-util-visit";

const CITATION_RE = /\[(\d+)\]/g;

/**
 * Turns inline `[n]` citation markers in text nodes into a custom `citation-chip`
 * element (via mdast `data.hName`/`hProperties`, the standard mdast-to-hast passthrough)
 * so react-markdown can render them as clickable chips instead of plain text.
 */
export function remarkCitations() {
  return (tree: Root) => {
    visit(tree, "text", (node: Text, index, parent: Parent | undefined) => {
      if (!parent || index === undefined) return;
      const value = node.value;
      CITATION_RE.lastIndex = 0;
      if (!CITATION_RE.test(value)) return;
      CITATION_RE.lastIndex = 0;

      const newNodes: (Text | { type: string; data: { hName: string; hProperties: { n: number } } })[] = [];
      let lastIndex = 0;
      let match: RegExpExecArray | null;
      while ((match = CITATION_RE.exec(value)) !== null) {
        if (match.index > lastIndex) {
          newNodes.push({ type: "text", value: value.slice(lastIndex, match.index) });
        }
        newNodes.push({
          type: "citationChip",
          data: { hName: "citation-chip", hProperties: { n: Number(match[1]) } },
        });
        lastIndex = match.index + match[0].length;
      }
      if (lastIndex < value.length) {
        newNodes.push({ type: "text", value: value.slice(lastIndex) });
      }

      parent.children.splice(index, 1, ...(newNodes as never[]));
      return index + newNodes.length;
    });
  };
}
