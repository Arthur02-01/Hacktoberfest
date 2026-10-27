const statusElement = document.getElementById("aiStatus");
const codeElement = document.getElementById("code");
const languageElement = document.getElementById("language");
const responseElement = document.getElementById("response");
const analyzeButton = document.getElementById("analyzeButton");
const exampleButton = document.getElementById("exampleButton");
const hintControls = document.getElementById("hintControls");
const nextHintButton = document.getElementById("nextHintButton");
const solutionButton = document.getElementById("solutionButton");
const modeButtons = document.querySelectorAll(".mode-button");
const descriptionElement = document.getElementById("modeDescription");
const hintLabels = ["Pista 1 — leve", "Pista 2 — intermediária", "Pista 3 — quase solução"];
let selectedMode = "hint";
let hintLevel = 0;
let previousHint = null;
let busy = false;
let exampleIndex = 0;

const examples = [
    {language: "python", code: `def calcular_media(notas):
    soma = 0

    for nota in notas:
        soma += nota

    return soma / 0

print(calcular_media([7, 8, 9]))`},
    {language: "javascript", code: `function soma(a, b) {
    return a + b;
}

console.log(soma(10));`},
    {language: "python", code: `numeros = [1, 2, 3, 4, 5]

for i in range(len(numeros) + 1):
    print(numeros[i])`}
];

function setMode(mode) {
    selectedMode = mode;
    modeButtons.forEach(button => {
        button.classList.toggle("active", button.dataset.mode === mode);
        button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
    });
}
function resetHintState() {
    hintLevel = 0;
    previousHint = null;
    updateHintControls();
    descriptionElement.textContent = selectedMode === "hint"
        ? "Modo Pistas: aprenda em três etapas." : "Professor virtual executado localmente.";
}
function updateHintControls() {
    hintControls.classList.toggle("hidden", busy || selectedMode !== "hint" || hintLevel === 0);
    nextHintButton.classList.toggle("hidden", hintLevel >= 3);
    solutionButton.classList.toggle("hidden", hintLevel < 3);
    nextHintButton.textContent = `Quero outra pista (${Math.min(hintLevel + 1, 3)}/3)`;
}
modeButtons.forEach(button => button.addEventListener("click", () => {
    if (busy) return;
    setMode(button.dataset.mode);
    resetHintState();
}));
codeElement.addEventListener("input", resetHintState);
languageElement.addEventListener("change", resetHintState);
exampleButton.addEventListener("click", () => {
    if (busy) return;
    const example = examples[exampleIndex];
    languageElement.value = example.language;
    codeElement.value = example.code;
    exampleIndex = (exampleIndex + 1) % examples.length;
    resetHintState();
});
analyzeButton.addEventListener("click", () => {
    if (busy) return;
    resetHintState();
    analyzeCode(1);
});
nextHintButton.addEventListener("click", () => {
    if (!busy && hintLevel > 0 && hintLevel < 3) analyzeCode(hintLevel + 1);
});
solutionButton.addEventListener("click", () => {
    if (busy || hintLevel !== 3) return;
    setMode("debug");
    resetHintState();
    analyzeCode(1);
});

async function checkHealth() {
    try {
        const response = await fetch("/api/health");
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (!data.ollama) throw new Error();
        statusElement.className = data.model_available ? "status online" : "status offline";
        statusElement.textContent = data.model_available ? "● IA local conectada" : "● Modelo não encontrado";
        statusElement.title = data.model_available ? "qwen2.5-coder:1.5b" : "Execute: ollama pull qwen2.5-coder:1.5b";
    } catch {
        statusElement.className = "status offline";
        statusElement.textContent = "● Ollama desconectado";
        statusElement.title = "Abra o Ollama ou execute ollama serve.";
    }
}
function setBusy(value) {
    busy = value;
    [analyzeButton, exampleButton, nextHintButton, solutionButton, languageElement, ...modeButtons]
        .forEach(element => { element.disabled = value; });
    codeElement.readOnly = value;
    responseElement.setAttribute("aria-busy", String(value));
    analyzeButton.textContent = value ? "Analisando..." : "Analisar com IA";
    updateHintControls();
}
async function analyzeCode(level = 1) {
    if (busy) return;
    const code = codeElement.value;
    if (!code.trim()) { showError("Cole algum código antes de analisar."); return; }
    if ([...code].length > 15000) { showError("O código ultrapassa o limite de 15.000 caracteres."); return; }
    const mode = selectedMode;
    setBusy(true);
    responseElement.className = "response-content";
    responseElement.innerHTML = '<div class="loading"><div class="spinner" aria-hidden="true"></div><p>Analisando código...</p></div>';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 100000);
    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            signal: controller.signal,
            body: JSON.stringify({language: languageElement.value, mode, code,
                hint_level: level, previous_hint: mode === "hint" ? previousHint : null})
        });
        const data = await response.json();
        if (!response.ok) {
            const message = typeof data.detail === "string" ? data.detail : "Dados inválidos. Confira o código, o modo e o nível da pista.";
            throw new Error(message);
        }
        if (typeof data.response !== "string" || !data.response.trim()) throw new Error("O modelo retornou uma resposta vazia.");
        responseElement.innerHTML = markdownToHtml(data.response);
        addCopyButtons();
        if (mode === "hint") {
            hintLevel = level;
            previousHint = data.response;
            descriptionElement.textContent = `Modo Pistas · ${hintLabels[level - 1]}`;
        } else {
            descriptionElement.textContent = modeButtons.length
                ? document.querySelector(`[data-mode="${mode}"] strong`).textContent.trim() : mode;
        }
    } catch (error) {
        showError(error.name === "AbortError" ? "A análise demorou demais. Tente novamente."
            : error instanceof TypeError ? "Não foi possível acessar o servidor. Verifique a conexão." : error.message);
    } finally {
        clearTimeout(timeout);
        setBusy(false);
    }
}
function showError(message) {
    responseElement.className = "response-content";
    responseElement.innerHTML = `<div class="error-message"><h3>Não foi possível analisar</h3><p>${escapeHtml(message)}</p></div>`;
}
function escapeHtml(value) {
    return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}
