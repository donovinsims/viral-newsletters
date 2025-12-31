#!/usr/bin/env python3
"""
Viral Newsletter Markdown → JSON Converter

Converts markdown newsletter files from Chris Williamson and Tim Denning
into clean, structured JSON format for LLM consumption.
"""

import json
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

# Configuration
BASE_DIR = Path("/Users/forex/Downloads/Viral Newsletters")
INPUT_DIRS = {
    "chris_williamson": BASE_DIR / "top_chriswilliamson_newsletters",
    "tim_denning": BASE_DIR / "top_tim-denning_substack_posts",
}
OUTPUT_DIR = BASE_DIR / "cleaned"


def clean_content(text: str) -> str:
    """Remove ads, tracking links, images, and promotional content."""
    
    # Remove image markdown
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    
    # Remove tracking/affiliate links (keep link text)
    text = re.sub(r'\[([^\]]+)\]\(https?://click\.convertkit[^\)]+\)', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\(https?://[^\)]*?drinklmnt[^\)]*?\)', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\(https?://[^\)]*?neutonic[^\)]*?\)', r'\1', text)
    
    # Remove promotional sections
    promo_patterns = [
        r'## \*\*LIFE HACK\*\*.*?(?=##|\Z)',  # LIFE HACK sections with ads
        r'Try my productivity drink.*?(?=\n\n|\Z)',
        r'Share this article with your friends.*?(?=\n\n|\Z)',
        r'\*\*LMNT.*?(?=\n\n|\Z)',
        r'Click here to grab your seat.*?(?=\n|\Z)',
        r'PS:.*?(?=\n\n|\Z)',
        r'^PS\s+.*?(?=\n\n|\Z)',
    ]
    for pattern in promo_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.MULTILINE | re.IGNORECASE)
    
    # Remove duplicate bullet points (common in Tim Denning posts)
    lines = text.split('\n')
    seen_bullets = set()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('* ') or stripped.startswith('- '):
            bullet_content = stripped[2:].strip()
            if bullet_content in seen_bullets:
                continue
            seen_bullets.add(bullet_content)
        cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines)
    
    # Normalize whitespace
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    text = re.sub(r'​', '', text)  # Remove zero-width spaces
    text = text.strip()
    
    return text


