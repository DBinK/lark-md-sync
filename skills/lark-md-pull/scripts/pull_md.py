#!/usr/bin/env python3
"""Pull a Lark document as Markdown, download images to assets/, and rewrite local paths."""

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
    # Pattern 1: Standard markdown images with lark media token or internal path: ![alt](token) or ![alt](url)
    # Pattern 2: Lark DocxXML fallback images: <img token="boxcn..." .../> or <img href="..."/>

    token_pattern = re.compile(r"!\[(.*?)\]\(([a-zA-Z0-9_\-]+)\)")
    img_tag_pattern = re.compile(r'<img\s+[^>]*token=["\']([a-zA-Z0-9_\-]+)["\'][^>]*\/?>')

    # Find tokens from markdown image syntax
    def replace_md_token(match: re.Match[str]) -> str:
        alt = match.group(1)
        token = match.group(2)
        # Avoid rewriting http(s) urls or local paths
        if token.startswith("http://") or token.startswith("https://") or "/" in token or "." in token:
            return match.group(0)

        ext = ".png"
        target_file = assets_dir / f"{token}{ext}"
        if download_media(doc_target, token, target_file, identity):
            # Use relative path from output markdown's perspective
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
        description="Pull Lark doc to local Markdown with media assets"
    )
    parser.add_argument("doc", help="Lark document URL or token")
    parser.add_argument(
        "-o",
        "--output",
        default="README.md",
        help="Local output markdown path (default: README.md)",
    )
    parser.add_argument(
        "--assets-dir",
        default="assets",
        help="Assets directory relative to output directory (default: assets)",
    )
    parser.add_argument(
        "--as",
        dest="identity",
        default="user",
        choices=["user", "bot"],
        help="Identity type (default: user)",
    )

    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    assets_dir = output_path.parent / args.assets_dir

    print(f"Fetching document: {args.doc} ...")
    content = fetch_lark_doc_markdown(args.doc, identity=args.identity)

    print("Processing multi-media assets...")
    processed_content = process_markdown_media(
        content, args.doc, assets_dir=assets_dir, identity=args.identity
    )

    # Write output markdown atomically via tmp file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(processed_content, encoding="utf-8")
    tmp_path.replace(output_path)

    print(f"Successfully saved Markdown to: {output_path}")


if __name__ == "__main__":
    main()
