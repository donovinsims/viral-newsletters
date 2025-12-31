#!/usr/bin/env python3
"""
Script to remove large bulky URLs from newsletter markdown files.
Targets Substack CDN image URLs and similar long URLs that clutter the content.
"""

import os
import re
import json
from pathlib import Path


def remove_bulky_urls(content: str) -> str:
    """Remove bulky image URLs and markdown image references from content."""
    
    # Pattern to match markdown image syntax with long Substack CDN URLs
    # ![alt text](https://substackcdn.com/image/fetch/...)
    substack_img_pattern = r'!\[([^\]]*)\]\(https://substackcdn\.com/image/fetch/[^\)]+\)'
    
    # Remove entire markdown image lines with Substack CDN URLs
    content = re.sub(substack_img_pattern, '', content)
    
    # Pattern to match standalone Substack CDN URLs
    standalone_url_pattern = r'https://substackcdn\.com/image/fetch/[^\s\)\]]+\s*'
    content = re.sub(standalone_url_pattern, '', content)
    
    # Pattern to match Substack post media URLs (s3.amazonaws.com)
    s3_img_pattern = r'!\[([^\]]*)\]\(https://substack-post-media\.s3\.amazonaws\.com/[^\)]+\)'
    content = re.sub(s3_img_pattern, '', content)
    
    # Remove any remaining long URLs (100+ chars) that look like CDN/image URLs
    long_cdn_url_pattern = r'https://[a-zA-Z0-9\-\.]+\.(amazonaws\.com|cloudfront\.net|substackcdn\.com)/[^\s\)\]]{100,}\s*'
    content = re.sub(long_cdn_url_pattern, '', content)
    
    # Clean up empty markdown image syntax that might be left
    content = re.sub(r'!\[\]\(\)', '', content)
    
    # Clean up multiple consecutive blank lines (reduce to max 2)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()


def process_markdown_files(directory: Path, dry_run: bool = False) -> dict:
    """Process all markdown files in a directory."""
    results = {'processed': 0, 'modified': 0, 'files': []}
    
    for md_file in directory.glob('*.md'):
        results['processed'] += 1
        
        with open(md_file, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        cleaned_content = remove_bulky_urls(original_content)
        
        if cleaned_content != original_content:
            results['modified'] += 1
            original_size = len(original_content)
            cleaned_size = len(cleaned_content)
            reduction = original_size - cleaned_size
            
            results['files'].append({
                'name': md_file.name,
                'original_size': original_size,
                'cleaned_size': cleaned_size,
                'reduction': reduction,
                'reduction_pct': round((reduction / original_size) * 100, 2)
            })
            
            if not dry_run:
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
    
    return results


def process_json_files(directory: Path, dry_run: bool = False) -> dict:
    """Process all JSON files in a directory to clean URLs from content fields."""
    results = {'processed': 0, 'modified': 0, 'files': []}
    
    for json_file in directory.glob('*.json'):
        results['processed'] += 1
        
        with open(json_file, 'r', encoding='utf-8') as f:
            original_content = f.read()
            data = json.loads(original_content)
        
        modified = False
        
        # Clean main_content field if it exists
        if 'main_content' in data and data['main_content']:
            cleaned = remove_bulky_urls(data['main_content'])
            if cleaned != data['main_content']:
                data['main_content'] = cleaned
                modified = True
        
        # Clean sections content if exists
        if 'sections' in data and isinstance(data['sections'], list):
            for section in data['sections']:
                if 'content' in section and section['content']:
                    cleaned = remove_bulky_urls(section['content'])
                    if cleaned != section['content']:
                        section['content'] = cleaned
                        modified = True
        
        if modified:
            results['modified'] += 1
            new_content = json.dumps(data, indent=2, ensure_ascii=False)
            original_size = len(original_content)
            cleaned_size = len(new_content)
            reduction = original_size - cleaned_size
            
            results['files'].append({
                'name': json_file.name,
                'original_size': original_size,
                'cleaned_size': cleaned_size,
                'reduction': reduction,
                'reduction_pct': round((reduction / original_size) * 100, 2) if original_size > 0 else 0
            })
            
            if not dry_run:
                with open(json_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
    
    return results


def main():
    base_dir = Path('/Users/forex/Downloads/Viral Newsletters')
    
    directories_to_process = {
        'tim_denning_md': base_dir / 'cleaned/original_copies/top_tim-denning_substack_posts',
        'chris_williamson_md': base_dir / 'cleaned/original_copies/top_chriswilliamson_newsletters',
        'tim_denning_json': base_dir / 'cleaned/tim_denning',
        'chris_williamson_json': base_dir / 'cleaned/chris_williamson',
    }
    
    print("=" * 60)
    print("NEWSLETTER URL CLEANING SCRIPT")
    print("=" * 60)
    
    total_stats = {
        'md_processed': 0,
        'md_modified': 0,
        'json_processed': 0,
        'json_modified': 0,
        'total_reduction': 0
    }
    
    # Process markdown files
    for name, directory in directories_to_process.items():
        if not directory.exists():
            print(f"\n⚠️  Directory not found: {directory}")
            continue
        
        print(f"\n📁 Processing: {directory.name}")
        print("-" * 40)
        
        if name.endswith('_md'):
            results = process_markdown_files(directory, dry_run=False)
            total_stats['md_processed'] += results['processed']
            total_stats['md_modified'] += results['modified']
        else:
            results = process_json_files(directory, dry_run=False)
            total_stats['json_processed'] += results['processed']
            total_stats['json_modified'] += results['modified']
        
        print(f"   Files processed: {results['processed']}")
        print(f"   Files modified: {results['modified']}")
        
        if results['files']:
            total_reduction = sum(f['reduction'] for f in results['files'])
            total_stats['total_reduction'] += total_reduction
            print(f"   Total size reduction: {total_reduction:,} bytes ({total_reduction / 1024:.1f} KB)")
            
            # Show top 5 files with most reduction
            top_files = sorted(results['files'], key=lambda x: x['reduction'], reverse=True)[:5]
            if top_files:
                print("\n   Top files with most reduction:")
                for f in top_files:
                    print(f"      • {f['name'][:50]}... -{f['reduction']:,} bytes ({f['reduction_pct']}%)")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Markdown files: {total_stats['md_processed']} processed, {total_stats['md_modified']} modified")
    print(f"JSON files: {total_stats['json_processed']} processed, {total_stats['json_modified']} modified")
    print(f"Total size reduction: {total_stats['total_reduction']:,} bytes ({total_stats['total_reduction'] / 1024:.1f} KB)")
    print("\n✅ Done!")


if __name__ == '__main__':
    main()
