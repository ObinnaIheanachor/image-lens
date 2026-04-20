from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(enabled_extensions=("html",)),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_markdown(context: dict) -> str:
    template = _env.get_template("report.md.j2")
    return template.render(**context)


def render_html(context: dict) -> str:
    template = _env.get_template("report.html.j2")
    return template.render(**context)


def render_pdf(context: dict) -> bytes:
    html = render_html(context)
    try:
        from weasyprint import HTML
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"pdf_renderer_unavailable: {exc}") from exc

    return HTML(string=html, base_url=str(_TEMPLATE_DIR)).write_pdf()
