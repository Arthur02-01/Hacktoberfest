"""Download e análise estática de repositórios Python públicos do GitHub.

O código baixado é tratado apenas como texto: nada aqui importa,
executa ou avalia os arquivos do repositório.
"""

import ast
import os
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urljoin, urlparse

import httpx


MAX_REPO_FILES = 30
MAX_FILE_SIZE = 50000
MAX_TOTAL_CHARS = 150000

MAX_ZIP_BYTES = 60 * 1024 * 1024
MAX_PY_BYTES = 1024 * 1024
MAX_REDIRECTS = 5
GITHUB_TIMEOUT = 30.0

LONG_FUNCTION_LINES = 60
LARGE_FILE_LINES = 800

MAX_CONTEXT_WARNINGS = 30
MAX_CONTEXT_SNIPPETS = 8
SNIPPET_RADIUS = 3

GITHUB_API = "https://api.github.com"
ALLOWED_REPO_HOSTS = {"github.com", "www.github.com"}
ALLOWED_DOWNLOAD_HOSTS = {"github.com", "codeload.github.com"}
BLOCKED_URL_PARTS = ("localhost", "127.0.0.1", "file://", "ftp://")

IGNORED_DIRS = {
    ".venv", "venv", "env", "__pycache__", ".git", "node_modules",
    "dist", "build", "site-packages", "migrations",
}

PRIORITY_FILES = [
    "main.py", "app.py", "server.py", "api.py", "routes.py",
    "models.py", "services.py", "utils.py", "config.py", "settings.py",
]

BACKEND_MODULES = {
    "fastapi", "flask", "django", "starlette", "aiohttp", "tornado",
    "sanic", "sqlalchemy", "celery", "uvicorn", "gunicorn",
}

SEVERITY_ORDER = {"CRÍTICO": 0, "IMPORTANTE": 1, "MELHORIA": 2}

NAME_PART = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
SECRET_NAME = re.compile(
    r"(password|passwd|pwd|secret|api_?key|access_?key|auth_?token|token|private_?key)",
    re.IGNORECASE,
)
TODO_COMMENT = re.compile(r"#.*\b(TODO|FIXME)\b", re.IGNORECASE)


class RepositoryError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class FileReport:
    path: str
    lines: list[str]
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    print_lines: list[int] = field(default_factory=list)
    truncated: bool = False


@dataclass
class RepositoryAnalysis:
    repository: str
    files_found: int = 0
    files: list[FileReport] = field(default_factory=list)
    syntax_errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    looks_like_backend: bool = False


# ---------------------------------------------------------------- URL


def parse_github_url(url: str) -> tuple[str, str]:
    url = url.strip()
    lowered = url.lower()

    if not lowered.startswith("https://github.com/") and not lowered.startswith("https://www.github.com/"):
        raise RepositoryError("URL inválida. Use o formato https://github.com/usuario/repositorio.")
    if any(part in lowered for part in BLOCKED_URL_PARTS):
        raise RepositoryError("URL inválida. Apenas repositórios do github.com são aceitos.")

    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_REPO_HOSTS
        or parsed.username
        or parsed.password
        or parsed.port
    ):
        raise RepositoryError("URL inválida. Apenas repositórios do github.com são aceitos.")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise RepositoryError("URL inválida. Informe o usuário e o repositório: https://github.com/usuario/repositorio.")

    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not NAME_PART.match(owner) or not NAME_PART.match(repo) or owner in {".", ".."} or repo in {".", ".."}:
        raise RepositoryError("URL inválida. O nome do usuário ou do repositório contém caracteres não permitidos.")

    return owner, repo


# ----------------------------------------------------------- download


