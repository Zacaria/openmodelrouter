import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { NotificationsProvider } from "./notifications";
import "./styles.css";
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <NotificationsProvider>
      <App />
    </NotificationsProvider>
  </React.StrictMode>,
);
