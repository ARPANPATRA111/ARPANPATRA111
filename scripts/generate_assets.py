#!/usr/bin/env python3
"""
Generate SVG assets for GitHub Profile README
This script generates theme-aware SVG files for stats, tech stack, etc.
"""

import os
import json
import requests
from datetime import datetime

# Environment variables
GH_TOKEN = os.environ.get('GH_TOKEN', '')
WAKATIME_API_KEY = os.environ.get('WAKATIME_API_KEY', '')
USERNAME = os.environ.get('USERNAME', 'ARPANPATRA111')

# Color schemes
DARK_THEME = {
    'bg': '#0d1117',
    'card_bg': '#161b22',
    'border': '#30363d',
    'text': '#c9d1d9',
    'text_secondary': '#8b949e',
    'accent': '#58a6ff',
    'accent_secondary': '#7ee787'
}

LIGHT_THEME = {
    'bg': '#ffffff',
    'card_bg': '#f6f8fa',
    'border': '#d0d7de',
    'text': '#24292f',
    'text_secondary': '#57606a',
    'accent': '#0969da',
    'accent_secondary': '#1a7f37'
}


def get_wakatime_stats():
    """Fetch WakaTime stats"""
    if not WAKATIME_API_KEY:
        return None
    
    try:
        url = f'https://wakatime.com/api/v1/users/current/stats/last_7_days'
        headers = {'Authorization': f'Basic {WAKATIME_API_KEY}'}
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json().get('data', {})
    except Exception as e:
        print(f"Error fetching WakaTime stats: {e}")
    return None


def get_github_stats():
    """Fetch GitHub stats"""
    stats = {
        'followers': 0,
        'total_stars': 0,
        'public_repos': 0
    }
    
    if not GH_TOKEN:
        return stats
    
    headers = {
        'Authorization': f'token {GH_TOKEN}',
        'Accept': 'application/vnd.github+json'
    }
    
    try:
        # Get user info
        user_response = requests.get(
            f'https://api.github.com/users/{USERNAME}',
            headers=headers,
            timeout=30
        )
        if user_response.status_code == 200:
            user_data = user_response.json()
            stats['followers'] = user_data.get('followers', 0)
            stats['public_repos'] = user_data.get('public_repos', 0)
        
        # Get total stars
        page = 1
        total_stars = 0
        while True:
            repos_response = requests.get(
                f'https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}',
                headers=headers,
                timeout=30
            )
            if repos_response.status_code != 200:
                break
            repos = repos_response.json()
            if not repos:
                break
            for repo in repos:
                total_stars += repo.get('stargazers_count', 0)
            page += 1
        stats['total_stars'] = total_stars
        
    except Exception as e:
        print(f"Error fetching GitHub stats: {e}")
    
    return stats


def generate_header_svg(theme, theme_name):
    """Generate header SVG"""
    colors = DARK_THEME if theme_name == 'dark' else LIGHT_THEME
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="200" viewBox="0 0 800 200">
  <defs>
    <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#667eea"/>
      <stop offset="50%" style="stop-color:#764ba2"/>
      <stop offset="100%" style="stop-color:#f093fb"/>
    </linearGradient>
  </defs>
  <rect width="800" height="200" fill="{colors['bg']}"/>
  <text x="400" y="80" font-family="Segoe UI, Arial, sans-serif" font-size="42" font-weight="bold" fill="url(#headerGrad)" text-anchor="middle">Hi 👋, I'm Arpan Patra</text>
  <text x="400" y="130" font-family="Segoe UI, Arial, sans-serif" font-size="20" fill="{colors['text_secondary']}" text-anchor="middle">Full Stack Developer | Open Source Enthusiast | Tech Explorer</text>
  <text x="400" y="170" font-family="Segoe UI, Arial, sans-serif" font-size="16" fill="{colors['text_secondary']}" text-anchor="middle">🚀 Building the future, one commit at a time</text>
