"""
AIDevBuilds — GitHub README Auto-Updater
Fetches latest 5 YouTube videos and updates the
<!-- YOUTUBE-VIDEOS-START --> section in README.md
"""

import os
import re
import requests
from datetime import datetime

YOUTUBE_API_KEY  = os.environ["YOUTUBE_API_KEY"]
CHANNEL_HANDLE   = os.environ.get("CHANNEL_HANDLE", "AIDevBuilds")
MAX_VIDEOS       = 5
README_PATH      = "README.md"

# Autopsy emoji map — based on video title keywords
AUTOPSY_KEYWORDS = {
    "security": "🔴 Security hole",
    "jwt":      "🔴 Auth bypass",
    "bug":      "🟠 Logic bug",
    "crash":    "🔴 Server crash",
    "memory":   "🟠 Memory leak",
    "context":  "🟡 Context lost",
    "hallucin": "🟠 Hallucination",
    "race":     "🔴 Race condition",
    "cors":     "🟡 CORS misconfigured",
    "env":      "🟡 Env config bug",
    "null":     "🟠 Null reference",
    "sql":      "🔴 SQL vulnerability",
}

def get_channel_id(handle: str) -> str:
    """Resolve @handle to channel ID using YouTube API."""
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part":       "id",
        "forHandle":  handle,
        "key":        YOUTUBE_API_KEY,
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    if not items:
        raise ValueError(f"Channel not found for handle: @{handle}")
    return items[0]["id"]


def get_latest_videos(channel_id: str, max_results: int = 5) -> list:
    """Fetch the latest videos from a channel."""
    # Step 1: get uploads playlist ID
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part":  "contentDetails",
        "id":    channel_id,
        "key":   YOUTUBE_API_KEY,
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    uploads_playlist = (
        resp.json()["items"][0]
        ["contentDetails"]["relatedPlaylists"]["uploads"]
    )

    # Step 2: get videos from uploads playlist
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part":       "snippet",
        "playlistId": uploads_playlist,
        "maxResults": max_results,
        "key":        YOUTUBE_API_KEY,
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()

    videos = []
    for item in resp.json().get("items", []):
        snippet  = item["snippet"]
        video_id = snippet["resourceId"]["videoId"]
        title    = snippet["title"]
        desc     = snippet.get("description", "")

        # Try to detect autopsy moment from description
        autopsy = detect_autopsy(title + " " + desc)

        # Try to detect tools used from title/description
        tools = detect_tools(title + " " + desc)

        # Try to detect video number from title
        num = detect_number(title)

        videos.append({
            "num":     num,
            "title":   title,
            "url":     f"https://youtu.be/{video_id}",
            "tools":   tools,
            "autopsy": autopsy,
        })

    return videos


def detect_autopsy(text: str) -> str:
    """Guess the autopsy finding from title/description keywords."""
    text_lower = text.lower()
    for keyword, label in AUTOPSY_KEYWORDS.items():
        if keyword in text_lower:
            return label
    return "🔬 See video"


def detect_tools(text: str) -> str:
    """Detect AI tools mentioned in title or description."""
    text_lower = text.lower()
    found = []
    tool_map = {
        "claude code":    "Claude Code",
        "copilot":        "Copilot",
        "cursor":         "Cursor",
        "windsurf":       "Windsurf",
        "chatgpt":        "ChatGPT",
        "gemini":         "Gemini",
        "fastapi":        "FastAPI",
        "node.js":        "Node.js",
        "next.js":        "Next.js",
        "python":         "Python",
        "express":        "Express",
    }
    for keyword, label in tool_map.items():
        if keyword in text_lower and label not in found:
            found.append(label)
    return " · ".join(found[:4]) if found else "AI Tools"


def detect_number(title: str) -> str:
    """Try to extract video number like #01 or Video 01 from title."""
    match = re.search(r'#(\d+)|[Vv]ideo\s+(\d+)|[Ee]p\.?\s*(\d+)', title)
    if match:
        num = match.group(1) or match.group(2) or match.group(3)
        return f"#{num.zfill(2)}"
    return "🔴"


def build_table(videos: list) -> str:
    """Build the markdown table rows for the README."""
    rows = ["| # | Video | Tools Used | Autopsy |",
            "|---|-------|------------|---------|"]
    for v in videos:
        row = f"| 🔴 {v['num']} | [{v['title']}]({v['url']}) | {v['tools']} | {v['autopsy']} |"
        rows.append(row)
    return "\n".join(rows)


def update_readme(table: str) -> None:
    """Replace content between YOUTUBE-VIDEOS markers in README.md"""
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    updated = content
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    new_block = (
        f"<!-- YOUTUBE-VIDEOS-START -->\n"
        f"<!-- Last updated: {timestamp} -->\n"
        f"{table}\n"
        f"<!-- YOUTUBE-VIDEOS-END -->"
    )

    pattern = r"<!-- YOUTUBE-VIDEOS-START -->.*?<!-- YOUTUBE-VIDEOS-END -->"
    updated = re.sub(pattern, new_block, content, flags=re.DOTALL)

    if updated == content:
        print("No markers found in README — check YOUTUBE-VIDEOS-START/END comments")
        return

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"README updated with {len(videos)} videos at {timestamp}")


if __name__ == "__main__":
    print(f"Fetching videos for @{CHANNEL_HANDLE}...")
    channel_id = get_channel_id(CHANNEL_HANDLE)
    print(f"Channel ID: {channel_id}")

    videos = get_latest_videos(channel_id, MAX_VIDEOS)
    print(f"Found {len(videos)} videos")
    for v in videos:
        print(f"  {v['num']} — {v['title'][:60]}")

    table = build_table(videos)
    update_readme(table)
