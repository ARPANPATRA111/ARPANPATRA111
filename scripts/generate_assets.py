#!/usr/bin/env python3
"""
Generate profile assets including:
- Weekly activity SVG charts
- Featured project cards (multiple projects)
- GitHub trophies with logarithmic progress
- Modern animated contribution graph
All generated locally without external API dependencies (except GitHub API).
"""

import json
import os
import re
import math
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any


# ============================================================
# CONFIGURATION
# ============================================================

GITHUB_USERNAME = os.environ.get("USERNAME", "ARPANPATRA111")
GH_TOKEN = os.environ.get("GH_TOKEN", os.environ.get("GITHUB_TOKEN", ""))

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": GITHUB_USERNAME
}
if GH_TOKEN:
    HEADERS["Authorization"] = f"token {GH_TOKEN}"


# ============================================================
# GITHUB API HELPERS
# ============================================================

def github_api_get(endpoint: str) -> Optional[Any]:
    """Make a GitHub API request."""
    url = f"https://api.github.com{endpoint}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        print(f"⚠️ GitHub API error for {endpoint}: {resp.status_code}")
    except Exception as e:
        print(f"⚠️ GitHub API request failed: {e}")
    return None


def get_user_stats() -> Dict:
    """Fetch user statistics from GitHub API with accurate commit count."""
    stats = {
        "total_repos": 0,
        "total_stars": 0,
        "total_forks": 0,
        "followers": 0,
        "following": 0,
        "public_gists": 0,
        "total_commits": 0,
        "total_prs": 0,
        "total_issues": 0,
        "contributions": {},
        "account_age_years": 0,
        "total_contributions": 0
    }
    
    # Get user info
    user_data = github_api_get(f"/users/{GITHUB_USERNAME}")
    if user_data:
        stats["total_repos"] = user_data.get("public_repos", 0)
        stats["followers"] = user_data.get("followers", 0)
        stats["following"] = user_data.get("following", 0)
        stats["public_gists"] = user_data.get("public_gists", 0)
        
        # Calculate account age
        created_at = user_data.get("created_at", "")
        if created_at:
            created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - created_date).days / 365
            stats["account_age_years"] = int(age)
    
    # Get repos to count stars, forks
    page = 1
    all_repos = []
    while True:
        repos_data = github_api_get(f"/users/{GITHUB_USERNAME}/repos?per_page=100&page={page}")
        if not repos_data:
            break
        all_repos.extend(repos_data)
        if len(repos_data) < 100:
            break
        page += 1
    
    total_commits = 0
    for repo in all_repos:
        stats["total_stars"] += repo.get("stargazers_count", 0)
        stats["total_forks"] += repo.get("forks_count", 0)
        
        # Get commit count for each repo
        if not repo.get("fork", False):  # Skip forked repos
            repo_name = repo.get("name", "")
            commits_data = github_api_get(f"/repos/{GITHUB_USERNAME}/{repo_name}/commits?author={GITHUB_USERNAME}&per_page=1")
            if commits_data:
                # Check if there's Link header for pagination count
                # For now, use contributors endpoint which gives accurate count
                contributors = github_api_get(f"/repos/{GITHUB_USERNAME}/{repo_name}/contributors?per_page=100")
                if contributors:
                    for contrib in contributors:
                        if contrib.get("login", "").lower() == GITHUB_USERNAME.lower():
                            total_commits += contrib.get("contributions", 0)
                            break
    
    stats["total_commits"] = total_commits
    
    # Get PRs created by user
    prs_data = github_api_get(f"/search/issues?q=author:{GITHUB_USERNAME}+type:pr")
    if prs_data:
        stats["total_prs"] = prs_data.get("total_count", 0)
    
    # Get issues created by user
    issues_data = github_api_get(f"/search/issues?q=author:{GITHUB_USERNAME}+type:issue")
    if issues_data:
        stats["total_issues"] = issues_data.get("total_count", 0)
    
    # Get contribution activity from events
    events = []
    for page in range(1, 4):
        page_events = github_api_get(f"/users/{GITHUB_USERNAME}/events?per_page=100&page={page}")
        if not page_events:
            break
        events.extend(page_events)
    
    # Group contributions by date
    contributions = {}
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    
    for event in events:
        created_at = event.get("created_at", "")
        if created_at:
            event_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if event_date >= cutoff:
                date_str = event_date.strftime("%Y-%m-%d")
                contributions[date_str] = contributions.get(date_str, 0) + 1
    
    stats["contributions"] = contributions
    stats["total_contributions"] = sum(contributions.values())
    
    return stats


