import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  return <main aria-label="Dashboard" />;
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
