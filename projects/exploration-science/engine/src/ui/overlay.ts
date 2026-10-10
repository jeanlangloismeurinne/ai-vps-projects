// DOM overlay above the canvas. Milestone 2: title, home button, node picker and
// the list of components still drawn as placeholders.

export interface OverlayHandlers {
  onHome(): void;
  onNode(id: string): void;
}

const CSS = `
.xs-overlay { position: absolute; inset: 0; pointer-events: none; font: 15px/1.4 system-ui, -apple-system, sans-serif; color: #10151c; }
.xs-overlay > * { pointer-events: auto; }
.xs-title { position: absolute; top: 12px; left: 16px; max-width: calc(100% - 220px); margin: 0; padding: 6px 14px; border-radius: 18px;
  background: rgba(255,255,255,.85); font-size: 17px; font-weight: 600; }
.xs-home { position: absolute; left: 16px; bottom: 16px; min-width: 44px; min-height: 44px; padding: 0 16px; border: 0; border-radius: 22px;
  background: rgba(255,255,255,.9); box-shadow: 0 2px 8px rgba(0,0,0,.2); font: inherit; font-weight: 600; cursor: pointer; }
.xs-node { position: absolute; top: 12px; right: 16px; min-height: 36px; font: inherit; border-radius: 8px; }
.xs-notice { position: absolute; right: 16px; bottom: 16px; max-width: 320px; padding: 8px 12px; border-radius: 8px;
  background: rgba(16,21,28,.75); color: #fff; font-size: 12px; }
.xs-notice:empty { display: none; }
`;

export class Overlay {
  private readonly title: HTMLHeadingElement;
  private readonly picker: HTMLSelectElement;
  private readonly notice: HTMLDivElement;

  constructor(container: HTMLElement, nodeIds: string[], handlers: OverlayHandlers) {
    const style = document.createElement("style");
    style.textContent = CSS;
    document.head.appendChild(style);

    const root = document.createElement("div");
    root.className = "xs-overlay";
    this.title = Object.assign(document.createElement("h1"), { className: "xs-title" });
    const home = Object.assign(document.createElement("button"), { className: "xs-home", type: "button", textContent: "↺ Retour" });
    home.addEventListener("click", () => handlers.onHome());
    this.picker = Object.assign(document.createElement("select"), { className: "xs-node", ariaLabel: "Nœud" });
    for (const id of nodeIds) this.picker.add(new Option(id, id));
    this.picker.addEventListener("change", () => handlers.onNode(this.picker.value));
    this.notice = Object.assign(document.createElement("div"), { className: "xs-notice" });
    root.append(this.title, home, this.picker, this.notice);
    container.appendChild(root);
  }

  show(nodeId: string, question: string, notices: string[]): void {
    this.title.textContent = question;
    this.picker.value = nodeId;
    this.notice.replaceChildren(...notices.map((n) => Object.assign(document.createElement("div"), { textContent: n })));
  }
}