def get_repo_info(owner: str, repo_name: str) -> Optional[Dict]:
    """Fetch repository information."""
    data = github_api_get(f"/repos/{owner}/{repo_name}")
    if data:
        # Get languages
        languages = github_api_get(f"/repos/{owner}/{repo_name}/languages")
        top_language = ""
        if languages:
            top_language = max(languages.items(), key=lambda x: x[1])[0] if languages else ""
        
        return {
            "name": data.get("name", ""),
            "full_name": data.get("full_name", ""),
            "description": data.get("description", "") or "No description provided",
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "language": top_language or data.get("language", ""),
            "topics": data.get("topics", []),
            "url": data.get("html_url", "")
        }
    return None


# ============================================================
# SVG GENERATORS
# ============================================================

def generate_weekly_activity_svg(stats: dict, theme: str = "dark") -> str:
    """Generate a weekly activity bar chart SVG."""
    daily_hours = stats.get("daily_hours", [0] * 7)
    daily_labels = stats.get("daily_labels", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    
    while len(daily_hours) < 7:
        daily_hours.append(0)
    while len(daily_labels) < 7:
        daily_labels.append("N/A")
    
    # Theme colors
    if theme == "dark":
        bg_color = "#0d1117"
        text_color = "#e6edf3"
        secondary_text = "#8b949e"
        grid_color = "#21262d"
        border_color = "#30363d"
    else:
        bg_color = "#ffffff"
        text_color = "#1f2328"
        secondary_text = "#656d76"
        grid_color = "#d0d7de"
        border_color = "#d0d7de"
    
    bar_gradients = [
        ("ff6b6b", "ff8e53"),
        ("feca57", "48dbfb"),
        ("5f27cd", "48dbfb"),
        ("ff6b81", "a55eea"),
        ("ff6348", "ffa502"),
        ("ffd32a", "7bed9f"),
        ("70a1ff", "5352ed"),
    ]
    
    width = 800
    height = 350
    padding = 60
    chart_width = width - (padding * 2)
    chart_height = height - (padding * 2) - 40
    
    max_hours = max(daily_hours) if max(daily_hours) > 0 else 8
    max_hours = max(max_hours, 1)
    
    max_idx = daily_hours.index(max(daily_hours)) if daily_hours else 0
    
    bar_width = chart_width / 7 * 0.6
    bar_spacing = chart_width / 7
    
    svg_parts = []
    svg_parts.append(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>''')
    
    for i, (color1, color2) in enumerate(bar_gradients):
        svg_parts.append(f'''
    <linearGradient id="grad{i}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#{color1};stop-opacity:1" />
      <stop offset="100%" style="stop-color:#{color2};stop-opacity:1" />
    </linearGradient>''')
    
    svg_parts.append('''
  </defs>''')
    
    svg_parts.append(f'''
  <rect width="{width}" height="{height}" fill="{bg_color}" rx="16" ry="16"/>
  <rect x="1" y="1" width="{width-2}" height="{height-2}" fill="none" stroke="{border_color}" stroke-width="1" rx="15" ry="15"/>''')
    
    for i in range(5):
        y = padding + 30 + (chart_height / 4 * i)
        hours_label = round(max_hours - (max_hours / 4 * i), 1)
        svg_parts.append(f'''
  <line x1="{padding}" y1="{y}" x2="{width - padding}" y2="{y}" stroke="{grid_color}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
  <text x="{padding - 10}" y="{y + 4}" text-anchor="end" fill="{secondary_text}" font-family="'Segoe UI', system-ui, sans-serif" font-size="11">{hours_label}h</text>''')
    
    for i, (label, hours) in enumerate(zip(daily_labels, daily_hours)):
        bar_x = padding + (bar_spacing * i) + (bar_spacing - bar_width) / 2
        bar_height = (hours / max_hours) * chart_height if max_hours > 0 else 0
        bar_y = padding + 30 + chart_height - bar_height
        
        if hours > 0 and bar_height < 10:
            bar_height = 10
            bar_y = padding + 30 + chart_height - bar_height
        
        gradient_id = i % len(bar_gradients)
        star = "⭐" if i == max_idx and hours > 0 else ""
        
        if hours > 0:
            svg_parts.append(f'''
  <rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" fill="url(#grad{gradient_id})" rx="8" ry="8">
    <animate attributeName="height" from="0" to="{bar_height}" dur="0.5s" fill="freeze"/>
    <animate attributeName="y" from="{padding + 30 + chart_height}" to="{bar_y}" dur="0.5s" fill="freeze"/>
  </rect>''')
        
        text_y = bar_y - 10 if hours > 0 else padding + 30 + chart_height - 20
        svg_parts.append(f'''
  <text x="{bar_x + bar_width/2}" y="{text_y}" text-anchor="middle" fill="{text_color}" font-family="'Segoe UI', system-ui, sans-serif" font-size="13" font-weight="500">{hours:.1f}h {star}</text>''')
        
        svg_parts.append(f'''
  <text x="{bar_x + bar_width/2}" y="{height - 20}" text-anchor="middle" fill="{secondary_text}" font-family="'Segoe UI', system-ui, sans-serif" font-size="12" font-weight="500">{label}</text>''')
    
    svg_parts.append('''
</svg>''')
    
    return "".join(svg_parts)


def generate_featured_project_svg(repo_info: Dict, theme: str = "dark", index: int = 0) -> str:
    """Generate a featured project card SVG."""
    if theme == "dark":
        bg_color = "#0d1117"
        card_bg = "#161b22"
        text_color = "#e6edf3"
        secondary_text = "#8b949e"
        border_color = "#30363d"
        accent_color = "#58a6ff"
    else:
        bg_color = "#ffffff"
        card_bg = "#f6f8fa"
        text_color = "#1f2328"
        secondary_text = "#656d76"
        border_color = "#d0d7de"
        accent_color = "#0969da"
    
    # Language colors
    lang_colors = {
        "JavaScript": "#f1e05a",
        "TypeScript": "#3178c6",
        "Python": "#3572A5",
        "Java": "#b07219",
        "C++": "#f34b7d",
        "C": "#555555",
        "HTML": "#e34c26",
        "CSS": "#563d7c",
        "Kotlin": "#A97BFF",
        "Go": "#00ADD8",
        "Rust": "#dea584",
        "Ruby": "#701516",
        "PHP": "#4F5D95",
        "Shell": "#89e051",
        "Swift": "#F05138",
        "Jupyter Notebook": "#DA5B0B",
    }
    
    name = repo_info.get("name", "Repository")
    description = repo_info.get("description", "No description")[:100]
    if len(repo_info.get("description", "")) > 100:
        description += "..."
    language = repo_info.get("language", "")
    stars = repo_info.get("stars", 0)
    forks = repo_info.get("forks", 0)
    lang_color = lang_colors.get(language, "#8b949e")
    
    width = 400
    height = 150
    
    # Split description for multiline
    desc_line1 = description[:50] if len(description) > 0 else ""
    desc_line2 = description[50:] if len(description) > 50 else ""
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>
    <linearGradient id="cardGrad{index}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{card_bg};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{bg_color};stop-opacity:1" />
    </linearGradient>
    <filter id="shadow{index}" x="-10%" y="-10%" width="120%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="8" flood-opacity="0.15"/>
    </filter>
  </defs>
  
  <rect width="{width}" height="{height}" fill="{bg_color}" rx="12" ry="12"/>
  <rect x="4" y="4" width="{width-8}" height="{height-8}" fill="url(#cardGrad{index})" rx="10" ry="10" stroke="{border_color}" stroke-width="1" filter="url(#shadow{index})"/>
  
  <!-- Repo Icon -->
  <g transform="translate(20, 20)">
    <path fill="{secondary_text}" d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z" transform="scale(1.2)"/>
  </g>
  
  <!-- Repo Name -->
  <text x="50" y="35" fill="{accent_color}" font-family="'Segoe UI', system-ui, sans-serif" font-size="16" font-weight="600">{name}</text>
  
  <!-- Description -->
  <text x="20" y="60" fill="{secondary_text}" font-family="'Segoe UI', system-ui, sans-serif" font-size="12">{desc_line1}</text>
  <text x="20" y="76" fill="{secondary_text}" font-family="'Segoe UI', system-ui, sans-serif" font-size="12">{desc_line2}</text>
  
  <!-- Footer Stats -->
  <g transform="translate(20, {height - 30})">
    <!-- Language -->
    <circle cx="6" cy="6" r="6" fill="{lang_color}"/>
    <text x="18" y="10" fill="{secondary_text}" font-family="'Segoe UI', system-ui, sans-serif" font-size="12">{language}</text>
    
    <!-- Stars -->
    <g transform="translate(120, 0)">
      <path fill="{secondary_text}" d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z" transform="scale(0.85)"/>
      <text x="18" y="10" fill="{secondary_text}" font-family="'Segoe UI', system-ui, sans-serif" font-size="12">{stars}</text>
    </g>
    
    <!-- Forks -->
    <g transform="translate(180, 0)">
      <path fill="{secondary_text}" d="M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z" transform="scale(0.85)"/>
      <text x="18" y="10" fill="{secondary_text}" font-family="'Segoe UI', system-ui, sans-serif" font-size="12">{forks}</text>
    </g>
  </g>
</svg>'''
    
    return svg


def logarithmic_progress(value: float, max_val: float, min_display: float = 0.25) -> float:
    """
    Calculate logarithmic progress to make low values appear more substantial.
    Returns a value between min_display and 1.0.
    """
    if value <= 0:
        return min_display
    if max_val <= 0:
        return 1.0
    
    # Use logarithmic scale: log(value + 1) / log(max + 1)
    # This makes the progress fill up faster for lower values
    progress = math.log(value + 1) / math.log(max_val + 1)
    
    # Ensure minimum display of 25% for any non-zero value
    return min_display + (1 - min_display) * progress


def generate_trophies_svg(stats: Dict, theme: str = "dark") -> str:
    """Generate GitHub trophies SVG with logarithmic progress (no letter grades)."""
    if theme == "dark":
        bg_color = "#0d1117"
        text_color = "#e6edf3"
        secondary_text = "#8b949e"
        border_color = "#30363d"
        card_bg = "#161b22"
    else:
        bg_color = "#ffffff"
        text_color = "#1f2328"
        secondary_text = "#656d76"
        border_color = "#d0d7de"
        card_bg = "#f6f8fa"
    
    # Trophy definitions with max reference values (for logarithmic scaling)
    trophies_config = [
        {
            "name": "Stars",
            "icon": "⭐",
            "value": stats.get("total_stars", 0),
            "max_ref": 100,  # Reference max for log scale
            "gradient": ("ffd700", "ff8c00"),
            "accent": "#ffd700"
        },
        {
            "name": "Commits",
            "icon": "📝",
            "value": stats.get("total_commits", 0),
            "max_ref": 500,
            "gradient": ("4CAF50", "2E7D32"),
            "accent": "#4CAF50"
        },
        {
            "name": "PRs",
            "icon": "🔀",
            "value": stats.get("total_prs", 0),
            "max_ref": 50,
            "gradient": ("9C27B0", "6A1B9A"),
            "accent": "#9C27B0"
        },
        {
            "name": "Issues",
            "icon": "❗",
            "value": stats.get("total_issues", 0),
            "max_ref": 50,
            "gradient": ("FF5722", "E64A19"),
            "accent": "#FF5722"
        },
        {
            "name": "Repos",
            "icon": "📁",
            "value": stats.get("total_repos", 0),
            "max_ref": 30,
            "gradient": ("2196F3", "1565C0"),
            "accent": "#2196F3"
        },
        {
            "name": "Followers",
            "icon": "👥",
            "value": stats.get("followers", 0),
            "max_ref": 100,
            "gradient": ("00BCD4", "0097A7"),
            "accent": "#00BCD4"
        },
        {
            "name": "Experience",
            "icon": "🏅",
            "value": stats.get("account_age_years", 0),
            "max_ref": 10,
            "gradient": ("E91E63", "C2185B"),
            "accent": "#E91E63"
        },
        {
            "name": "Activity",
            "icon": "🔥",
            "value": stats.get("total_contributions", 0),
            "max_ref": 500,
            "gradient": ("FF9800", "F57C00"),
            "accent": "#FF9800"
        }
    ]
    
    trophy_width = 120
    trophy_height = 120
    cols = 4
    rows = 2
    padding = 10
    
    width = cols * trophy_width + (cols + 1) * padding
    height = rows * trophy_height + (rows + 1) * padding
    
    svg_parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>''']
    
    # Add gradients for each trophy
    for i, trophy in enumerate(trophies_config):
        c1, c2 = trophy["gradient"]
        svg_parts.append(f'''
    <linearGradient id="tGrad{i}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#{c1};stop-opacity:1" />
      <stop offset="100%" style="stop-color:#{c2};stop-opacity:1" />
    </linearGradient>
    <filter id="glow{i}" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>''')
    
    svg_parts.append(f'''
  </defs>
  <rect width="{width}" height="{height}" fill="{bg_color}" rx="12" ry="12"/>''')
    
    for idx, trophy in enumerate(trophies_config):
        row = idx // cols
        col = idx % cols
        x = col * trophy_width + (col + 1) * padding
        y = row * trophy_height + (row + 1) * padding
        
        # Calculate logarithmic progress
        progress = logarithmic_progress(trophy["value"], trophy["max_ref"])
        progress_width = int((trophy_width - 20) * progress)
        
        # Trophy card
        svg_parts.append(f'''
  <g transform="translate({x}, {y})">
    <rect width="{trophy_width}" height="{trophy_height}" fill="{card_bg}" stroke="{border_color}" stroke-width="1" rx="10" ry="10"/>
    
    <!-- Trophy Icon with glow -->
    <text x="{trophy_width/2}" y="40" text-anchor="middle" font-size="32" filter="url(#glow{idx})">{trophy["icon"]}</text>
    
    <!-- Trophy Name -->
    <text x="{trophy_width/2}" y="68" text-anchor="middle" fill="{text_color}" font-family="'Segoe UI', system-ui, sans-serif" font-size="12" font-weight="600">{trophy["name"]}</text>
    
    <!-- Value with accent color -->
    <text x="{trophy_width/2}" y="86" text-anchor="middle" fill="{trophy['accent']}" font-family="'Segoe UI', system-ui, sans-serif" font-size="14" font-weight="bold">{trophy["value"]}</text>
    
    <!-- Progress bar background -->
    <rect x="10" y="{trophy_height - 20}" width="{trophy_width - 20}" height="8" fill="{border_color}" rx="4" ry="4"/>
    
    <!-- Progress bar fill with animation -->
    <rect x="10" y="{trophy_height - 20}" width="{progress_width}" height="8" fill="url(#tGrad{idx})" rx="4" ry="4">
      <animate attributeName="width" from="0" to="{progress_width}" dur="1.2s" fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1"/>
    </rect>
    
    <!-- Shimmer effect -->
    <rect x="10" y="{trophy_height - 20}" width="{progress_width}" height="8" fill="url(#tGrad{idx})" rx="4" ry="4" opacity="0.3">
      <animate attributeName="opacity" values="0.3;0.6;0.3" dur="2s" repeatCount="indefinite"/>
    </rect>
  </g>''')
    
    svg_parts.append('''
</svg>''')
    
    return "".join(svg_parts)


def generate_contribution_graph_svg(contributions: Dict[str, int], theme: str = "dark") -> str:
    """Generate a modern, highly animated contribution graph SVG."""
    if theme == "dark":
        bg_color = "#0d1117"
        text_color = "#e6edf3"
        secondary_text = "#8b949e"
        border_color = "#30363d"
        empty_color = "#161b22"
        # Modern gradient levels
        level_colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
        glow_color = "#39d353"
    else:
        bg_color = "#ffffff"
        text_color = "#1f2328"
        secondary_text = "#656d76"
        border_color = "#d0d7de"
        empty_color = "#ebedf0"
        level_colors = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
        glow_color = "#216e39"
    
    # Calculate dimensions
    cell_size = 11
    cell_gap = 3
    weeks = 53
    days = 7
    
    left_padding = 45
    top_padding = 50
    right_padding = 30
    bottom_padding = 50
    
    width = left_padding + weeks * (cell_size + cell_gap) + right_padding
    height = top_padding + days * (cell_size + cell_gap) + bottom_padding
    
    # Generate dates for last 52 weeks
    today = datetime.now(timezone.utc).date()
    days_since_sunday = today.weekday() + 1
    if days_since_sunday == 7:
        days_since_sunday = 0
    end_date = today
    start_date = end_date - timedelta(days=364)
    
    svg_parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>
    <!-- Glow filter for active cells -->
    <filter id="cellGlow" x="-100%" y="-100%" width="300%" height="300%">
      <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    
    <!-- Gradient for title -->
    <linearGradient id="titleGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:{level_colors[2]};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{level_colors[4]};stop-opacity:1" />
    </linearGradient>
    
    <!-- Animated shimmer -->
    <linearGradient id="shimmer" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:transparent"/>
      <stop offset="50%" style="stop-color:rgba(255,255,255,0.15)"/>
      <stop offset="100%" style="stop-color:transparent"/>
      <animate attributeName="x1" values="-100%;100%" dur="3s" repeatCount="indefinite"/>
      <animate attributeName="x2" values="0%;200%" dur="3s" repeatCount="indefinite"/>
    </linearGradient>
    
    <!-- Pulse animation for legend -->
    <filter id="pulse">
      <feGaussianBlur in="SourceGraphic" stdDeviation="1"/>
    </filter>''']
    
    # Add level gradients
    for i, color in enumerate(level_colors[1:], 1):
        svg_parts.append(f'''
    <radialGradient id="levelGrad{i}" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:{color};stop-opacity:1"/>
      <stop offset="100%" style="stop-color:{color};stop-opacity:0.7"/>
    </radialGradient>''')
    
    svg_parts.append(f'''
  </defs>
  
  <!-- Background -->
  <rect width="{width}" height="{height}" fill="{bg_color}" rx="16" ry="16"/>
  <rect x="1" y="1" width="{width-2}" height="{height-2}" fill="none" stroke="{border_color}" stroke-width="1" rx="15" ry="15"/>
  
  <!-- Title -->
  <text x="{left_padding}" y="28" fill="url(#titleGrad)" font-family="'Segoe UI', system-ui, sans-serif" font-size="14" font-weight="700">
    Contribution Activity
    <animate attributeName="opacity" values="0.8;1;0.8" dur="3s" repeatCount="indefinite"/>
  </text>''')
    
    # Day labels with icons
    day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    for i in [1, 3, 5]:  # Only show Mon, Wed, Fri
        y = top_padding + i * (cell_size + cell_gap) + cell_size / 2 + 4
        svg_parts.append(f'''
  <text x="{left_padding - 10}" y="{y}" text-anchor="end" fill="{secondary_text}" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" font-weight="500">{day_labels[i]}</text>''')
    
    # Month labels
    current_date = start_date
    prev_month = None
    for week in range(weeks):
        month_name = current_date.strftime("%b")
        if month_name != prev_month:
            x = left_padding + week * (cell_size + cell_gap)
            svg_parts.append(f'''
  <text x="{x}" y="{top_padding - 10}" fill="{secondary_text}" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" font-weight="500">{month_name}</text>''')
            prev_month = month_name
        current_date += timedelta(days=7)
    
    # Calculate max for color levels
    max_contrib = max(contributions.values()) if contributions else 1
    max_contrib = max(max_contrib, 1)
    
    # Draw contribution cells with animations
    current_date = start_date
    cell_index = 0
    
    for week in range(weeks):
        for day in range(days):
            date_str = current_date.strftime("%Y-%m-%d")
            count = contributions.get(date_str, 0)
            
            # Determine color level
            if count == 0:
                level = 0
                color = level_colors[0]
            elif count <= max_contrib * 0.25:
                level = 1
                color = level_colors[1]
            elif count <= max_contrib * 0.5:
                level = 2
                color = level_colors[2]
            elif count <= max_contrib * 0.75:
                level = 3
                color = level_colors[3]
            else:
                level = 4
                color = level_colors[4]
            
            x = left_padding + week * (cell_size + cell_gap)
            y = top_padding + day * (cell_size + cell_gap)
            
            # Staggered animation delay
            delay = (week * 0.02) + (day * 0.01)
            
            # Add hover target rect (invisible)
            svg_parts.append(f'''
  <g class="cell" data-date="{date_str}" data-count="{count}">''')
            
            if level > 0:
                # Active cell with glow and animation
                svg_parts.append(f'''
    <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="{color}" rx="2" ry="2" opacity="0">
      <animate attributeName="opacity" from="0" to="1" dur="0.4s" begin="{delay:.2f}s" fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1"/>
      <animate attributeName="rx" values="2;3;2" dur="2s" begin="{delay + 0.5:.2f}s" repeatCount="indefinite"/>
    </rect>
    <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="url(#shimmer)" rx="2" ry="2" opacity="0">
      <animate attributeName="opacity" from="0" to="0.3" dur="0.4s" begin="{delay:.2f}s" fill="freeze"/>
    </rect>''')
            else:
                # Empty cell
                svg_parts.append(f'''
    <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="{color}" rx="2" ry="2" opacity="0">
      <animate attributeName="opacity" from="0" to="1" dur="0.3s" begin="{delay:.2f}s" fill="freeze"/>
    </rect>''')
            
            # Tooltip
            svg_parts.append(f'''
    <title>{date_str}: {count} contribution{"s" if count != 1 else ""}</title>
  </g>''')
            
            current_date += timedelta(days=1)
            cell_index += 1
    
    # Animated legend
    legend_x = width - 180
    legend_y = height - 25
    
    svg_parts.append(f'''
  <!-- Legend with pulse animation -->
  <g transform="translate({legend_x}, {legend_y})">
    <text x="-35" y="9" fill="{secondary_text}" font-family="'Segoe UI', system-ui, sans-serif" font-size="10">Less</text>''')
    
    for i, color in enumerate(level_colors):
        svg_parts.append(f'''
    <rect x="{i * 15}" y="0" width="{cell_size}" height="{cell_size}" fill="{color}" rx="2" ry="2">
      <animate attributeName="opacity" values="0.7;1;0.7" dur="2s" begin="{i * 0.2}s" repeatCount="indefinite"/>
    </rect>''')
    
    svg_parts.append(f'''
    <text x="{5 * 15 + 8}" y="9" fill="{secondary_text}" font-family="'Segoe UI', system-ui, sans-serif" font-size="10">More</text>
  </g>''')
    
    # Total contributions counter with animated number
    total = sum(contributions.values())
    svg_parts.append(f'''
  <!-- Contribution count -->
  <g transform="translate({left_padding}, {height - 18})">
    <text fill="{text_color}" font-family="'Segoe UI', system-ui, sans-serif" font-size="12" font-weight="600">
      <tspan fill="{level_colors[4]}">{total}</tspan> contributions in the last year
    </text>
  </g>''')
    
    svg_parts.append('''
</svg>''')
    
    return "".join(svg_parts)


def generate_all_featured_projects_svg(repos_info: List[Dict], theme: str = "dark") -> str:
    """Generate a combined SVG with all featured projects in a grid."""
    if not repos_info:
        return ""
    
    if theme == "dark":
        bg_color = "#0d1117"
        border_color = "#30363d"
    else:
        bg_color = "#ffffff"
        border_color = "#d0d7de"
    
    # Layout: 2 columns, as many rows as needed
    card_width = 400
    card_height = 150
    cols = 2
    gap = 20
    padding = 20
    
    rows = (len(repos_info) + cols - 1) // cols
    
    width = padding * 2 + cols * card_width + (cols - 1) * gap
    height = padding * 2 + rows * card_height + (rows - 1) * gap
    
    svg_parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <rect width="{width}" height="{height}" fill="{bg_color}" rx="16" ry="16"/>
  <rect x="1" y="1" width="{width-2}" height="{height-2}" fill="none" stroke="{border_color}" stroke-width="1" rx="15" ry="15"/>''']
    
    for idx, repo_info in enumerate(repos_info):
        row = idx // cols
        col = idx % cols
        x = padding + col * (card_width + gap)
        y = padding + row * (card_height + gap)
        
        # Generate individual card SVG and embed it
        card_svg = generate_featured_project_svg(repo_info, theme, idx)
        
        # Remove the outer SVG tags and embed as a group
        card_content = card_svg.split('>', 1)[1].rsplit('</svg>', 1)[0]
        
        svg_parts.append(f'''
  <g transform="translate({x}, {y})">
    {card_content}
  </g>''')
    
    svg_parts.append('''
</svg>''')
    
    return "".join(svg_parts)


# ============================================================
# FEATURED PROJECT CONFIG
# ============================================================

def load_featured_projects_config() -> List[str]:
    """Load featured projects configuration from data/featured-projects.json."""
    config_path = Path(os.getcwd()) / "data" / "featured-projects.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("repo_urls", [])
    
    # Fallback to old single-project config
    old_config_path = Path(os.getcwd()) / "data" / "featured-project.json"
    if old_config_path.exists():
        with open(old_config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            url = data.get("repo_url", "")
            return [url] if url else []
    
    return []


def save_featured_projects_config(urls: List[str]):
    """Save featured projects configuration."""
    data_dir = Path(os.getcwd()) / "data"
    data_dir.mkdir(exist_ok=True)
    config_path = data_dir / "featured-projects.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"repo_urls": urls}, f, indent=2)


# ============================================================
# MAIN FUNCTION
# ============================================================

def main():
    """Main function to generate all SVG assets."""
    workspace_root = Path(os.getcwd())
    stats_file = workspace_root / "wakatime_stats.json"
    assets_dir = workspace_root / "assets"
    data_dir = workspace_root / "data"
    
    assets_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)
    
    # Load WakaTime stats
    if stats_file.exists():
        with open(stats_file, "r", encoding="utf-8") as f:
            wakatime_stats = json.load(f)
        print(f"✅ Loaded WakaTime stats from {stats_file}")
    else:
        print(f"⚠️ WakaTime stats file not found, using defaults")
        wakatime_stats = {
            "daily_hours": [0] * 7,
            "daily_labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        }
    
    # Generate weekly activity SVGs
    print("\n📊 Generating weekly activity charts...")
    for theme in ["dark", "light"]:
        svg = generate_weekly_activity_svg(wakatime_stats, theme)
        svg_file = assets_dir / f"weekly-activity-{theme}.svg"
        with open(svg_file, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"  ✅ Generated {svg_file.name}")
    
    # Fetch GitHub stats
    print("\n🔍 Fetching GitHub stats...")
    github_stats = get_user_stats()
    print(f"  📊 Total stars: {github_stats['total_stars']}")
    print(f"  📊 Total repos: {github_stats['total_repos']}")
    print(f"  📊 Followers: {github_stats['followers']}")
    print(f"  📊 PRs: {github_stats['total_prs']}")
    print(f"  📊 Issues: {github_stats['total_issues']}")
    print(f"  📊 Commits: {github_stats['total_commits']}")
    
    # Save GitHub stats for README updates
    github_stats_file = data_dir / "github-stats.json"
    stats_to_save = {k: v for k, v in github_stats.items() if k != "contributions"}
    stats_to_save["contribution_days"] = len(github_stats.get("contributions", {}))
    with open(github_stats_file, "w", encoding="utf-8") as f:
        json.dump(stats_to_save, f, indent=2)
    print(f"  ✅ Saved GitHub stats to {github_stats_file.name}")
    
    # Generate trophies SVGs
    print("\n🏆 Generating GitHub trophies (logarithmic progress)...")
    for theme in ["dark", "light"]:
        svg = generate_trophies_svg(github_stats, theme)
        svg_file = assets_dir / f"github-trophies-{theme}.svg"
        with open(svg_file, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"  ✅ Generated {svg_file.name}")
    
    # Generate contribution graph
    print("\n📈 Generating modern contribution graph...")
    contributions = github_stats.get("contributions", {})
    print(f"  📊 Found {len(contributions)} days with contributions")
    
    for theme in ["dark", "light"]:
        svg = generate_contribution_graph_svg(contributions, theme)
        svg_file = assets_dir / f"contribution-graph-{theme}.svg"
        with open(svg_file, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"  ✅ Generated {svg_file.name}")
    
    # Generate featured project SVGs (multiple projects)
    print("\n🎯 Generating featured project cards...")
    repo_urls = load_featured_projects_config()
    
    if not repo_urls:
        # Create default config with all projects
        repo_urls = [
            "https://github.com/ARPANPATRA111/AtMark",
            "https://github.com/ARPANPATRA111/TripBudget",
            "https://github.com/ARPANPATRA111/Fitness-Dashboard",
            "https://github.com/ARPANPATRA111/Float-Chat",
            "https://github.com/ARPANPATRA111/MOB-APP",
            "https://github.com/ARPANPATRA111/Medix-manager"
        ]
        save_featured_projects_config(repo_urls)
        print(f"  📝 Created featured projects config with {len(repo_urls)} repos")
    
    # Fetch info for all repos
    repos_info = []
    for idx, repo_url in enumerate(repo_urls):
        match = re.match(r"https://github\.com/([^/]+)/([^/]+)/?", repo_url)
        if match:
            owner, repo_name = match.groups()
            repo_info = get_repo_info(owner, repo_name)
            if repo_info:
                repos_info.append(repo_info)
                print(f"  ✅ Fetched info for {repo_name}")
                
                # Generate individual project card
                for theme in ["dark", "light"]:
                    svg = generate_featured_project_svg(repo_info, theme, idx)
                    svg_file = assets_dir / f"featured-project-{idx}-{theme}.svg"
                    with open(svg_file, "w", encoding="utf-8") as f:
                        f.write(svg)
            else:
                print(f"  ⚠️ Could not fetch info for {repo_url}")
        else:
            print(f"  ⚠️ Invalid repo URL format: {repo_url}")
    
    # Generate combined grid SVG
    if repos_info:
        print("\n📦 Generating combined featured projects grid...")
        for theme in ["dark", "light"]:
            svg = generate_all_featured_projects_svg(repos_info, theme)
            svg_file = assets_dir / f"featured-projects-grid-{theme}.svg"
            with open(svg_file, "w", encoding="utf-8") as f:
                f.write(svg)
            print(f"  ✅ Generated {svg_file.name}")
        
        # Save all repos info
        repos_info_file = data_dir / "featured-projects-info.json"
        with open(repos_info_file, "w", encoding="utf-8") as f:
            json.dump(repos_info, f, indent=2)
        print(f"  ✅ Saved all featured projects info")
        
        # Also generate single featured project (first one) for backward compatibility
        for theme in ["dark", "light"]:
            svg = generate_featured_project_svg(repos_info[0], theme, 0)
            svg_file = assets_dir / f"featured-project-{theme}.svg"
            with open(svg_file, "w", encoding="utf-8") as f:
                f.write(svg)
    
    print("\n🎉 All assets generated successfully!")


if __name__ == "__main__":
    main()
