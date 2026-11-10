#!/usr/bin/env python3
"""Pull a Lark document as Markdown, download images to a per-doc assets folder, and rewrite local paths."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a shell command safely and return output."""
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def slugify_title(title: str) -> str:
    """Convert title to safe, space-free Unicode slug using hyphens.

    Preserves Chinese/CJK characters and alphanumerics, replaces spaces and symbols with single hyphen.
    """
    # Strip whitespace
    s = title.strip()
    # Remove leading markdown heading hashes like '# ' or '## '
    s = re.sub(r"^#+\s*", "", s)
    # Replace whitespace and unsafe filename/URL characters with hyphen
    # Characters replaced: space, tab, newline, / \ : * ? " < > | ( ) [ ] { } （ ） 【 】 、 ， 。 , . / ~ ` ! @ # $ % ^ & + = ; '
    s = re.sub(r'[\s/\\:*?"<>|()\[\]{}（）【】、，。,\'"`~!@#$%^&+;=]+', "-", s)
    # Collapse multiple hyphens
    s = re.sub(r"-+", "-", s).strip("-")
    # Lowercase ASCII characters only (leaves Unicode CJK intact)
    s = s.lower()
    return s or "untitled"


def extract_title_from_markdown(content: str) -> str:
    """Extract document title from the first heading or first non-empty line of markdown."""
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        # If it's a markdown heading
        if line.startswith("#"):
            return re.sub(r"^#+\s*", "", line).strip()
        # Fallback to the first non-empty line
        return line[:50].strip()
    return "untitled"


def fetch_lark_doc_markdown(doc_target: str, identity: str = "user") -> str:
    """Fetch raw markdown from Lark document using lark-cli."""
    cmd = [
        "lark-cli",
        "docs",
        "+fetch",
        "--doc",
        doc_target,
        "--doc-format",
        "markdown",
        "--as",
        identity,
        "--json",
    ]
    proc = run_command(cmd)
    if proc.returncode != 0:
        sys.stderr.write(f"Failed to fetch lark doc: {proc.stderr}\n")
        sys.exit(proc.returncode)

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as err:
        sys.stderr.write(f"Failed to parse lark-cli output JSON: {err}\n")
        sys.exit(1)

    if not data.get("ok"):
        sys.stderr.write(f"lark-cli error: {data}\n")
        sys.exit(1)

    # Document content is under data.document.content
    content = data.get("data", {}).get("document", {}).get("content", "")
    return content


def download_media(doc_target: str, token: str, output_path: Path, identity: str = "user") -> bool:
    """Download media token from Lark document."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "lark-cli",
        "docs",
        "+media-download",
        "--doc",
        doc_target,
        "--token",
        token,
        "--output",
        str(output_path),
        "--overwrite",
        "--as",
        identity,
    ]
    proc = run_command(cmd)
    if proc.returncode != 0:
        sys.stderr.write(f"Warning: Failed to download media token {token}: {proc.stderr}\n")
        return False
    return True


def process_markdown_media(
    content: str, doc_target: str, assets_dir: Path, identity: str = "user"
) -> str:
    """Extract media tokens and Lark images, download them to assets_dir, and rewrite URLs."""
    token_pattern = re.compile(r"!\[(.*?)\]\(([a-zA-Z0-9_\-]+)\)")
    img_tag_pattern = re.compile(r'<img\s+[^>]*token=["\']([a-zA-Z0-9_\-]+)["\'][^>]*\/?>')

    # Find tokens from markdown image syntax
    def replace_md_token(match: re.Match[str]) -> str:
        alt = match.group(1)
        token = match.group(2)
        if token.startswith("http://") or token.startswith("https://") or "/" in token or "." in token:
            return match.group(0)

        ext = ".png"
        target_file = assets_dir / f"{token}{ext}"
        if download_media(doc_target, token, target_file, identity):
            return f"![{alt}]({assets_dir.name}/{token}{ext})"
        return match.group(0)

    content = token_pattern.sub(replace_md_token, content)

    # Find tokens from img tags if any residual DocxXML
    def replace_img_tag(match: re.Match[str]) -> str:
        token = match.group(1)
        ext = ".png"
        target_file = assets_dir / f"{token}{ext}"
        if download_media(doc_target, token, target_file, identity):
            return f"![image]({assets_dir.name}/{token}{ext})"
        return match.group(0)

    content = img_tag_pattern.sub(replace_img_tag, content)
    return content


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pull Lark doc to local Markdown with dedicated per-doc assets folder"
    )
    parser.add_argument("doc", help="Lark document URL or token")
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help="Local output markdown path (default: auto-detected from title as <slug>.md)",
    )
    parser.add_argument(
        "--assets-dir",
        default="",
        help="Assets directory name or path (default: <filename>.assets)",
    )
    parser.add_argument(
        "--as",
        dest="identity",
        default="user",
        choices=["user", "bot"],
        help="Identity type (default: user)",
    )

    args = parser.parse_args()

    print(f"Fetching document: {args.doc} ...")
    content = fetch_lark_doc_markdown(args.doc, identity=args.identity)

    # Determine output markdown path
    if args.output:
        output_path = Path(args.output).resolve()
        # If output filename has spaces, slugify stem
        if " " in output_path.name:
            clean_stem = slugify_title(output_path.stem)
            output_path = output_path.with_name(f"{clean_stem}{output_path.suffix}")
    else:
        title = extract_title_from_markdown(content)
        slug = slugify_title(title)
        output_path = Path(f"{slug}.md").resolve()

    # Determine dedicated assets directory: <doc_name>.assets/
    if args.assets_dir:
        assets_dir = Path(args.assets_dir)
        if not assets_dir.is_absolute():
            assets_dir = output_path.parent / assets_dir
    else:
        assets_dir = output_path.parent / f"{output_path.stem}.assets"

    print("Processing multi-media assets into dedicated folder...")
    processed_content = process_markdown_media(
        content, args.doc, assets_dir=assets_dir, identity=args.identity
    )

    # Write output markdown atomically via tmp file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(processed_content, encoding="utf-8")
    tmp_path.replace(output_path)

    print(f"Successfully saved Markdown to: {output_path}")
    if assets_dir.exists() and any(assets_dir.iterdir()):
        print(f"Assets downloaded to: {assets_dir}")


if __name__ == "__main__":
    main()
