import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def load_template(template_name: str) -> str:
    """Load a template file from the templates directory."""
    path = TEMPLATES_DIR / f"{template_name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


def render_template(template_name: str, **kwargs) -> str:
    """Load and render a template with the given variables."""
    template = load_template(template_name)
    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.error(f"Missing template variable {e} in template '{template_name}'")
        raise
