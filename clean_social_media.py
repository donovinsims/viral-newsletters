#!/usr/bin/env python3
"""
Clean and normalize Twitter & LinkedIn JSON data for LLM scraping.
Also re-optimizes newsletter JSONs.
"""

import json
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/forex/Downloads/Viral Newsletters")
OUTPUT_DIR = BASE_DIR / "cleaned"


def clean_text(text: str) -> str:
    """Clean social media text content."""
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove zero-width spaces
    text = text.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
    # Remove emoji CTA patterns but keep content emojis
    text = re.sub(r'♻️\s*(Reshare|Repost|Share)[^.]*\.?', '', text, flags=re.IGNORECASE)
    # Clean up trailing whitespace
    text = text.strip()
    return text


def calculate_engagement_rate(stats: dict, views: int = None) -> float:
    """Calculate engagement rate as percentage."""
    if views and views > 0:
        # Twitter style: (likes + retweets + replies) / views
        total_engagement = stats.get('likes', 0) + stats.get('retweets', 0) + stats.get('replies', 0)
        return round((total_engagement / views) * 100, 2)
    elif 'total_reactions' in stats:
        # LinkedIn: just return total reactions as a score
        return stats['total_reactions']
    return 0


def process_twitter():
    """Process Twitter data to clean JSON format."""
    input_file = BASE_DIR / "refrence_top_tweets_posts.txt" / "dataset_twitter-scraper_goats.txt"
    output_dir = OUTPUT_DIR / "twitter"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        tweets = json.load(f)
    
    cleaned_tweets = []
    
    for tweet in tweets:
        # Skip low-engagement posts (less than 50 likes)
        if tweet.get('likes', 0) < 50:
            continue
        
        # Skip very short tweets (likely replies or fragments)
        text = tweet.get('text') or ''
        if len(text) < 50:
            continue
        
        # Calculate engagement rate
        views = tweet.get('views', 0)
        engagement_rate = 0
        if views > 0:
            engagement = tweet.get('likes', 0) + tweet.get('retweets', 0) + tweet.get('replies', 0)
            engagement_rate = round((engagement / views) * 100, 2)
        
        cleaned = {
            "id": tweet.get('id'),
            "source": "twitter",
            "author": tweet.get('username', '').lstrip('@'),
            "date": tweet.get('timestamp', '').split('T')[0] if tweet.get('timestamp') else None,
            "url": tweet.get('url'),
            "text": clean_text(text),
            "word_count": len(text.split()),
            "metrics": {
                "likes": tweet.get('likes', 0),
                "retweets": tweet.get('retweets', 0),
                "replies": tweet.get('replies', 0),
                "views": views,
                "engagement_rate": engagement_rate
            }
        }
        cleaned_tweets.append(cleaned)
    
    # Sort by engagement (likes)
    cleaned_tweets.sort(key=lambda x: x['metrics']['likes'], reverse=True)
    
    # Save as single JSON array
    output_file = output_dir / "twitter_posts_cleaned.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_tweets, f, indent=2, ensure_ascii=False)
    
    # Also save individual files for top posts
    for i, tweet in enumerate(cleaned_tweets[:50]):  # Top 50 by likes
        individual_file = output_dir / f"tweet_{tweet['id']}.json"
        with open(individual_file, 'w', encoding='utf-8') as f:
            json.dump(tweet, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Twitter: {len(cleaned_tweets)} posts cleaned (from {len(tweets)} original)")
    return len(cleaned_tweets)


def process_linkedin():
    """Process LinkedIn data to clean JSON format."""
    input_file = BASE_DIR / "refrence_ruben_hassid_ai _guru_linkedin_posts.txt" / "dataset_linkedin-profile-posts_ruben_hassid.txt"
    output_dir = OUTPUT_DIR / "linkedin"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        posts = json.load(f)
    
    cleaned_posts = []
    
    for i, post in enumerate(posts):
        # Flatten nested structures
        posted_at = post.get('posted_at', {})
        author = post.get('author', {})
        stats = post.get('stats', {})
        
        # Parse date
        raw_date = posted_at.get('date', '')
        date = None
        if raw_date:
            try:
                # Format: "2025-05-13 07:00:08"
                date = raw_date.split(' ')[0]
            except:
                date = None
        
        # Clean text
        text = clean_text(post.get('text', ''))
        
        # Skip empty posts
        if not text or len(text) < 30:
            continue
        
        cleaned = {
            "id": f"linkedin_{i+1}",
            "source": "linkedin",
            "author": f"{author.get('first_name', '')} {author.get('last_name', '')}".strip(),
            "author_username": author.get('username'),
            "author_headline": author.get('headline'),
            # NO profile_picture - explicitly removed as requested
            "date": date,
            "profile_url": author.get('profile_url'),
            "text": text,
            "word_count": len(text.split()),
            "metrics": {
                "total_reactions": stats.get('total_reactions', 0),
                "likes": stats.get('like', 0),
                "love": stats.get('love', 0),
                "insight": stats.get('insight', 0),
                "celebrate": stats.get('celebrate', 0),
                "support": stats.get('support', 0),
                "funny": stats.get('funny', 0),
                "comments": stats.get('comments', 0),
                "reposts": stats.get('reposts', 0)
            }
        }
        cleaned_posts.append(cleaned)
    
    # Sort by total reactions
    cleaned_posts.sort(key=lambda x: x['metrics']['total_reactions'], reverse=True)
    
    # Save as single JSON array
    output_file = output_dir / "linkedin_posts_cleaned.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_posts, f, indent=2, ensure_ascii=False)
    
    # Also save individual files for top posts
    for post in cleaned_posts[:50]:  # Top 50 by reactions
        individual_file = output_dir / f"{post['id']}.json"
        with open(individual_file, 'w', encoding='utf-8') as f:
            json.dump(post, f, indent=2, ensure_ascii=False)
    
    print(f"✓ LinkedIn: {len(cleaned_posts)} posts cleaned (from {len(posts)} original)")
    return len(cleaned_posts)


def reoptimize_newsletters():
    """Re-optimize newsletter JSONs with better topic extraction and ad removal."""
    improved = 0
    
    for source in ["chris_williamson", "tim_denning"]:
        source_dir = OUTPUT_DIR / source
        if not source_dir.exists():
            continue
        
        for json_file in source_dir.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Fix topics - remove generic ones
            bad_topics = {'Post', 'Page2', 'Page3', 'Page4', 'Page5', 'Page6', 
                         'Page7', 'Page8', 'Page9', 'Pageunknown', 'Minute', 'Monday'}
            if 'topics' in data:
                data['topics'] = [t for t in data['topics'] if t not in bad_topics]
            
            # Remove remaining promotional sections from content
            if 'sections' in data:
                cleaned_sections = []
                for section in data['sections']:
                    heading = section.get('heading', '')
                    # Skip pure promotional sections
                    if heading in ['LIFE HACK'] and 'LMNT' in section.get('content', ''):
                        continue
                    cleaned_sections.append(section)
                data['sections'] = cleaned_sections
            
            # Clean main_content of promotional CTAs
            if 'main_content' in data:
                content = data['main_content']
                # Remove common promotional patterns
                content = re.sub(r'Try LMNT Risk-Free[^\n]*\n?', '', content)
                content = re.sub(r'Big love,\s*Chris x', '', content)
                content = re.sub(r'Try my productivity drink[^\n]*\n?', '', content)
                data['main_content'] = content.strip()
                data['word_count'] = len(content.split())
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            improved += 1
    
    print(f"✓ Newsletters: {improved} files re-optimized")
    return improved


def update_manifest():
    """Update the manifest with all sources."""
    manifest_file = OUTPUT_DIR / "manifest.json"
    
    # Count files
    twitter_count = len(list((OUTPUT_DIR / "twitter").glob("*.json"))) if (OUTPUT_DIR / "twitter").exists() else 0
    linkedin_count = len(list((OUTPUT_DIR / "linkedin").glob("*.json"))) if (OUTPUT_DIR / "linkedin").exists() else 0
    chris_count = len(list((OUTPUT_DIR / "chris_williamson").glob("*.json"))) if (OUTPUT_DIR / "chris_williamson").exists() else 0
    tim_count = len(list((OUTPUT_DIR / "tim_denning").glob("*.json"))) if (OUTPUT_DIR / "tim_denning").exists() else 0
    
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "sources": {
            "twitter": {"files": twitter_count, "description": "Cleaned viral Twitter posts"},
            "linkedin": {"files": linkedin_count, "description": "Ruben Hassid LinkedIn posts"},
            "chris_williamson": {"files": chris_count, "description": "Chris Williamson newsletters"},
            "tim_denning": {"files": tim_count, "description": "Tim Denning Substack posts"}
        },
        "total_files": twitter_count + linkedin_count + chris_count + tim_count
    }
    
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"Manifest updated: {manifest['total_files']} total files")
    
    return manifest


if __name__ == "__main__":
    print("Cleaning social media data...\n")
    
    twitter_count = process_twitter()
    linkedin_count = process_linkedin()
    newsletter_count = reoptimize_newsletters()
    
    update_manifest()
    
    print(f"\nAll data cleaned successfully!")