def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "CodeTutor-AI"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def fetch_default_branch(client: httpx.AsyncClient, owner: str, repo: str) -> str:
    try:
        response = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=_github_headers())
    except httpx.TimeoutException as error:
        raise RepositoryError("O GitHub demorou demais para responder. Tente novamente.", 504) from error
    except httpx.RequestError as error:
        raise RepositoryError("GitHub indisponível. Verifique sua conexão com a internet.", 503) from error

    if response.status_code == 404:
        raise RepositoryError(
            "Repositório não encontrado. Confira a URL. Repositórios privados também "
            "aparecem como não encontrados: o CodeTutor analisa apenas repositórios públicos.",
            404,
        )
    if response.status_code in (403, 429):
        if response.headers.get("x-ratelimit-remaining") == "0" or response.status_code == 429:
            raise RepositoryError(
                "Limite de requisições da API do GitHub atingido. Aguarde alguns minutos ou defina GITHUB_TOKEN.",
                429,
            )
        raise RepositoryError("Acesso negado pelo GitHub. O repositório pode ser privado.", 403)
    if response.status_code >= 500:
        raise RepositoryError("GitHub indisponível no momento. Tente novamente mais tarde.", 503)
    if response.status_code != 200:
        raise RepositoryError("O GitHub retornou uma resposta inesperada.", 502)

    try:
        data = response.json()
    except ValueError as error:
        raise RepositoryError("O GitHub retornou uma resposta inválida.", 502) from error

    if data.get("private"):
        raise RepositoryError("Repositório privado. O CodeTutor analisa apenas repositórios públicos.", 403)

    branch = data.get("default_branch")
    if not isinstance(branch, str) or not branch or ".." in branch or branch.startswith("/"):
        raise RepositoryError("Não foi possível descobrir a branch padrão do repositório.", 502)
    return branch


async def download_zip(client: httpx.AsyncClient, owner: str, repo: str, branch: str, destination: Path) -> None:
    url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{quote(branch, safe='/')}.zip"

    try:
        # Redirects are followed by hand so every hop is checked against the allowlist.
        for _ in range(MAX_REDIRECTS + 1):
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS:
                raise RepositoryError("Download falhou: o GitHub redirecionou para um endereço não permitido.", 502)

            async with client.stream("GET", url, headers={"User-Agent": "CodeTutor-AI"}) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get("location", ""))
                    continue
                if response.status_code == 404:
                    raise RepositoryError("Download falhou: arquivo ZIP da branch padrão não encontrado.", 404)
                if response.status_code != 200:
                    raise RepositoryError("Download falhou. O GitHub não entregou o arquivo ZIP.", 502)

                declared = response.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > MAX_ZIP_BYTES:
                    raise RepositoryError(_too_large_message(), 413)

                received = 0
                with destination.open("wb") as output:
                    async for chunk in response.aiter_bytes():
                        received += len(chunk)
                        if received > MAX_ZIP_BYTES:
                            raise RepositoryError(_too_large_message(), 413)
                        output.write(chunk)
                return

        raise RepositoryError("Download falhou: redirecionamentos demais.", 502)
    except httpx.TimeoutException as error:
        raise RepositoryError("Tempo limite excedido ao baixar o repositório.", 504) from error
    except httpx.RequestError as error:
        raise RepositoryError("Download falhou. Verifique sua conexão com a internet.", 503) from error


def _too_large_message() -> str:
    return f"Repositório grande demais para análise (limite de {MAX_ZIP_BYTES // (1024 * 1024)} MB no ZIP)."


# ------------------------------------------------------------ extração


def _relative_repo_path(member_name: str) -> PurePosixPath | None:
    # GitHub zips wrap everything in a "<repo>-<branch>/" folder.
    parts = PurePosixPath(member_name).parts
    if len(parts) < 2:
        return None
    return PurePosixPath(*parts[1:])


def _validate_members(archive: zipfile.ZipFile, destination: Path) -> None:
    root = destination.resolve()
    for info in archive.infolist():
        name = info.filename.replace("\\", "/")
        target = (root / name).resolve()
        if name.startswith("/") or not target.is_relative_to(root):
            raise RepositoryError("O arquivo ZIP contém caminhos inseguros e foi rejeitado.", 400)


def _is_test_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    name = parts[-1]
    return name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py" or any(
        part in {"tests", "test"} for part in parts[:-1]
    )


def _priority_key(path: PurePosixPath) -> tuple:
    try:
        rank = PRIORITY_FILES.index(path.name)
    except ValueError:
        rank = len(PRIORITY_FILES)
    return _is_test_path(str(path)), rank, len(path.parts), str(path).lower()


