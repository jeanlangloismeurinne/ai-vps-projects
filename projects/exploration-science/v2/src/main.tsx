import "@fontsource/inter/400.css";
import "@fontsource/inter/600.css";
import "./style.css";
import { createRoot } from "react-dom/client";
import { App } from "./App";

if (new URLSearchParams(window.location.search).has("silhouette")) document.body.classList.add("silhouette");

createRoot(document.getElementById("root")!).render(<App />);