def extract_topics_from_filename(filename: str) -> list[str]:
    """Extract topics from filename slugs."""
    # Remove common prefixes and extensions
    name = re.sub(r'^post-page\d+-', '', filename)
    name = re.sub(r'^post-pageunknown-', '', filename)
    name = re.sub(r'\.md$', '', name)
    
    # Split on common separators
    parts = re.split(r'[-_]', name)
    
    # Filter out common words and short items
    stopwords = {'3', 'minute', 'monday', 'the', 'a', 'an', 'and', 'or', 'to', 'of', 'in', 'for', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought', 'used', 'if', 'you', 'your', 'youre', 'its', 'im', 'ive', 'that', 'this', 'these', 'those', 'who', 'what', 'which', 'how', 'when', 'where', 'why'}
    
    topics = []
    for part in parts:
        cleaned = part.lower().strip()
        if len(cleaned) > 2 and cleaned not in stopwords:
            topics.append(cleaned.capitalize())
    
    return topics[:5]  # Limit to 5 topics


def extract_sections(content: str) -> list[dict]:
    """Extract sections from markdown content."""
    sections = []
    
    # Split by H2 headers
    pattern = r'^##\s+(.+?)$'
    parts = re.split(pattern, content, flags=re.MULTILINE)
    
    if len(parts) > 1:
        # First part is content before any H2
        if parts[0].strip():
            sections.append({
                "heading": "Introduction",
                "content": clean_content(parts[0])
            })
        
        # Pairs of (heading, content)
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                heading = parts[i].strip().replace('**', '')
                content_part = parts[i + 1].strip()
                if content_part:
                    sections.append({
                        "heading": heading,
                        "content": clean_content(content_part)
                    })
    else:
        # No H2 headers, treat entire content as one section
        sections.append({
            "heading": "Main",
            "content": clean_content(content)
        })
    
    return sections


def calculate_reading_time(text: str) -> int:
    """Calculate estimated reading time in minutes (assuming 200 wpm)."""
    words = len(text.split())
    return max(1, round(words / 200))


def parse_chris_williamson(filepath: Path) -> dict:
    """Parse Chris Williamson newsletter format."""
    content = filepath.read_text(encoding='utf-8')
    filename = filepath.name
    
    # Extract title from first bold line or H2
    title_match = re.search(r'\*\*(.+?)\*\*', content)
    if not title_match:
        title_match = re.search(r'^##\s+(.+?)$', content, re.MULTILINE)
    
    title = title_match.group(1) if title_match else filename.replace('.md', '').replace('-', ' ').title()
    
    # Clean and extract content
    cleaned = clean_content(content)
    sections = extract_sections(content)
    topics = extract_topics_from_filename(filename)
    
    # Generate ID from filename
    slug = re.sub(r'[^a-z0-9]+', '-', filename.lower().replace('.md', ''))
    
    return {
        "id": slug,
        "source": "chris_williamson",
        "title": title[:200],  # Limit title length
        "author": "Chris Williamson",
        "date": None,  # Not available in these files
        "source_url": None,
        "topics": topics,
        "sections": sections,
        "main_content": cleaned,
        "word_count": len(cleaned.split()),
        "reading_time_minutes": calculate_reading_time(cleaned)
    }


def parse_tim_denning(filepath: Path) -> dict:
    """Parse Tim Denning Substack post format."""
    content = filepath.read_text(encoding='utf-8')
    filename = filepath.name
    
    # Extract metadata from header
    title_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else filename.replace('.md', '').replace('_', ' ').title()
    
    # Extract date
    date_match = re.search(r'\*\*Date:\*\*\s*(.+?)$', content, re.MULTILINE)
    date_str = None
    if date_match:
        raw_date = date_match.group(1).strip()
        if raw_date and raw_date != "Unknown Date":
            date_str = raw_date
    
    # Extract source URL
    url_match = re.search(r'\*\*Source URL:\*\*\s*(https?://[^\s]+)', content)
    source_url = url_match.group(1) if url_match else None
    
    # Remove metadata section for content processing
    content_start = content.find('---', 10)
    if content_start != -1:
        main_content = content[content_start + 3:]
    else:
        main_content = content
    
    # Clean and extract
    cleaned = clean_content(main_content)
    sections = extract_sections(main_content)
    topics = extract_topics_from_filename(filename)
    
    # Generate ID
    slug = re.sub(r'[^a-z0-9]+', '-', filename.lower().replace('.md', ''))
    
    return {
        "id": slug,
        "source": "tim_denning",
        "title": title[:200],
        "author": "Tim Denning",
        "date": date_str,
        "source_url": source_url,
        "topics": topics,
        "sections": sections,
        "main_content": cleaned,
        "word_count": len(cleaned.split()),
        "reading_time_minutes": calculate_reading_time(cleaned)
    }


def process_all_files():
    """Process all newsletter files and output JSON."""
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "sources": {},
        "total_files": 0,
        "total_words": 0
    }
    
    parsers = {
        "chris_williamson": parse_chris_williamson,
        "tim_denning": parse_tim_denning,
    }
    
    for source, input_dir in INPUT_DIRS.items():
        output_subdir = OUTPUT_DIR / source
        output_subdir.mkdir(parents=True, exist_ok=True)
        
        source_stats = {"files": 0, "words": 0, "errors": []}
        
        for md_file in sorted(input_dir.glob("*.md")):
            try:
                parser = parsers[source]
                data = parser(md_file)
                
                # Write JSON output
                output_file = output_subdir / (md_file.stem + ".json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                source_stats["files"] += 1
                source_stats["words"] += data["word_count"]
                
                print(f"✓ {source}/{md_file.name} → {data['word_count']} words")
                
            except Exception as e:
                error_msg = f"{md_file.name}: {str(e)}"
                source_stats["errors"].append(error_msg)
                print(f"✗ {source}/{md_file.name} - ERROR: {e}")
        
        manifest["sources"][source] = source_stats
        manifest["total_files"] += source_stats["files"]
        manifest["total_words"] += source_stats["words"]
    
    # Write manifest
    manifest_file = OUTPUT_DIR / "manifest.json"
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"Conversion complete!")
    print(f"Total files: {manifest['total_files']}")
    print(f"Total words: {manifest['total_words']:,}")
    print(f"Manifest: {manifest_file}")
    
    return manifest


def verify_output():
    """Verify all JSON files are valid and complete."""
    errors = []
    valid_count = 0
    
    for source in ["chris_williamson", "tim_denning"]:
        output_dir = OUTPUT_DIR / source
        for json_file in output_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                
                # Check required fields
                required = ["id", "source", "title", "main_content", "word_count"]
                missing = [f for f in required if f not in data or not data[f]]
                
                if missing:
                    errors.append(f"{json_file.name}: Missing fields: {missing}")
                else:
                    valid_count += 1
                    
            except json.JSONDecodeError as e:
                errors.append(f"{json_file.name}: Invalid JSON - {e}")
    
    print(f"\nVerification Results:")
    print(f"  Valid files: {valid_count}")
    print(f"  Errors: {len(errors)}")
    
    for err in errors[:10]:
        print(f"  - {err}")
    
    return len(errors) == 0


if __name__ == "__main__":
    import sys
    
    if "--verify" in sys.argv:
        success = verify_output()
        sys.exit(0 if success else 1)
    else:
        process_all_files()
        verify_output()