function inlineMarkdown(text) {
    // Inline code is isolated before applying emphasis to prose.
    return text.split(/(`[^`]+`)/g).map(part => part.startsWith("`") && part.endsWith("`")
        ? `<code>${escapeHtml(part.slice(1, -1))}</code>`
        : escapeHtml(part).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")).join("");
}
function markdownToHtml(markdown) {
    const lines = String(markdown).replace(/\r\n?/g, "\n").split("\n");
    const html = [];
    let paragraph = [];
    let list = null;
    function flush() {
        if (paragraph.length) { html.push(`<p>${paragraph.map(inlineMarkdown).join("<br>")}</p>`); paragraph = []; }
        if (list) { html.push(`</${list}>`); list = null; }
    }
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const fence = line.match(/^\s*(`{3,}|~{3,})(.*)$/);
        if (fence) {
            flush();
            const code = [];
            const closing = new RegExp(`^\\s*${fence[1][0]}{${fence[1].length},}\\s*$`);
            while (++i < lines.length && !closing.test(lines[i])) code.push(lines[i]);
            html.push(`<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`);
            continue;
        }
        const heading = line.match(/^(#{1,6})\s+(.+)$/);
        const item = line.match(/^\s*(?:([-*+])|\d+[.)])\s+(.+)$/);
        if (!line.trim()) { flush(); }
        else if (heading) {
            flush();
            const level = heading[1].length;
            html.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
        } else if (item) {
            const type = item[1] ? "ul" : "ol";
            if (paragraph.length || (list && list !== type)) flush();
            if (!list) { html.push(`<${type}>`); list = type; }
            html.push(`<li>${inlineMarkdown(item[2])}</li>`);
        } else {
            if (list) flush();
            paragraph.push(line);
        }
    }
    flush();
    return html.join("\n");
}
function addCopyButtons(container = responseElement) {
    container.querySelectorAll("pre").forEach(block => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "copy-code-button";
        button.textContent = "Copiar";
        button.addEventListener("click", async () => {
            try {
                await navigator.clipboard.writeText(block.querySelector("code").textContent);
                button.textContent = "Copiado";
            } catch {
                button.textContent = "Selecione e copie";
            }
            setTimeout(() => { button.textContent = "Copiar"; }, 2000);
        });
        block.appendChild(button);
    });
}
const tabButtons = document.querySelectorAll(".tab-button");
const tabPanels = document.querySelectorAll(".tab-panel");
const repoForm = document.getElementById("repoForm");
const repoUrlElement = document.getElementById("repoUrl");
const repoButton = document.getElementById("repoButton");
const repoSummary = document.getElementById("repoSummary");
const repoFindings = document.getElementById("repoFindings");
const repoReport = document.getElementById("repoReport");
const repoSteps = ["Baixando repositório...", "Analisando arquivos Python...",
    "Preparando diagnóstico...", "Consultando CodeTutor AI..."];
let repoBusy = false;

tabButtons.forEach(button => button.addEventListener("click", () => {
    tabButtons.forEach(tab => {
        const active = tab === button;
        tab.classList.toggle("active", active);
        tab.setAttribute("aria-selected", String(active));
    });
    tabPanels.forEach(panel => panel.classList.toggle("hidden", panel.id !== button.dataset.tab));
}));

