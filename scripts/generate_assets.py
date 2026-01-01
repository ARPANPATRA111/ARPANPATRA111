#!/usr/bin/env python3
"""
Generate SVG assets for GitHub Profile README
This script generates theme-aware SVG files for stats, tech stack, etc.
"""

import os
import json
import requests
import base64
from datetime import datetime, timedelta, timezone

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
        # Calculate dates for last 7 days
        today_utc = datetime.now(timezone.utc).date()
        start_date = (today_utc - timedelta(days=6)).strftime('%Y-%m-%d')
        end_date = today_utc.strftime('%Y-%m-%d')
        
        url = f'https://wakatime.com/api/v1/users/current/summaries?start={start_date}&end={end_date}'
        
        # Encode API key for Basic Auth
        encoded_key = base64.b64encode(WAKATIME_API_KEY.encode()).decode()
        headers = {'Authorization': f'Basic {encoded_key}'}
        
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            # Return the list of days directly
            return response.json().get('data', [])
        else:
            print(f"Error fetching WakaTime stats: Status {response.status_code}, Response: {response.text}")
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
    
    # Prepare data
    days_data = []
    max_seconds = 0
    
    if wakatime_data and isinstance(wakatime_data, list):
        # Sort by date to ensure chronological order
        sorted_data = sorted(wakatime_data, key=lambda x: x.get('range', {}).get('date', ''))
        # Take last 7 entries
        recent_data = sorted_data[-7:]
        
        for day in recent_data:
            date_str = day.get('range', {}).get('date', '')
            total_seconds = day.get('grand_total', {}).get('total_seconds', 0)
            
            label = 'N/A'
            if date_str:
                try:
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                    label = dt.strftime('%a %d') # e.g., Mon 01
                except:
                    pass
            
            # Format precise time for tooltip
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            time_text = f"{hours}h {minutes}m"
            
            # Format decimal time for display (matching image style)
            decimal_hours = f"{total_seconds/3600:.1f}h"
            
            days_data.append({
                'label': label,
                'seconds': total_seconds,
                'text': decimal_hours,
                'full_text': time_text
            })
            if total_seconds > max_seconds:
                max_seconds = total_seconds
    
    # Fill with placeholders if no data
    if not days_data:
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        for d in days:
            days_data.append({'label': d, 'seconds': 0, 'text': '0.0h', 'full_text': '0h 0m'})
            
    # Find max index for star
    max_idx = -1
    if max_seconds > 0:
        for i, d in enumerate(days_data):
            if d['seconds'] == max_seconds:
                max_idx = i
                break

    # Chart dimensions
    svg_width = 800
    svg_height = 250
    chart_bottom = 210
    bar_width = 60
    gap = 40
    
    # Calculate total width to center
    total_chart_width = len(days_data) * bar_width + (len(days_data) - 1) * gap
    start_x = (svg_width - total_chart_width) / 2
    
    max_val = max_seconds if max_seconds > 0 else 1
    
    # Gradient definitions matching the image style (Vibrant distinct gradients)
    gradient_pairs = [
        ('#FF9966', '#FF5E62'), # 1. Orange -> Red
        ('#F2C94C', '#2F80ED'), # 2. Yellow -> Blue
        ('#DA22FF', '#9733EE'), # 3. Purple -> Blue
        ('#FF512F', '#DD2476'), # 4. Pink -> Red
        ('#FF8008', '#FFC837'), # 5. Orange -> Yellow
        ('#A8FF78', '#78FFD6'), # 6. Green -> Teal
        ('#1FA2FF', '#12D8FA')  # 7. Blue -> Cyan
    ]
    
    # Ensure we have enough gradients
    while len(gradient_pairs) < len(days_data):
        gradient_pairs.append(gradient_pairs[len(gradient_pairs)%7])

    defs = ""
    for i, (start, end) in enumerate(gradient_pairs):
        defs += f'''
    <linearGradient id="grad{i}_{theme_name}" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" style="stop-color:{start};stop-opacity:1" />
        <stop offset="100%" style="stop-color:{end};stop-opacity:1" />
    </linearGradient>'''

    bars_svg = ''
    
    for i, item in enumerate(days_data):
        seconds = item['seconds']
        # Max height 120
        height = (seconds / max_val) * 120
        if height < 4 and seconds > 0: height = 4
        
        x = start_x + i * (bar_width + gap)
        y = chart_bottom - height
        
        # Text above bar
        text_y = y - 8
        
        # Animation
        anim_height = f'''<animate attributeName="height" from="0" to="{height}" dur="1s" fill="freeze" calcMode="spline" keyTimes="0; 1" keySplines="0.42 0 0.58 1" />'''
        anim_y = f'''<animate attributeName="y" from="{chart_bottom}" to="{y}" dur="1s" fill="freeze" calcMode="spline" keyTimes="0; 1" keySplines="0.42 0 0.58 1" />'''
        anim_text_y = f'''<animate attributeName="y" from="{chart_bottom}" to="{text_y}" dur="1s" fill="freeze" calcMode="spline" keyTimes="0; 1" keySplines="0.42 0 0.58 1" />'''
        
        # Label text with star if max
        label_text = item['text']
        if i == max_idx:
             label_text += " ⭐"

        bars_svg += f'''
    <g class="bar-group">
        <rect x="{x}" y="{y}" width="{bar_width}" height="{height}" rx="6" fill="url(#grad{i}_{theme_name})">
            <title>{item['full_text']}</title>
            {anim_height}
            {anim_y}
        </rect>
        <text x="{x + bar_width/2}" y="{chart_bottom + 25}" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="{colors['text_secondary']}" text-anchor="middle">{item['label']}</text>
        
        <text x="{x + bar_width/2}" y="{text_y}" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="bold" fill="{colors['text']}" text-anchor="middle" opacity="0">
            {label_text}
            <animate attributeName="opacity" from="0" to="1" begin="0.8s" dur="0.5s" fill="freeze" />
            {anim_text_y}
        </text>
    </g>'''
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">
  <defs>
    {defs}
  </defs>
  <rect width="{svg_width}" height="{svg_height}" fill="{colors['bg']}" rx="10"/>
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
    print(f"WakaTime Data: {wakatime_data is not None}")
    
    # Generate ONLY weekly activity SVGs for both themes
    # Header and footer SVGs are static and should not be regenerated
    for theme in ['dark', 'light']:
        # Weekly Activity only
        save_svg(generate_weekly_activity_svg(theme, wakatime_data), f'weekly-activity-{theme}.svg')
        print(f"Generated weekly-activity-{theme}.svg")
    
    # Save stats to JSON
    with open('wakatime_stats.json', 'w') as f:
        json.dump({
            'github_stats': github_stats,
            'wakatime_available': wakatime_data is not None,
            'updated_at': datetime.utcnow().isoformat()
        }, f, indent=2)
    
    print("✅ Asset generation complete!")


if __name__ == '__main__':
    main()