def analyze_zip(zip_path: Path, extract_dir: Path, repository: str) -> RepositoryAnalysis:
    analysis = RepositoryAnalysis(repository=repository)

    try:
        archive = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError) as error:
        raise RepositoryError("Download falhou: o arquivo ZIP recebido está corrompido.", 502) from error

    with archive:
        _validate_members(archive, extract_dir)

        candidates = []
        for info in archive.infolist():
            if info.is_dir() or not info.filename.endswith(".py"):
                continue
            relative = _relative_repo_path(info.filename)
            if relative is None or any(part in IGNORED_DIRS for part in relative.parts[:-1]):
                continue
            if relative.name == "__init__.py" and info.file_size == 0:
                continue
            candidates.append((relative, info))

        analysis.files_found = len(candidates)
        if not candidates:
            raise RepositoryError("Nenhum arquivo Python (.py) foi encontrado neste repositório.", 422)

        candidates.sort(key=lambda item: _priority_key(item[0]))
        total_chars = 0

        for relative, info in candidates:
            if len(analysis.files) >= MAX_REPO_FILES:
                analysis.notes.append(f"Limite de {MAX_REPO_FILES} arquivos atingido; os demais não foram analisados.")
                break
            if info.file_size > MAX_PY_BYTES:
                analysis.warnings.append(_warning(str(relative), None, "ArquivoMuitoGrande", "MELHORIA",
                                                  "Arquivo grande demais para ser lido; foi ignorado na análise."))
                continue

            extracted = Path(archive.extract(info, extract_dir))
            text = extracted.read_bytes().decode("utf-8", errors="replace")

            if relative.name == "__init__.py" and not text.strip():
                analysis.files_found -= 1
                continue

            truncated = len(text) > MAX_FILE_SIZE
            if truncated:
                text = text[:MAX_FILE_SIZE]
            if total_chars + len(text) > MAX_TOTAL_CHARS:
                analysis.notes.append(f"Limite total de {MAX_TOTAL_CHARS} caracteres atingido; os demais arquivos não foram analisados.")
                break
            total_chars += len(text)

            report = FileReport(path=str(relative), lines=text.splitlines(), truncated=truncated)
            _analyze_file(report, text, analysis)
            analysis.files.append(report)

    all_imports = {module.split(".")[0] for report in analysis.files for module in report.imports}
    analysis.looks_like_backend = bool(all_imports & BACKEND_MODULES)
    if analysis.looks_like_backend:
        for report in analysis.files:
            if report.print_lines:
                analysis.warnings.append(_warning(
                    report.path, report.print_lines[0], "PrintEmBackend", "MELHORIA",
                    f"{len(report.print_lines)} chamada(s) a print() em um projeto que parece backend; prefira o módulo logging.",
                ))

    analysis.warnings.sort(key=lambda item: (SEVERITY_ORDER[item["severity"]], item["file"], item["line"] or 0))
    return analysis


# ---------------------------------------------------- análise estática


def _warning(file: str, line: int | None, kind: str, severity: str, message: str) -> dict:
    return {"file": file, "line": line, "type": kind, "severity": severity, "message": message}


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts = [func.attr]
        value = func.value
        while isinstance(value, ast.Attribute):
            parts.append(value.attr)
            value = value.value
        if isinstance(value, ast.Name):
            parts.append(value.id)
        return ".".join(reversed(parts))
    return ""


def _mask(value: str) -> str:
    return f'"{value[:2]}***"' if len(value) > 2 else '"***"'


def _check_secret(name: str, value: ast.AST, path: str, line: int, analysis: RepositoryAnalysis) -> None:
    if (
        SECRET_NAME.search(name)
        and isinstance(value, ast.Constant)
        and isinstance(value.value, str)
        and len(value.value.strip()) >= 4
    ):
        if _is_test_path(path):
            severity, hint = "MELHORIA", "Em testes isso costuma ser aceitável, desde que não seja uma credencial real."
        else:
            severity, hint = "CRÍTICO", "Use variáveis de ambiente."
        analysis.warnings.append(_warning(
            path, line, "SegredoHardcoded", severity,
            f"'{name}' recebe um valor fixo no código ({_mask(value.value)}). {hint}",
        ))