</svg>'''
    return svg


def generate_footer_svg(theme_name):
    """Generate footer SVG"""
    colors = DARK_THEME if theme_name == 'dark' else LIGHT_THEME
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="100" viewBox="0 0 800 100">
  <rect width="800" height="100" fill="{colors['bg']}"/>
  <text x="400" y="40" font-family="Segoe UI, Arial, sans-serif" font-size="18" fill="{colors['text_secondary']}" text-anchor="middle">Thanks for visiting! 🙏</text>
  <text x="400" y="70" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{colors['text_secondary']}" text-anchor="middle">⭐ Star my repos if you find them useful!</text>
</svg>'''
    return svg


def generate_weekly_activity_svg(theme_name, wakatime_data=None):
    """Generate weekly activity chart SVG"""
    colors = DARK_THEME if theme_name == 'dark' else LIGHT_THEME
    
    # Default data if WakaTime not available
    days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    hours = [0] * 7
    
    if wakatime_data and 'days' in wakatime_data:
        for i, day_data in enumerate(wakatime_data.get('days', [])[:7]):
            hours[i] = day_data.get('grand_total', {}).get('hours', 0)
    
    max_hours = max(hours) if max(hours) > 0 else 8
    bar_colors = ['#ff6b6b', '#feca57', '#48dbfb', '#ff9ff3', '#54a0ff', '#5f27cd', '#00d2d3']
    
    bars_svg = ''
    for i, (day, hour) in enumerate(zip(days, hours)):
        bar_height = (hour / max_hours) * 120 if max_hours > 0 else 0
        x = 80 + i * 100
        bars_svg += f'''
    <rect x="{x}" y="{180 - bar_height}" width="60" height="{bar_height}" rx="5" fill="{bar_colors[i]}" opacity="0.8"/>
    <text x="{x + 30}" y="200" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="{colors['text_secondary']}" text-anchor="middle">{day}</text>
    <text x="{x + 30}" y="{170 - bar_height}" font-family="Segoe UI, Arial, sans-serif" font-size="11" fill="{colors['text']}" text-anchor="middle">{hour:.1f}h</text>'''
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="220" viewBox="0 0 800 220">
  <rect width="800" height="220" fill="{colors['bg']}" rx="10"/>
  <text x="400" y="30" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="bold" fill="{colors['text']}" text-anchor="middle">📈 Weekly Coding Activity</text>
  {bars_svg}
</svg>'''
    return svg


def generate_tech_stack_line_svg(theme_name, line_num, techs):
    """Generate animated tech stack line SVG"""
    colors = DARK_THEME if theme_name == 'dark' else LIGHT_THEME
    direction = 'normal' if line_num % 2 == 1 else 'reverse'
    
    # Double the techs for seamless loop
    all_techs = techs + techs
    
    items_svg = ''
    x = 0
    for tech in all_techs:
        items_svg += f'''
      <g transform="translate({x}, 0)">
        <rect width="100" height="30" rx="15" fill="{colors['card_bg']}" stroke="{colors['border']}" stroke-width="1"/>
        <text x="50" y="20" font-family="Segoe UI, Arial, sans-serif" font-size="11" fill="{colors['text']}" text-anchor="middle">{tech}</text>
      </g>'''
        x += 110
    
    total_width = len(techs) * 110
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="50" viewBox="0 0 800 50">
  <defs>
    <clipPath id="clip{line_num}{theme_name}">
      <rect width="800" height="50"/>
    </clipPath>
  </defs>
  <rect width="800" height="50" fill="{colors['bg']}"/>
  <g clip-path="url(#clip{line_num}{theme_name})">
    <g transform="translate(0, 10)">
      <animateTransform attributeName="transform" type="translate" 
        from="0 10" to="-{total_width} 10" dur="20s" repeatCount="indefinite" 
        direction="{direction}"/>
      {items_svg}
    </g>
  </g>
</svg>'''
    return svg