function validateRepoUrl(value) {
    let url;
    try { url = new URL(value.trim()); } catch { return false; }
    const parts = url.pathname.split("/").filter(Boolean);
    return url.protocol === "https:" && ["github.com", "www.github.com"].includes(url.hostname)
        && !url.port && !url.username && parts.length >= 2;
}
function showRepoError(message) {
    repoSummary.classList.add("hidden");
    repoFindings.classList.add("hidden");
    repoReport.className = "response-content";
    repoReport.innerHTML = `<div class="error-message"><h3>Não foi possível analisar o repositório</h3><p>${escapeHtml(message)}</p></div>`;
}
function renderRepoSummary(data) {
    const stats = [
        ["Repositório", data.repository], ["Arquivos Python encontrados", data.files_found],
        ["Arquivos analisados", data.files_analyzed], ["Erros de sintaxe", data.syntax_errors],
        ["Alertas", data.warnings]
    ];
    repoSummary.innerHTML = stats.map(([label, value], index) =>
        `<div class="stat${index === 0 ? " stat-wide" : ""}${label === "Erros de sintaxe" && value ? " stat-danger" : ""}">
            <span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
    repoSummary.classList.remove("hidden");

    const items = [
        ...data.syntax_error_details.map(item => ({...item, severity: "CRÍTICO"})),
        ...data.warning_details
    ];
    const notes = data.notes.map(note => `<p class="repo-note">${escapeHtml(note)}</p>`).join("");
    if (!items.length) {
        repoFindings.innerHTML = `<h3>Análise estática</h3>${notes}<p class="repo-note">Nenhum alerta encontrado.</p>`;
    } else {
        const shown = items.slice(0, 40);
        repoFindings.innerHTML = `<h3>Análise estática</h3>${notes}<ul>${shown.map(item => {
            const severity = item.severity === "CRÍTICO" ? "critical" : item.severity === "IMPORTANTE" ? "important" : "minor";
            const location = `${item.file}${item.line ? `:${item.line}` : ""}`;
            return `<li><span class="badge ${severity}">${escapeHtml(item.severity)}</span>
                <code>${escapeHtml(location)}</code> ${escapeHtml(item.message)}</li>`;
        }).join("")}</ul>${items.length > shown.length
            ? `<p class="repo-note">... e mais ${items.length - shown.length} alerta(s).</p>` : ""}`;
    }
    repoFindings.classList.remove("hidden");
}
function setRepoBusy(value) {
    repoBusy = value;
    repoButton.disabled = value;
    repoUrlElement.readOnly = value;
    repoReport.setAttribute("aria-busy", String(value));
    repoButton.textContent = value ? "Analisando..." : "Analisar repositório";
}

repoForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (repoBusy) return;
    const repositoryUrl = repoUrlElement.value.trim();
    if (!validateRepoUrl(repositoryUrl)) {
        showRepoError("URL inválida. Use o formato https://github.com/usuario/repositorio.");
        return;
    }
    setRepoBusy(true);
    repoSummary.classList.add("hidden");
    repoFindings.classList.add("hidden");
    repoReport.className = "response-content";
    repoReport.innerHTML = '<div class="loading"><div class="spinner" aria-hidden="true"></div><p id="repoStep"></p></div>';
    let step = 0;
    const stepElement = document.getElementById("repoStep");
    stepElement.textContent = repoSteps[0];
    const stepTimer = setInterval(() => {
        step = Math.min(step + 1, repoSteps.length - 1);
        stepElement.textContent = repoSteps[step];
    }, 3500);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 240000);
    try {
        const response = await fetch("/api/analyze-repository", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            signal: controller.signal,
            body: JSON.stringify({repository_url: repositoryUrl})
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(typeof data.detail === "string" ? data.detail : "URL inválida ou dados incorretos.");
        }
        if (typeof data.report !== "string" || !data.report.trim()) throw new Error("O modelo retornou um relatório vazio.");
        renderRepoSummary(data);
        repoReport.innerHTML = markdownToHtml(data.report);
        addCopyButtons(repoReport);
    } catch (error) {
        showRepoError(error.name === "AbortError" ? "Tempo limite excedido. Tente um repositório menor ou tente novamente."
            : error instanceof TypeError ? "Não foi possível acessar o servidor. Verifique a conexão." : error.message);
    } finally {
        clearInterval(stepTimer);
        clearTimeout(timeout);
        setRepoBusy(false);
    }
});

setMode("hint");
resetHintState();
checkHealth();
setInterval(checkHealth, 15000);
