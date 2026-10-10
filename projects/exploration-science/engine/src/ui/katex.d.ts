// KaTeX ships without type declarations; only what the overlay uses.
declare module "katex" {
  const katex: {
    renderToString(tex: string, options?: { throwOnError?: boolean; displayMode?: boolean; output?: "html" | "mathml" | "htmlAndMathml" }): string;
  };
  export default katex;
}