def generate_github_stats_svg(theme_name, stats):
    """Generate GitHub stats SVG"""
    colors = DARK_THEME if theme_name == 'dark' else LIGHT_THEME
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="200" viewBox="0 0 800 200">
  <rect width="800" height="200" fill="{colors['bg']}" rx="10"/>
  <text x="400" y="40" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="bold" fill="{colors['text']}" text-anchor="middle">📊 GitHub Statistics</text>
  
  <g transform="translate(100, 70)">
    <rect width="180" height="80" rx="10" fill="{colors['card_bg']}" stroke="{colors['border']}"/>
    <text x="90" y="35" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="bold" fill="{colors['accent']}" text-anchor="middle">{stats.get('followers', 0)}</text>
    <text x="90" y="60" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{colors['text_secondary']}" text-anchor="middle">Followers</text>
  </g>
  
  <g transform="translate(310, 70)">
    <rect width="180" height="80" rx="10" fill="{colors['card_bg']}" stroke="{colors['border']}"/>
    <text x="90" y="35" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="bold" fill="#feca57" text-anchor="middle">{stats.get('total_stars', 0)}</text>
    <text x="90" y="60" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{colors['text_secondary']}" text-anchor="middle">Total Stars</text>
  </g>
  
  <g transform="translate(520, 70)">
    <rect width="180" height="80" rx="10" fill="{colors['card_bg']}" stroke="{colors['border']}"/>
    <text x="90" y="35" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="bold" fill="{colors['accent_secondary']}" text-anchor="middle">{stats.get('public_repos', 0)}</text>
    <text x="90" y="60" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{colors['text_secondary']}" text-anchor="middle">Repositories</text>
  </g>
</svg>'''
    return svg


def generate_trophies_svg(theme_name):
    """Generate GitHub trophies SVG"""
    colors = DARK_THEME if theme_name == 'dark' else LIGHT_THEME
    
    trophies = [
        ('🏆', 'Commits', '#feca57'),
        ('⭐', 'Stars', '#ff6b6b'),
        ('👥', 'Followers', '#48dbfb'),
        ('📦', 'Repos', '#ff9ff3'),
        ('🔥', 'Streak', '#54a0ff'),
        ('💻', 'PRs', '#5f27cd')
    ]
    
    trophy_items = ''
    for i, (emoji, label, color) in enumerate(trophies):
        x = 40 + (i % 6) * 120
        trophy_items += f'''
    <g transform="translate({x}, 60)">
      <rect width="100" height="80" rx="10" fill="{colors['card_bg']}" stroke="{color}" stroke-width="2"/>
      <text x="50" y="40" font-size="28" text-anchor="middle">{emoji}</text>
      <text x="50" y="65" font-family="Segoe UI, Arial, sans-serif" font-size="11" fill="{colors['text']}" text-anchor="middle">{label}</text>
    </g>'''
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="160" viewBox="0 0 800 160">
  <rect width="800" height="160" fill="{colors['bg']}" rx="10"/>
  <text x="400" y="35" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="bold" fill="{colors['text']}" text-anchor="middle">🏆 Achievement Trophies</text>
  {trophy_items}
</svg>'''
    return svg


def save_svg(content, filename):
    """Save SVG content to file"""
    os.makedirs('assets', exist_ok=True)
    filepath = os.path.join('assets', filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Generated: {filepath}")


def main():
    print("🚀 Starting asset generation...")
    
    # Fetch data
    github_stats = get_github_stats()
    wakatime_data = get_wakatime_stats()
    
    print(f"GitHub Stats: {github_stats}")
    
    # Generate SVGs for both themes (only headers, footers, and weekly activity)
    for theme in ['dark', 'light']:
        # Header and Footer
        save_svg(generate_header_svg(theme, theme), f'header-{theme}.svg')
        save_svg(generate_footer_svg(theme), f'footer-{theme}.svg')
        
        # Weekly Activity
        save_svg(generate_weekly_activity_svg(theme, wakatime_data), f'weekly-activity-{theme}.svg')
    
    # Save stats to JSON
    with open('wakatime_stats.json', 'w') as f:
        json.dump({
            'github_stats': github_stats,
            'updated_at': datetime.utcnow().isoformat()
        }, f, indent=2)
    
    print("✅ Asset generation complete!")


if __name__ == '__main__':
    main()
