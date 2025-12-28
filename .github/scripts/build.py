# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "jinja2>=3.1.0",
#     "fire>=0.7.0",
#     "loguru>=0.7.0",
# ]
# ///
"""
Build script for marimo notebooks.

This script exports marimo notebooks to HTML/WebAssembly format and generates
an index.html file that lists all the notebooks.

Usage:
    uv run .github/scripts/build.py [--output-dir OUTPUT_DIR]
    uv run .github/scripts/build.py --output-dir _site
"""

import subprocess
from pathlib import Path

import fire
import jinja2
from loguru import logger


def _export_html_wasm(
    notebook_path: Path,
    output_dir: Path,
    as_app: bool = False,
) -> bool:
    """Export a single marimo notebook to HTML/WebAssembly format.

    Args:
        notebook_path: Path to the marimo notebook (.py file) to export
        output_dir: Directory where the exported HTML file will be saved
        as_app: Whether to export as an app (run mode) or notebook (edit mode)

    Returns:
        True if export succeeded, False otherwise
    """
    # Base command for marimo export
    cmd: list[str] = ["uvx", "marimo", "export", "html-wasm", "--sandbox"]

    # Configure export mode
    if as_app:
        logger.info(f"Exporting {notebook_path} as app (run mode)")
        cmd.extend(["--mode", "run", "--no-show-code"])
    else:
        logger.info(f"Exporting {notebook_path} as notebook (edit mode)")
        cmd.extend(["--mode", "edit"])

    try:
        # Create full output path and ensure directory exists
        output_file: Path = output_dir / notebook_path.with_suffix(".html")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Add notebook path and output file to command
        cmd.extend([str(notebook_path), "-o", str(output_file)])

        # Run marimo export command
        logger.debug(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Successfully exported {notebook_path}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Error exporting {notebook_path}:")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error exporting {notebook_path}: {e}")
        return False


def _generate_index(
    output_dir: Path,
    notebooks_data: list[dict] | None = None,
    apps_data: list[dict] | None = None,
) -> None:
    """Generate an index.html file that lists all the notebooks.

    Args:
        output_dir: Directory where the index.html file will be saved
        notebooks_data: List of dictionaries with data for notebooks
        apps_data: List of dictionaries with data for apps
    """
    logger.info("Generating index.html")

    index_path: Path = output_dir / "index.html"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Simple HTML template (inline to avoid external dependency)
    html_template = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GitHub Audit Log Analyzer - Notebooks</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="font-sans text-gray-800 bg-gray-50 min-h-screen">
  <div class="max-w-4xl mx-auto p-6">
    <!-- Header -->
    <header class="bg-white rounded-lg shadow-sm p-8 text-center mb-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-2">GitHub Audit Log Analyzer</h1>
      <p class="text-gray-600">Interactive analysis notebooks powered by marimo</p>
    </header>

    <main>
      {% if notebooks %}
      <section class="mb-8">
        <h2 class="text-xl font-bold text-gray-800 mb-4">📓 Notebooks</h2>
        <p class="text-gray-600 mb-4">Interactive notebooks - you can modify and experiment with the code</p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          {% for notebook in notebooks %}
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
            <div class="bg-gray-100 px-4 py-3 border-b border-gray-200">
              <h3 class="font-semibold text-gray-800">{{ notebook.display_name }}</h3>
            </div>
            <div class="p-4">
              <a href="{{ notebook.html_path }}"
                 class="inline-block bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded transition-colors">
                Open Notebook
              </a>
            </div>
          </div>
          {% endfor %}
        </div>
      </section>
      {% endif %}

      {% if apps %}
      <section class="mb-8">
        <h2 class="text-xl font-bold text-gray-800 mb-4">🚀 Apps</h2>
        <p class="text-gray-600 mb-4">Interactive applications - code is hidden for a clean interface</p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          {% for app in apps %}
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
            <div class="bg-amber-100 px-4 py-3 border-b border-amber-200">
              <h3 class="font-semibold text-gray-800">{{ app.display_name }}</h3>
            </div>
            <div class="p-4">
              <a href="{{ app.html_path }}"
                 class="inline-block bg-amber-500 hover:bg-amber-600 text-white py-2 px-4 rounded transition-colors">
                Open App
              </a>
            </div>
          </div>
          {% endfor %}
        </div>
      </section>
      {% endif %}
    </main>

    <footer class="mt-12 pt-6 border-t border-gray-200 text-center text-sm text-gray-500">
      <p>Built with <a href="https://marimo.io" target="_blank" class="text-blue-500 hover:underline">marimo</a></p>
      <p class="mt-1">GitHub Organization Audit Log Analyzer</p>
    </footer>
  </div>
</body>
</html>"""

    try:
        template = jinja2.Template(html_template)
        rendered_html = template.render(
            notebooks=notebooks_data or [],
            apps=apps_data or [],
        )

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)

        # Create .nojekyll file to prevent GitHub Pages from processing with Jekyll
        nojekyll_path = output_dir / ".nojekyll"
        nojekyll_path.touch()

        logger.info(f"Successfully generated index.html at {index_path}")

    except Exception as e:
        logger.error(f"Error generating index.html: {e}")
        raise


def _export_folder(
    folder: Path,
    output_dir: Path,
    as_app: bool = False,
) -> list[dict]:
    """Export all marimo notebooks in a folder to HTML/WebAssembly format.

    Args:
        folder: Path to the folder containing marimo notebooks
        output_dir: Directory where the exported HTML files will be saved
        as_app: Whether to export as apps (run mode) or notebooks (edit mode)

    Returns:
        List of dictionaries with "display_name" and "html_path" for each notebook
    """
    if not folder.exists():
        logger.warning(f"Directory not found: {folder}")
        return []

    # Find all Python files in the folder (non-recursive to avoid __pycache__)
    notebooks = list(folder.glob("*.py"))
    logger.info(f"Found {len(notebooks)} Python files in {folder}")

    if not notebooks:
        logger.warning(f"No notebooks found in {folder}!")
        return []

    # Export each notebook and collect metadata
    notebook_data = []
    for nb in sorted(notebooks):
        if _export_html_wasm(nb, output_dir, as_app=as_app):
            notebook_data.append(
                {
                    "display_name": nb.stem.replace("_", " ").title(),
                    "html_path": str(nb.with_suffix(".html")),
                }
            )

    logger.info(
        f"Successfully exported {len(notebook_data)} out of {len(notebooks)} files from {folder}"
    )
    return notebook_data


def main(
    output_dir: str | Path = "_site",
) -> None:
    """Main function to export marimo notebooks.

    Args:
        output_dir: Directory where the exported files will be saved (default: _site)
    """
    logger.info("Starting marimo build process")

    output_dir_path: Path = Path(output_dir)
    logger.info(f"Output directory: {output_dir_path}")

    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Export notebooks from the notebooks/ directory
    notebooks_data = _export_folder(Path("notebooks"), output_dir_path, as_app=False)

    # Export apps from the apps/ directory (if exists)
    apps_data = _export_folder(Path("apps"), output_dir_path, as_app=True)

    if not notebooks_data and not apps_data:
        logger.warning("No notebooks or apps found!")
        return

    # Generate the index.html file
    _generate_index(
        output_dir=output_dir_path,
        notebooks_data=notebooks_data,
        apps_data=apps_data,
    )

    logger.info(f"Build completed successfully. Output directory: {output_dir_path}")


if __name__ == "__main__":
    fire.Fire(main)
