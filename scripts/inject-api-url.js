const fs = require("fs");
const path = require("path");

const API_URL = process.env.VITE_API_URL || process.env.API_URL || "";
const htmlPath = path.join(__dirname, "..", "static", "index.html");

let html = fs.readFileSync(htmlPath, "utf-8");
html = html.replace(
  'window.__API_BASE__ = ""',
  `window.__API_BASE__ = "${API_URL}"`
);
fs.writeFileSync(htmlPath, html, "utf-8");

console.log(`Injected API_URL: "${API_URL}" into index.html`);
