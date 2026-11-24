import { createRoot } from "react-dom/client";
import { App } from "./app";
import "./synapse/tokens.css";
import "./synapse/components.css";
import "./styles/theme.css";
import "./styles/app.css";

createRoot(document.getElementById("root")).render(<App />);
