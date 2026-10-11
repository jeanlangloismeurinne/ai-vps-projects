import katex from "katex";
import "katex/dist/katex.min.css";
import type { TextEntry } from "../content/types";
import { displayed } from "./texts";

const math = (tex: string) => {
  const span = document.createElement("span");
  span.innerHTML = katex.renderToString(tex, { throwOnError: false });
  return span;
};

/** How explorable terms behave where the text is shown. */
export interface TermOptions {
  /** Clickable now: the target node exists and no arrival tour is playing. */
  live(node: string): boolean;
  /** Why a term is not clickable, as a tooltip. */
  offReason(node: string): string;
  onTerm(node: string): void;
}

/** Plain text with the explorable phrases wrapped (first occurrence of each). */
function textWithLinks(text: string, links: { phrase: string; node: string }[], options?: TermOptions): Node[] {
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
    const node = first.link.node;
    const live = options?.live(node) ?? false;
    // Spec, Termes explorables: a button when the target can be opened, else underlined only.
    const term = Object.assign(document.createElement(live ? "button" : "span"), { className: live ? "xs-term live" : "xs-term", textContent: first.link.phrase });
    term.dataset.node = node;
    if (live) {
      (term as HTMLButtonElement).type = "button";
      term.title = "Toucher pour explorer cette notion";
      term.addEventListener("click", (event) => {
        event.stopPropagation();
        options!.onTerm(node);
      });
    } else {
      term.title = options?.offReason(node) ?? "Notion à explorer (nœud pas encore écrit)";
    }
    nodes.push(term);
    rest = rest.slice(first.at + first.link.phrase.length);
    links = links.filter((l) => l !== first!.link);
  }
  nodes.push(document.createTextNode(rest));
  return nodes;
}

/** Displayed text: `$…$` segments typeset with KaTeX, explorable phrases marked. */
export function renderEntry(entry: TextEntry | undefined, options?: TermOptions): HTMLElement {
  const root = document.createElement("div");
  const text = displayed(entry);
  const links = typeof entry === "object" ? (entry.links ?? []) : [];
  const body = document.createElement("p");
  body.className = "xs-text";
  text.split(/(\$[^$]+\$)/).forEach((part) => {
    if (part.startsWith("$") && part.endsWith("$") && part.length > 1) body.append(math(part.slice(1, -1)));
    else body.append(...textWithLinks(part, links, options));
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
