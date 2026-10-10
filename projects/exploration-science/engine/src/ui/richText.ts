import katex from "katex";
import "katex/dist/katex.min.css";
import type { TextEntry } from "../content/types";
import { displayed } from "./texts";

const math = (tex: string) => {
  const span = document.createElement("span");
  span.innerHTML = katex.renderToString(tex, { throwOnError: false });
  return span;
};

/** Plain text with the explorable phrases wrapped (first occurrence of each). */
function textWithLinks(text: string, links: { phrase: string; node: string }[]): Node[] {
  const nodes: Node[] = [];
  let rest = text;
  while (rest.length > 0) {
    let first: { at: number; link: { phrase: string; node: string } } | null = null;
    for (const link of links) {
      const at = rest.indexOf(link.phrase);
      if (at >= 0 && (!first || at < first.at)) first = { at, link };
    }
    if (!first) break;
    nodes.push(document.createTextNode(rest.slice(0, first.at)));
    const term = Object.assign(document.createElement("span"), { className: "xs-term", textContent: first.link.phrase });
    term.dataset.node = first.link.node;
    // Spec, Termes explorables: the card needs the target node, not written yet.
    term.title = "Notion à explorer (nœud pas encore écrit)";
    nodes.push(term);
    rest = rest.slice(first.at + first.link.phrase.length);
    links = links.filter((l) => l !== first!.link);
  }
  nodes.push(document.createTextNode(rest));
  return nodes;
}

/** Displayed text: `$…$` segments typeset with KaTeX, explorable phrases marked. */
export function renderEntry(entry: TextEntry | undefined): HTMLElement {
  const root = document.createElement("div");
  const text = displayed(entry);
  const links = typeof entry === "object" ? (entry.links ?? []) : [];
  const body = document.createElement("p");
  body.className = "xs-text";
  text.split(/(\$[^$]+\$)/).forEach((part) => {
    if (part.startsWith("$") && part.endsWith("$") && part.length > 1) body.append(math(part.slice(1, -1)));
    else body.append(...textWithLinks(part, links));
  });
  root.append(body);

  // Every equation defines its terms on screen too (CLAUDE.md, Exactitude).
  if (typeof entry === "object" && entry.terms) {
    const list = document.createElement("dl");
    list.className = "xs-terms";
    for (const term of entry.terms) {
      const dt = document.createElement("dt");
      dt.append(math(term.symbol));
      const dd = document.createElement("dd");
      dd.textContent = term.unit ? `${term.meaning} (${term.unit})` : term.meaning;
      list.append(dt, dd);
    }
    root.append(list);
  }
  return root;
}
