import type { Level, TextEntry, Texts } from "../content/types";

export const LEVELS: { id: Level; name: string }[] = [
  { id: "discovery", name: "Découverte" },
  { id: "essential", name: "Essentiel" },
  { id: "advanced", name: "Approfondi" },
];

/** A key is looked up in the level first, then in common (texts schema). */
export function lookup(texts: Texts | undefined, level: Level, key: string | undefined): TextEntry | undefined {
  if (!texts || !key) return undefined;
  return (texts.levels[level]?.[key] ?? texts.common[key]) as TextEntry | undefined;
}

/** The displayed version: the subtitle when there is one, else the spoken text. */
export function displayed(entry: TextEntry | undefined): string {
  if (entry === undefined) return "";
  return typeof entry === "string" ? entry : (entry.subtitle ?? entry.text);
}