def _analyze_file(report: FileReport, text: str, analysis: RepositoryAnalysis) -> None:
    path = report.path

    for number, line in enumerate(report.lines, start=1):
        match = TODO_COMMENT.search(line)
        if match:
            analysis.warnings.append(_warning(path, number, match.group(1).upper(), "MELHORIA",
                                              f"Comentário {match.group(1).upper()} pendente: {line.strip()[:120]}"))

    if len(report.lines) > LARGE_FILE_LINES or report.truncated:
        analysis.warnings.append(_warning(path, None, "ArquivoGrande", "MELHORIA",
                                          f"Arquivo com {len(report.lines)} linhas"
                                          f"{' (truncado na análise)' if report.truncated else ''}; considere dividi-lo em módulos."))

    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError as error:
        analysis.syntax_errors.append({
            "file": path, "line": error.lineno, "type": type(error).__name__, "message": error.msg,
        })
        return
    except (ValueError, RecursionError, MemoryError):
        analysis.syntax_errors.append({
            "file": path, "line": None, "type": "ParseError", "message": "O arquivo não pôde ser analisado pelo parser.",
        })
        return

    imported: dict[str, int] = {}
    seen_imports: set[tuple] = set()
    method_nodes: set[int] = set()
    used_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    used_names |= {node.value.id for node in ast.walk(tree)
                   if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)}

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            source = ""
            if isinstance(node, ast.ImportFrom):
                source = "." * node.level + (node.module or "")
            for alias in node.names:
                full = f"{source}.{alias.name}" if source else alias.name
                report.imports.append(source or alias.name)
                if alias.name == "*":
                    analysis.warnings.append(_warning(path, node.lineno, "ImportCuringa", "MELHORIA",
                                                      f"'from {source} import *' dificulta saber de onde vêm os nomes."))
                    continue
                key = (full, alias.asname)
                if key in seen_imports:
                    analysis.warnings.append(_warning(path, node.lineno, "ImportDuplicado", "MELHORIA",
                                                      f"Import duplicado: {full}."))
                seen_imports.add(key)
                local = alias.asname or alias.name.split(".")[0]
                imported.setdefault(local, node.lineno)

        elif isinstance(node, ast.ClassDef):
            report.classes.append(node.name)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    report.methods.append(f"{node.name}.{item.name}")
                    method_nodes.add(id(item))

        elif isinstance(node, ast.ExceptHandler):
            if node.type is None:
                analysis.warnings.append(_warning(path, node.lineno, "ExceptSemTipo", "IMPORTANTE",
                                                  "'except:' sem tipo captura qualquer erro, inclusive KeyboardInterrupt."))
            elif isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
                analysis.warnings.append(_warning(path, node.lineno, "ExceptGenerico", "IMPORTANTE",
                                                  f"'except {node.type.id}:' é genérico demais e pode esconder erros."))

        elif isinstance(node, ast.Call):
            name = _call_name(node)
            if name in {"eval", "exec"}:
                analysis.warnings.append(_warning(path, node.lineno, f"Uso de {name}", "CRÍTICO",
                                                  f"{name}() pode executar código arbitrário."))
            elif name in {"pickle.loads", "pickle.load"}:
                analysis.warnings.append(_warning(path, node.lineno, "PickleInseguro", "CRÍTICO",
                                                  f"{name}() com dados não confiáveis pode executar código."))
            elif name == "os.system":
                analysis.warnings.append(_warning(path, node.lineno, "OsSystem", "CRÍTICO",
                                                  "os.system() executa comandos do shell; risco de injeção de comandos."))
            elif name.startswith("subprocess."):
                for keyword in node.keywords:
                    if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        analysis.warnings.append(_warning(path, node.lineno, "SubprocessShell", "CRÍTICO",
                                                          f"{name}(..., shell=True) permite injeção de comandos."))
            elif name == "print":
                report.print_lines.append(node.lineno)
            for keyword in node.keywords:
                if keyword.arg:
                    _check_secret(keyword.arg, keyword.value, path, node.lineno, analysis)

        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                name = target.id if isinstance(target, ast.Name) else target.attr if isinstance(target, ast.Attribute) else ""
                if name and node.value is not None:
                    _check_secret(name, node.value, path, node.lineno, analysis)

        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    _check_secret(key.value, value, path, node.lineno, analysis)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if id(node) not in method_nodes:
                report.functions.append(node.name)
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > LONG_FUNCTION_LINES:
                analysis.warnings.append(_warning(path, node.lineno, "FuncaoLonga", "MELHORIA",
                                                  f"A função '{node.name}' tem {length} linhas; considere dividi-la."))

    if not path.endswith("__init__.py"):
        exported = _exported_names(tree)
        for local, line in imported.items():
            if local not in used_names and local not in exported:
                analysis.warnings.append(_warning(path, line, "ImportNaoUsado", "MELHORIA",
                                                  f"'{local}' é importado, mas parece não ser utilizado."))

    report.imports = sorted(set(report.imports))


