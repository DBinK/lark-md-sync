#!/usr/bin/env python3
"""Pull a Lark document as Markdown, download images/whiteboards to a per-doc assets folder, and rewrite local paths."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a shell command safely and return output."""
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def slugify_title(title: str) -> str:
    """Convert title to safe, space-free Unicode slug using hyphens.

    Preserves Chinese/CJK characters and alphanumerics, replaces spaces and symbols with single hyphen.
    """
    s = title.strip()
    s = re.sub(r"^#+\s*", "", s)
    s = re.sub(r'[\s/\\:*?"<>|()\[\]{}（）【】、，。,\'"`~!@#$%^&+;=]+', "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    s = s.lower()
    return s or "untitled"


def extract_title_from_markdown(content: str) -> str:
    """Extract document title from the first heading, <title> tag, or first non-empty line."""
    title_match = re.search(r"<title[^>]*>(.*?)</title>", content, flags=re.DOTALL)
    if title_match and title_match.group(1).strip():
        return title_match.group(1).strip()

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            return re.sub(r"^#+\s*", "", line).strip()
        return line[:50].strip()
    return "untitled"


def fetch_lark_doc(doc_target: str, identity: str = "user") -> tuple[str, dict[str, Any]]:
    """Fetch raw markdown and reference_map from Lark document using lark-cli."""
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
    ]
    proc = run_command(cmd)
    if proc.returncode != 0:
        sys.stderr.write(f"Failed to fetch lark doc: {proc.stderr or proc.stdout}\n")
        sys.exit(proc.returncode)

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as err:
        sys.stderr.write(f"Failed to parse lark-cli output JSON: {err}\n")
        sys.exit(1)

    if not data.get("ok"):
        sys.stderr.write(f"lark-cli error: {data}\n")
        sys.exit(1)

    doc_data = data.get("data", {}).get("document", {})
    content = doc_data.get("content", "")
    ref_map = doc_data.get("reference_map", {}) or {}
    return content, ref_map


def download_media(
    token: str,
    assets_dir: Path,
    identity: str = "user",
    media_type: str = "media",
) -> str | None:
    """Download media or whiteboard token via lark-cli and return the saved filename."""
    assets_dir.mkdir(parents=True, exist_ok=True)
    base_output = assets_dir / token
    cmd = [
        "lark-cli",
        "docs",
        "+media-download",
        "--token",
        token,
        "--type",
        media_type,
        "--output",
        str(base_output),
        "--overwrite",
        "--as",
        identity,
    ]
    proc = run_command(cmd)
    if proc.returncode != 0:
        sys.stderr.write(
            f"Warning: Failed to download {media_type} token {token}: {proc.stderr or proc.stdout}\n"
        )
        return None

    # Check JSON output for exact saved path (lark-cli auto-completes file extension)
    try:
        res_data = json.loads(proc.stdout)
        saved_out = (
            res_data.get("data", {}).get("output")
            or res_data.get("data", {}).get("path")
            or res_data.get("output")
        )
        if saved_out and Path(saved_out).exists():
            return Path(saved_out).name
    except json.JSONDecodeError:
        pass

    # Fallback: check files in assets_dir matching token.* or token
    matches = sorted(assets_dir.glob(f"{token}.*"))
    if matches:
        return matches[0].name
    if base_output.exists():
        return base_output.name
    return None


def resolve_ref_token(
    raw_ref: str, ref_map: dict[str, Any], default_group: str = "img"
) -> str:
    """Resolve short reference key (e.g. img_1) from reference_map if present."""
    for group in (default_group, "image", "media", "source", "whiteboard"):
        group_dict = ref_map.get(group)
        if isinstance(group_dict, dict) and raw_ref in group_dict:
            entry = group_dict[raw_ref]
            if isinstance(entry, dict) and entry.get("token"):
                return str(entry["token"])
    return raw_ref


def process_markdown_media(
    content: str,
    ref_map: dict[str, Any],
    assets_dir: Path,
    identity: str = "user",
) -> str:
    """Extract media tokens, images, and whiteboards, download them to assets_dir, and rewrite paths."""
    token_pattern = re.compile(r"!\[(.*?)\]\(([a-zA-Z0-9_\-]+)\)")
    img_tag_pattern = re.compile(
        r'<img\s+[^>]*?(?:token|ref)=["\']([a-zA-Z0-9_\-]+)["\'][^>]*?\/?>'
    )
    wb_tag_pattern = re.compile(
        r'<whiteboard\s+[^>]*?(?:token|ref)=["\']([a-zA-Z0-9_\-]+)["\'][^>]*?\/?>'
    )

    def replace_md_token(match: re.Match[str]) -> str:
        alt = match.group(1)
        raw_token = match.group(2)
        if (
            raw_token.startswith(("http://", "https://", "@"))
            or "/" in raw_token
            or "." in raw_token
        ):
            return match.group(0)

        token = resolve_ref_token(raw_token, ref_map, "img")
        saved_name = download_media(token, assets_dir, identity, media_type="media")
        if saved_name:
            return f"![{alt}]({assets_dir.name}/{saved_name})"
        return match.group(0)

    content = token_pattern.sub(replace_md_token, content)

    def replace_img_tag(match: re.Match[str]) -> str:
        raw_token = match.group(1)
        token = resolve_ref_token(raw_token, ref_map, "img")
        saved_name = download_media(token, assets_dir, identity, media_type="media")
        if saved_name:
            return f"![image]({assets_dir.name}/{saved_name})"
        return match.group(0)

    content = img_tag_pattern.sub(replace_img_tag, content)

    def replace_wb_tag(match: re.Match[str]) -> str:
        raw_token = match.group(1)
        token = resolve_ref_token(raw_token, ref_map, "whiteboard")
        saved_name = download_media(
            token, assets_dir, identity, media_type="whiteboard"
        )
        if saved_name:
            return f"![whiteboard]({assets_dir.name}/{saved_name})"
        return match.group(0)

    content = wb_tag_pattern.sub(replace_wb_tag, content)
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
    content, ref_map = fetch_lark_doc(args.doc, identity=args.identity)

    # Determine output markdown path
    if args.output:
        output_path = Path(args.output).resolve()
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
        content, ref_map, assets_dir=assets_dir, identity=args.identity
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
