"use strict";
const form = document.querySelector("#question-form");
const input = document.querySelector("#question");
const status = document.querySelector("#query-status");
const button = document.querySelector("#ask");
const log = document.querySelector("#conversation");
function node(tag, text, className) {
  const item = document.createElement(tag);
  if (text) item.textContent = text;
  if (className) item.className = className;
  return item;
}
function sourceLink(source, text) {
  const link = node("a", text);
  const url = new URL(source.url);
  if (url.protocol === "https:" && ["www.cisa.gov", "www.nist.gov"].includes(url.hostname)) link.href = url.href;
  link.target = "_blank"; link.rel = "noopener noreferrer";
  return link;
}
async function loadSources() {
  const info = document.querySelector("#source-status");
  try {
    const response = await fetch("/api/knowledge/sources");
    if (!response.ok) throw new Error("Source record unavailable. Please reload.");
    const data = await response.json();
    info.textContent = `${data.sources.length} documents · ${data.sources.reduce((n, s) => n + s.chunks, 0)} indexed passages`;
    data.sources.forEach(source => {
      const card = node("article", null, "source-card");
      card.append(node("span", `${source.id} / ${source.agency}`, "eyebrow"), sourceLink(source, source.title + " ↗"), node("p", `${source.archived ? "Archived educational source" : "Source updated " + source.source_date} · ${source.chunks} passages`));
      document.querySelector("#sources").append(card);
    });
  } catch (error) { info.textContent = error.message; }
}
document.querySelectorAll("[data-question]").forEach(item => item.addEventListener("click", () => { input.value = item.dataset.question; input.focus(); }));
form.addEventListener("submit", async event => {
  event.preventDefault();
  if (!form.reportValidity() || button.disabled) return;
  const question = input.value.trim();
  log.querySelector(".welcome")?.remove();
  button.disabled = true; status.textContent = "Embedding your question and retrieving evidence…";
  const userMessage = node("div", question, "user-message"); log.append(userMessage);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch("/api/knowledge/query", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({question}), signal: controller.signal});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Question could not be processed. Check its length and try again.");
    const answer = node("article", null, "answer-message");
    answer.append(node("h3", data.supported ? (data.mode === "llm_generated" ? "Generated answer with sources" : "Evidence from the corpus") : "Evidence not available"), node("p", data.answer, "answer-text"));
    data.evidence.forEach((evidence, i) => {
      const detail = node("details");
      detail.append(node("summary", `[${i + 1}] ${evidence.source.title} · ${evidence.heading}`));
      detail.append(node("blockquote", evidence.text), sourceLink(evidence.source, "Open original source ↗"), node("p", `${evidence.source.id} · ${evidence.source.archived ? "Archived" : "NIST educational source"} · cosine ${evidence.score.toFixed(3)} · imported ${evidence.source.accessed_at.slice(0, 10)}`, "muted"));
      answer.append(detail);
    });
    answer.append(node("p", `${data.mode === "llm_generated" ? "LLM-generated · " + data.model : "Extractive mode"} · ${Math.round(data.latency_ms)} ms. ${data.limitation}`, "muted"));
    if (data.fallback_reason) answer.append(node("p", "Generation unavailable; showing retrieved excerpts. Reason: " + data.fallback_reason.replaceAll("_", " "), "muted"));
    log.append(answer); status.textContent = "Response ready. Open the source details to inspect the evidence.";
  } catch (error) { status.textContent = error.name === "AbortError" ? "Request timed out. Please try again." : error.message; }
  finally { clearTimeout(timeout); button.disabled = false; }
});
loadSources();