def _exported_names(tree: ast.Module) -> set[str]:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            if isinstance(node.value, (ast.List, ast.Tuple)):
                return {item.value for item in node.value.elts if isinstance(item, ast.Constant)}
    return set()


# ------------------------------------------------- contexto para a IA


def _snippet(report: FileReport, line: int) -> str:
    start = max(1, line - SNIPPET_RADIUS)
    end = min(len(report.lines), line + SNIPPET_RADIUS)
    width = len(str(end))
    return "\n".join(f"{number:>{width}} | {report.lines[number - 1][:160]}" for number in range(start, end + 1))


def build_repository_context(analysis: RepositoryAnalysis) -> str:
    by_path = {report.path: report for report in analysis.files}
    sections = [
        f"REPOSITÓRIO: {analysis.repository}",
        f"Arquivos Python encontrados: {analysis.files_found}. Analisados: {len(analysis.files)}.",
        f"Parece backend/web: {'sim' if analysis.looks_like_backend else 'não'}.",
    ]
    sections += analysis.notes

    structure = []
    for report in analysis.files[:20]:
        details = []
        if report.classes:
            details.append("classes: " + ", ".join(report.classes[:6]))
        if report.functions:
            details.append("funções: " + ", ".join(report.functions[:8]))
        if report.methods:
            details.append(f"{len(report.methods)} método(s)")
        structure.append(f"- {report.path} ({len(report.lines)} linhas)" + (f" — {'; '.join(details)}" if details else ""))
    if len(analysis.files) > 20:
        structure.append(f"- ... e mais {len(analysis.files) - 20} arquivo(s)")
    sections.append("ESTRUTURA RESUMIDA:\n" + "\n".join(structure))

    modules = sorted({module.split(".")[0] for report in analysis.files for module in report.imports if module and not module.startswith(".")})
    if modules:
        sections.append("BIBLIOTECAS IMPORTADAS: " + ", ".join(modules[:40]))

    if analysis.syntax_errors:
        sections.append("ERROS DE SINTAXE (CRÍTICO):\n" + "\n".join(
            f"- {item['file']}, linha {item['line'] or '?'}: {item['type']}: {item['message']}"
            for item in analysis.syntax_errors[:10]
        ))
    else:
        sections.append("ERROS DE SINTAXE: nenhum encontrado.")

    if analysis.warnings:
        listed = analysis.warnings[:MAX_CONTEXT_WARNINGS]
        lines = [f"- [{item['severity']}] {item['file']}, linha {item['line'] or '-'}: {item['message']}" for item in listed]
        if len(analysis.warnings) > len(listed):
            lines.append(f"- ... e mais {len(analysis.warnings) - len(listed)} alerta(s) de menor prioridade")
        sections.append("ALERTAS DA ANÁLISE ESTÁTICA:\n" + "\n".join(lines))
    else:
        sections.append("ALERTAS DA ANÁLISE ESTÁTICA: nenhum alerta encontrado.")

    snippets = []
    for item in analysis.syntax_errors + analysis.warnings:
        if len(snippets) >= MAX_CONTEXT_SNIPPETS:
            break
        report = by_path.get(item["file"])
        if report and item["line"] and item["line"] <= len(report.lines):
            snippets.append(f"{item['file']} (linha {item['line']}):\n```python\n{_snippet(report, item['line'])}\n```")
    if snippets:
        sections.append("TRECHOS RELEVANTES:\n\n" + "\n\n".join(snippets))

    return "\n\n".join(sections)
