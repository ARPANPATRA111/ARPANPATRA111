#!/usr/bin/env python3
"""
Profile Assets Generator
Generates all SVG assets for the GitHub profile README
Self-hosted - No external API dependencies
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
USERNAME = os.getenv('USERNAME', 'ARPANPATRA111')
GH_TOKEN = os.getenv('GH_TOKEN')
WAKATIME_API_KEY = os.getenv('WAKATIME_API_KEY')
ASSETS_DIR = Path('assets')

# Ensure assets directory exists
ASSETS_DIR.mkdir(exist_ok=True)

# Color schemes
COLORS = {
    'dark': {
        'bg': '#0d1117',
        'bg_secondary': '#161b22',
        'text': '#c9d1d9',
        'text_secondary': '#8b949e',
        'accent': '#58a6ff',
        'accent_gradient': ['#ff6b6b', '#feca57', '#48dbfb', '#ff9ff3'],
        'border': '#30363d',
        'success': '#3fb950',
        'warning': '#d29922',
        'heatmap': ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353']
    },
    'light': {
        'bg': '#ffffff',
        'bg_secondary': '#f6f8fa',
        'text': '#24292f',
        'text_secondary': '#57606a',
        'accent': '#0969da',
        'accent_gradient': ['#ff6b6b', '#feca57', '#00d2d3', '#ff9ff3'],
        'border': '#d0d7de',
        'success': '#1a7f37',
        'warning': '#bf8700',
        'heatmap': ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39']
    }
}

# Skills list (no categorization as requested)
SKILLS = [
    ('HTML5', '#E34F26'),
    ('CSS3', '#1572B6'),
    ('JavaScript', '#F7DF1E'),
    ('TypeScript', '#3178C6'),
    ('React', '#61DAFB'),
    ('Next.js', '#000000'),
    ('Node.js', '#339933'),
    ('Python', '#3776AB'),
    ('Java', '#007396'),
    ('C++', '#00599C'),
    ('MongoDB', '#47A248'),
    ('PostgreSQL', '#4169E1'),
    ('Firebase', '#FFCA28'),
    ('Docker', '#2496ED'),
    ('Git', '#F05032'),
    ('AWS', '#232F3E'),
    ('Azure', '#0078D4'),
    ('Tailwind', '#06B6D4'),
    ('Redux', '#764ABC'),
    ('GraphQL', '#E10098'),
]


def fetch_github_stats():
    """Fetch GitHub statistics using GitHub API"""
    headers = {'Authorization': f'token {GH_TOKEN}'} if GH_TOKEN else {}
    
    stats = {
        'followers': 0,
        'following': 0,
        'public_repos': 0,
        'total_stars': 0,
        'total_commits': 0,
        'total_prs': 0,
        'total_issues': 0,
        'total_contributions': 0,
        'contributions': []
    }
    
    try:
        # Fetch user data
        print(f"  Fetching user data for {USERNAME}...")
        user_resp = requests.get(f'https://api.github.com/users/{USERNAME}', headers=headers)
        if user_resp.ok:
            user_data = user_resp.json()
            stats['followers'] = user_data.get('followers', 0)
            stats['following'] = user_data.get('following', 0)
            stats['public_repos'] = user_data.get('public_repos', 0)
            print(f"    Followers: {stats['followers']}, Repos: {stats['public_repos']}")
        else:
            print(f"    Failed to fetch user data: {user_resp.status_code}")
        
        # Fetch repos for stars count
        print("  Fetching repositories...")
        repos_resp = requests.get(
            f'https://api.github.com/users/{USERNAME}/repos?per_page=100',
            headers=headers
        )
        if repos_resp.ok:
            repos = repos_resp.json()
            stats['total_stars'] = sum(repo.get('stargazers_count', 0) for repo in repos)
            print(f"    Total Stars: {stats['total_stars']}")
        
        # Fetch contribution data using GraphQL (requires token)
        if GH_TOKEN:
            print("  Fetching contribution data via GraphQL...")
            graphql_query = """
            query($username: String!) {
                user(login: $username) {
                    contributionsCollection {
                        totalCommitContributions
                        totalPullRequestContributions
                        totalIssueContributions
                        contributionCalendar {
                            totalContributions
                            weeks {
                                contributionDays {
                                    contributionCount
                                    date
                                }
                            }
                        }
                    }
                    pullRequests(first: 1) {
                        totalCount
                    }
                    issues(first: 1) {
                        totalCount
                    }
                }
            }
            """
            graphql_resp = requests.post(
                'https://api.github.com/graphql',
                headers={'Authorization': f'bearer {GH_TOKEN}'},
                json={'query': graphql_query, 'variables': {'username': USERNAME}}
            )
            if graphql_resp.ok:
                data = graphql_resp.json()
                user = data.get('data', {}).get('user', {})
                contrib_collection = user.get('contributionsCollection', {})
                calendar = contrib_collection.get('contributionCalendar', {})
                
                stats['total_commits'] = contrib_collection.get('totalCommitContributions', 0)
                stats['total_prs'] = user.get('pullRequests', {}).get('totalCount', 0)
                stats['total_issues'] = user.get('issues', {}).get('totalCount', 0)
                stats['total_contributions'] = calendar.get('totalContributions', 0)
                
                print(f"    Commits: {stats['total_commits']}, PRs: {stats['total_prs']}")
                print(f"    Total Contributions: {stats['total_contributions']}")
                
                # Parse contribution calendar
                weeks = calendar.get('weeks', [])
                for week in weeks:
                    for day in week.get('contributionDays', []):
                        stats['contributions'].append({
                            'date': day.get('date'),
                            'count': day.get('contributionCount', 0)
                        })
                print(f"    Contribution days loaded: {len(stats['contributions'])}")
            else:
                print(f"    GraphQL failed: {graphql_resp.status_code}")
        else:
            print("  No GH_TOKEN - using REST API fallback...")
            events_resp = requests.get(
                f'https://api.github.com/users/{USERNAME}/events?per_page=100',
                headers=headers
            )
            if events_resp.ok:
                events = events_resp.json()
                push_events = [e for e in events if e.get('type') == 'PushEvent']
                stats['total_commits'] = sum(len(e.get('payload', {}).get('commits', [])) for e in push_events)
                
    except Exception as e:
        print(f"Error fetching GitHub stats: {e}")
    
    return stats


def fetch_wakatime_stats():
    """Fetch WakaTime statistics from local cache"""
    try:
        with open('wakatime_stats.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"  Loaded WakaTime stats from cache")
            print(f"    Today: {data.get('today_total', 'N/A')}")
            print(f"    This Week: {data.get('this_week_total', 'N/A')}")
            return data
    except Exception as e:
        print(f"  Could not load wakatime_stats.json: {e}")
        return {
            'today_total': '0h 0m',
            'yesterday_total': '0h 0m',
            'this_week_total': '0h 0m',
            'last_week_total': '0h 0m',
            'week_change': '+0%',
            'daily_hours': [0] * 7,
            'daily_labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'most_productive_day': 'N/A',
            'most_productive_hours': 0,
            'top_language': 'N/A',
            'top_editor': 'VS Code',
        }


def fetch_profile_views():
    """Fetch profile views from stored data"""
    try:
        with open('data/profile-views.json', 'r') as f:
            data = json.load(f)
            views = data.get('total_views', 0)
            print(f"  Profile views: {views}")
            return views
    except Exception as e:
        print(f"  Could not load profile views: {e}")
        return 0


def generate_stat_card(title, value, theme='dark'):
    """Generate a stat card SVG - clean layout without emojis"""
    c = COLORS[theme]
    display_value = str(value)[:18] if len(str(value)) > 18 else str(value)
    safe_title = title.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="85" viewBox="0 0 200 85">
  <defs>
    <linearGradient id="grad_{theme}_{safe_title}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{c['accent_gradient'][0]};stop-opacity:0.12"/>
      <stop offset="100%" style="stop-color:{c['accent_gradient'][2]};stop-opacity:0.12"/>
    </linearGradient>
  </defs>
  <rect width="200" height="85" rx="10" fill="{c['bg_secondary']}"/>
  <rect x="1" y="1" width="198" height="83" rx="9" fill="url(#grad_{theme}_{safe_title})" opacity="0.6"/>
  <text x="100" y="28" font-family="Segoe UI, Arial, sans-serif" font-size="11" fill="{c['text_secondary']}" text-anchor="middle" font-weight="500">{title}</text>
  <text x="100" y="58" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="bold" fill="{c['text']}" text-anchor="middle">{display_value}</text>
</svg>'''
    return svg


def generate_header_svg(theme='dark'):
    """Generate animated header SVG"""
    c = COLORS[theme]
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="100" viewBox="0 0 900 100">
  <defs>
    <linearGradient id="headerGrad_{theme}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:{c['accent_gradient'][0]}">
        <animate attributeName="stop-color" values="{c['accent_gradient'][0]};{c['accent_gradient'][1]};{c['accent_gradient'][2]};{c['accent_gradient'][3]};{c['accent_gradient'][0]}" dur="8s" repeatCount="indefinite"/>
      </stop>
      <stop offset="50%" style="stop-color:{c['accent_gradient'][1]}">
        <animate attributeName="stop-color" values="{c['accent_gradient'][1]};{c['accent_gradient'][2]};{c['accent_gradient'][3]};{c['accent_gradient'][0]};{c['accent_gradient'][1]}" dur="8s" repeatCount="indefinite"/>
      </stop>
      <stop offset="100%" style="stop-color:{c['accent_gradient'][2]}">
        <animate attributeName="stop-color" values="{c['accent_gradient'][2]};{c['accent_gradient'][3]};{c['accent_gradient'][0]};{c['accent_gradient'][1]};{c['accent_gradient'][2]}" dur="8s" repeatCount="indefinite"/>
      </stop>
    </linearGradient>
  </defs>
  <rect width="900" height="100" fill="{c['bg']}"/>
  <text x="50%" y="45%" dominant-baseline="middle" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="38" font-weight="bold" fill="url(#headerGrad_{theme})">
    Hi there! I'm Arpan
  </text>
  <text x="50%" y="78" dominant-baseline="middle" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{c['text_secondary']}">
    Full Stack Developer | Open Source Enthusiast | Tech Explorer
  </text>
</svg>'''
    return svg


def generate_footer_svg(theme='dark'):
    """Generate animated footer SVG"""
    c = COLORS[theme]
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="60" viewBox="0 0 900 60">
  <defs>
    <linearGradient id="footerGrad_{theme}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:{c['accent_gradient'][0]}"/>
      <stop offset="33%" style="stop-color:{c['accent_gradient'][1]}"/>
      <stop offset="66%" style="stop-color:{c['accent_gradient'][2]}"/>
      <stop offset="100%" style="stop-color:{c['accent_gradient'][3]}"/>
    </linearGradient>
  </defs>
  <rect width="900" height="2" fill="url(#footerGrad_{theme})"/>
  <rect y="58" width="900" height="2" fill="url(#footerGrad_{theme})"/>
  <text x="50%" y="35" dominant-baseline="middle" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="13" fill="{c['text_secondary']}">
    Thanks for visiting! Drop a star if you like my work
  </text>
</svg>'''
    return svg


def generate_social_badge(platform, theme='dark'):
    """Generate animated social badge SVG"""
    c = COLORS[theme]
    
    platforms = {
        'linkedin': {'color': '#0A66C2', 'text': 'LinkedIn'},
        'twitter': {'color': '#1DA1F2', 'text': 'Twitter/X'},
        'youtube': {'color': '#FF0000', 'text': 'YouTube'},
        'email': {'color': '#EA4335', 'text': 'Email'},
        'portfolio': {'color': '#8B5CF6', 'text': 'Portfolio'}
    }
    
    p = platforms.get(platform, {'color': c['accent'], 'text': platform})
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="110" height="36" viewBox="0 0 110 36">
  <defs>
    <linearGradient id="socialGrad_{platform}_{theme}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{p['color']};stop-opacity:0.9"/>
      <stop offset="100%" style="stop-color:{p['color']};stop-opacity:1"/>
    </linearGradient>
  </defs>
  <rect width="110" height="36" rx="18" fill="url(#socialGrad_{platform}_{theme})">
    <animate attributeName="opacity" values="0.92;1;0.92" dur="2s" repeatCount="indefinite"/>
  </rect>
  <text x="55" y="23" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="bold" fill="white" text-anchor="middle">{p['text']}</text>
</svg>'''
    return svg


def generate_skills_scroll(theme='dark'):
    """Generate horizontally scrolling skills SVG"""
    c = COLORS[theme]
    
    skill_elements = []
    x = 0
    for skill, color in SKILLS:
        skill_elements.append(f'''
    <g transform="translate({x}, 0)">
      <rect width="95" height="32" rx="16" fill="{color}" opacity="0.9"/>
      <text x="47" y="21" font-family="Segoe UI, Arial, sans-serif" font-size="11" font-weight="bold" 
            fill="white" text-anchor="middle">{skill}</text>
    </g>''')
        x += 105
    
    total_width = x
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="50" viewBox="0 0 900 50">
  <defs>
    <clipPath id="skillsClip_{theme}">
      <rect width="900" height="50"/>
    </clipPath>
  </defs>
  <rect width="900" height="50" fill="{c['bg']}"/>
  <g clip-path="url(#skillsClip_{theme})">
    <g transform="translate(0, 9)">
      <animateTransform attributeName="transform" type="translate" 
                        from="0 9" to="-{total_width} 9" 
                        dur="25s" repeatCount="indefinite"/>
      {''.join(skill_elements)}
      <g transform="translate({total_width}, 0)">
        {''.join(skill_elements)}
      </g>
    </g>
  </g>
</svg>'''
    return svg


def generate_weekly_chart(wakatime_stats, theme='dark'):
    """Generate weekly activity bar chart SVG"""
    c = COLORS[theme]
    
    if not wakatime_stats:
        wakatime_stats = {'daily_hours': [0]*7, 'daily_labels': ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']}
    
    hours = wakatime_stats.get('daily_hours', [0]*7)
    labels = wakatime_stats.get('daily_labels', ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'])
    
    while len(hours) < 7:
        hours.append(0)
    while len(labels) < 7:
        labels.append('')
    
    max_hours = max(hours) if max(hours) > 0 else 1
    bar_width = 70
    spacing = 25
    chart_height = 180
    
    bars = []
    for i, (h, label) in enumerate(zip(hours[:7], labels[:7])):
        bar_height = (h / max_hours) * 130 if max_hours > 0 else 0
        x = i * (bar_width + spacing) + 80
        y = chart_height - bar_height
        
        gradient_id = f"barGrad_{i}_{theme}"
        
        bars.append(f'''
    <defs>
      <linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" style="stop-color:{c['accent_gradient'][i % 4]}"/>
        <stop offset="100%" style="stop-color:{c['accent_gradient'][(i+1) % 4]}"/>
      </linearGradient>
    </defs>
    <rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" rx="6" fill="url(#{gradient_id})">
      <animate attributeName="height" from="0" to="{bar_height}" dur="0.5s" fill="freeze"/>
      <animate attributeName="y" from="{chart_height}" to="{y}" dur="0.5s" fill="freeze"/>
    </rect>
    <text x="{x + bar_width/2}" y="{y - 8}" font-family="Segoe UI, Arial, sans-serif" font-size="11" 
          fill="{c['text']}" text-anchor="middle">{h:.1f}h</text>
    <text x="{x + bar_width/2}" y="{chart_height + 20}" font-family="Segoe UI, Arial, sans-serif" font-size="11" 
          fill="{c['text_secondary']}" text-anchor="middle">{label}</text>''')
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="250" viewBox="0 0 900 250">
  <rect width="900" height="250" fill="{c['bg']}" rx="12"/>
  <text x="450" y="28" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="bold" 
        fill="{c['text']}" text-anchor="middle">Weekly Coding Activity</text>
  <g transform="translate(75, 35)">
    {''.join(bars)}
  </g>
</svg>'''
    return svg


def generate_github_stats_card(stats, theme='dark'):
    """Generate GitHub stats overview card"""
    c = COLORS[theme]
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="160" viewBox="0 0 900 160">
  <defs>
    <linearGradient id="statsCardGrad_{theme}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{c['accent_gradient'][0]};stop-opacity:0.08"/>
      <stop offset="100%" style="stop-color:{c['accent_gradient'][2]};stop-opacity:0.08"/>
    </linearGradient>
  </defs>
  <rect width="900" height="160" rx="12" fill="{c['bg_secondary']}"/>
  <rect x="2" y="2" width="896" height="156" rx="10" fill="url(#statsCardGrad_{theme})"/>
  
  <text x="450" y="28" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="bold" 
        fill="{c['text']}" text-anchor="middle">GitHub Statistics</text>
  
  <g transform="translate(45, 48)">
    <g>
      <rect width="150" height="65" rx="8" fill="{c['bg']}" opacity="0.5"/>
      <text x="75" y="25" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="{c['text_secondary']}" text-anchor="middle">Followers</text>
      <text x="75" y="50" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="bold" fill="{c['text']}" text-anchor="middle">{stats.get('followers', 0)}</text>
    </g>
    
    <g transform="translate(165, 0)">
      <rect width="150" height="65" rx="8" fill="{c['bg']}" opacity="0.5"/>
      <text x="75" y="25" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="{c['text_secondary']}" text-anchor="middle">Repositories</text>
      <text x="75" y="50" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="bold" fill="{c['text']}" text-anchor="middle">{stats.get('public_repos', 0)}</text>
    </g>
    
    <g transform="translate(330, 0)">
      <rect width="150" height="65" rx="8" fill="{c['bg']}" opacity="0.5"/>
      <text x="75" y="25" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="{c['text_secondary']}" text-anchor="middle">Total Stars</text>
      <text x="75" y="50" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="bold" fill="{c['text']}" text-anchor="middle">{stats.get('total_stars', 0)}</text>
    </g>
    
    <g transform="translate(495, 0)">
      <rect width="150" height="65" rx="8" fill="{c['bg']}" opacity="0.5"/>
      <text x="75" y="25" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="{c['text_secondary']}" text-anchor="middle">Commits (Year)</text>
      <text x="75" y="50" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="bold" fill="{c['text']}" text-anchor="middle">{stats.get('total_commits', 0)}</text>
    </g>
    
    <g transform="translate(660, 0)">
      <rect width="150" height="65" rx="8" fill="{c['bg']}" opacity="0.5"/>
      <text x="75" y="25" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="{c['text_secondary']}" text-anchor="middle">Contributions</text>
      <text x="75" y="50" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="bold" fill="{c['accent']}" text-anchor="middle">{stats.get('total_contributions', 0)}</text>
    </g>
  </g>
</svg>'''
    return svg


def generate_contribution_heatmap(stats, theme='dark'):
    """Generate contribution heatmap SVG"""
    c = COLORS[theme]
    contributions = stats.get('contributions', [])
    
    cell_size = 10
    cell_gap = 3
    weeks = 52
    days = 7
    
    contrib_map = {}
    for contrib in contributions:
        if contrib.get('date'):
            contrib_map[contrib['date']] = contrib.get('count', 0)
    
    cells = []
    today = datetime.now()
    
    max_contrib = 1
    if contributions:
        counts = [c.get('count', 0) for c in contributions if c.get('count', 0) > 0]
        if counts:
            max_contrib = max(counts)
    
    for week in range(weeks):
        for day in range(days):
            date = today - timedelta(days=(weeks - 1 - week) * 7 + (6 - day))
            date_str = date.strftime('%Y-%m-%d')
            count = contrib_map.get(date_str, 0)
            
            if count == 0:
                level = 0
            elif count <= max_contrib * 0.25:
                level = 1
            elif count <= max_contrib * 0.5:
                level = 2
            elif count <= max_contrib * 0.75:
                level = 3
            else:
                level = 4
            
            x = 45 + week * (cell_size + cell_gap)
            y = 35 + day * (cell_size + cell_gap)
            color = c['heatmap'][level]
            
            cells.append(f'''
    <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" rx="2" fill="{color}"/>''')
    
    day_labels = ['', 'Mon', '', 'Wed', '', 'Fri', '']
    day_label_elements = []
    for i, label in enumerate(day_labels):
        if label:
            y = 35 + i * (cell_size + cell_gap) + cell_size/2 + 3
            day_label_elements.append(f'''
    <text x="38" y="{y}" font-family="Segoe UI, Arial, sans-serif" font-size="8" 
          fill="{c['text_secondary']}" text-anchor="end">{label}</text>''')
    
    month_labels = []
    current_month = None
    for week in range(weeks):
        date = today - timedelta(days=(weeks - 1 - week) * 7)
        month = date.strftime('%b')
        if month != current_month:
            current_month = month
            x = 45 + week * (cell_size + cell_gap)
            month_labels.append(f'''
    <text x="{x}" y="26" font-family="Segoe UI, Arial, sans-serif" font-size="8" 
          fill="{c['text_secondary']}">{month}</text>''')
    
    total_contributions = stats.get('total_contributions', sum(c.get('count', 0) for c in contributions))
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="155" viewBox="0 0 900 155">
  <rect width="900" height="155" fill="{c['bg']}" rx="12"/>
  <text x="450" y="16" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="{c['text']}" text-anchor="middle">
    {total_contributions} contributions in the last year
  </text>
  {''.join(month_labels)}
  {''.join(day_label_elements)}
  {''.join(cells)}
  
  <g transform="translate(730, 133)">
    <text x="-8" y="8" font-family="Segoe UI, Arial, sans-serif" font-size="8" fill="{c['text_secondary']}">Less</text>
    <rect x="20" y="0" width="{cell_size}" height="{cell_size}" rx="2" fill="{c['heatmap'][0]}"/>
    <rect x="{20 + cell_size + 2}" y="0" width="{cell_size}" height="{cell_size}" rx="2" fill="{c['heatmap'][1]}"/>
    <rect x="{20 + (cell_size + 2) * 2}" y="0" width="{cell_size}" height="{cell_size}" rx="2" fill="{c['heatmap'][2]}"/>
    <rect x="{20 + (cell_size + 2) * 3}" y="0" width="{cell_size}" height="{cell_size}" rx="2" fill="{c['heatmap'][3]}"/>
    <rect x="{20 + (cell_size + 2) * 4}" y="0" width="{cell_size}" height="{cell_size}" rx="2" fill="{c['heatmap'][4]}"/>
    <text x="{20 + (cell_size + 2) * 5 + 4}" y="8" font-family="Segoe UI, Arial, sans-serif" font-size="8" fill="{c['text_secondary']}">More</text>
  </g>
</svg>'''
    return svg


def generate_project_card_full(name, emoji, description, tech_stack, features, theme='dark'):
    """Generate full-width project card SVG"""
    c = COLORS[theme]
    feature_text = ' | '.join(features[:4])
    safe_name = name.replace(' ', '').replace('-', '')
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="90" viewBox="0 0 900 90">
  <defs>
    <linearGradient id="projGrad_{safe_name}_{theme}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{c['accent_gradient'][0]};stop-opacity:0.12"/>
      <stop offset="100%" style="stop-color:{c['accent_gradient'][2]};stop-opacity:0.12"/>
    </linearGradient>
  </defs>
  <rect width="900" height="90" rx="10" fill="{c['bg_secondary']}" stroke="{c['border']}" stroke-width="1"/>
  <rect x="2" y="2" width="896" height="86" rx="8" fill="url(#projGrad_{safe_name}_{theme})" opacity="0.6"/>
  
  <text x="22" y="38" font-size="26">{emoji}</text>
  <text x="58" y="32" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="bold" fill="{c['text']}">{name}</text>
  <text x="58" y="52" font-family="Segoe UI, Arial, sans-serif" font-size="11" fill="{c['text_secondary']}">{description}</text>
  <text x="58" y="72" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="{c['accent']}">{tech_stack}</text>
  
  <text x="865" y="52" font-family="Segoe UI, Arial, sans-serif" font-size="9" fill="{c['text_secondary']}" text-anchor="end">{feature_text}</text>
  <text x="865" y="32" font-family="Segoe UI, Arial, sans-serif" font-size="11" fill="{c['accent']}" text-anchor="end">Click to expand</text>
</svg>'''
    return svg


def generate_badge_svg(label, value, color, theme='dark'):
    """Generate a profile badge SVG"""
    c = COLORS[theme]
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="140" height="26" viewBox="0 0 140 26">
  <rect width="65" height="26" rx="4" fill="{c['bg_secondary']}"/>
  <rect x="65" width="75" height="26" rx="4" fill="{color}"/>
  <text x="32" y="17" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="{c['text']}" text-anchor="middle">{label}</text>
  <text x="102" y="17" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="white" text-anchor="middle" font-weight="bold">{value}</text>
</svg>'''
    return svg


def save_svg(filepath, content):
    """Save SVG content with UTF-8 encoding"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    print("=" * 50)
    print("Profile Assets Generator")
    print("=" * 50)
    
    print("\n[1/3] Fetching GitHub stats...")
    github_stats = fetch_github_stats()
    
    print("\n[2/3] Fetching WakaTime stats...")
    wakatime_stats = fetch_wakatime_stats()
    
    print("\n[3/3] Fetching profile views...")
    profile_views = fetch_profile_views()
    
    # Calculate average daily coding time
    daily_hours = wakatime_stats.get('daily_hours', [0]*7)
    avg_daily_hours = sum(daily_hours) / len(daily_hours) if daily_hours else 0
    avg_daily_str = f"{int(avg_daily_hours)}h {int((avg_daily_hours % 1) * 60)}m"
    active_days = sum(1 for h in daily_hours if h > 0)
    
    for theme in ['dark', 'light']:
        print(f"\n[Generating {theme} theme assets]")
        
        save_svg(ASSETS_DIR / f'header-{theme}.svg', generate_header_svg(theme))
        save_svg(ASSETS_DIR / f'footer-{theme}.svg', generate_footer_svg(theme))
        
        for platform in ['linkedin', 'twitter', 'youtube', 'email', 'portfolio']:
            save_svg(ASSETS_DIR / f'social-{platform}-{theme}.svg', generate_social_badge(platform, theme))
        
        save_svg(ASSETS_DIR / f'skills-scroll-{theme}.svg', generate_skills_scroll(theme))
        save_svg(ASSETS_DIR / f'weekly-activity-{theme}.svg', generate_weekly_chart(wakatime_stats, theme))
        save_svg(ASSETS_DIR / f'github-stats-{theme}.svg', generate_github_stats_card(github_stats, theme))
        save_svg(ASSETS_DIR / f'contribution-heatmap-{theme}.svg', generate_contribution_heatmap(github_stats, theme))
        
        save_svg(ASSETS_DIR / f'github-followers.svg', generate_badge_svg('Followers', str(github_stats.get('followers', 0)), '#58a6ff', 'dark'))
        save_svg(ASSETS_DIR / f'github-followers-light.svg', generate_badge_svg('Followers', str(github_stats.get('followers', 0)), '#0969da', 'light'))
        save_svg(ASSETS_DIR / f'github-stars.svg', generate_badge_svg('Stars', str(github_stats.get('total_stars', 0)), '#f0883e', 'dark'))
        save_svg(ASSETS_DIR / f'github-stars-light.svg', generate_badge_svg('Stars', str(github_stats.get('total_stars', 0)), '#bf8700', 'light'))
        save_svg(ASSETS_DIR / f'profile-views.svg', generate_badge_svg('Views', str(profile_views), '#a371f7', 'dark'))
        save_svg(ASSETS_DIR / f'profile-views-light.svg', generate_badge_svg('Views', str(profile_views), '#8250df', 'light'))
        
        stat_configs = [
            ('today', 'Today', wakatime_stats.get('today_total', '0h 0m')),
            ('yesterday', 'Yesterday', wakatime_stats.get('yesterday_total', '0h 0m')),
            ('thisweek', 'This Week', wakatime_stats.get('this_week_total', '0h 0m')),
            ('lastweek', 'Last Week', wakatime_stats.get('last_week_total', '0h 0m')),
            ('productive', 'Most Productive', wakatime_stats.get('most_productive_day', 'N/A')),
            ('toplang', 'Top Language', wakatime_stats.get('top_language', 'N/A')),
            ('editor', 'Editor', wakatime_stats.get('top_editor', 'VS Code')),
            ('avgdaily', 'Daily Average', avg_daily_str),
            ('activedays', 'Active Days', f"{active_days}/7"),
            ('weekchange', 'Week Change', wakatime_stats.get('week_change', '+0%')),
            ('commits', 'Commits (Year)', str(github_stats.get('total_commits', 0))),
            ('prs', 'Pull Requests', str(github_stats.get('total_prs', 0))),
        ]
        
        for stat_id, title, value in stat_configs:
            save_svg(ASSETS_DIR / f'stat-{stat_id}-{theme}.svg', generate_stat_card(title, value, theme))
        
        projects = [
            ('atmark', '📝', 'AtMark', 'A modern note-taking application', 'React, Node.js, MongoDB', ['Rich Text', 'Tags', 'Search', 'Cloud Sync']),
            ('tripbudget', '✈️', 'TripBudget', 'Travel expense tracking made easy', 'React Native, Firebase', ['Expenses', 'Analytics', 'Multi-currency', 'Groups']),
            ('fitness', '💪', 'Fitness Dashboard', 'Track your fitness journey', 'Next.js, TailwindCSS', ['Progress', 'Workouts', 'Nutrition', 'Responsive']),
            ('floatchat', '💬', 'Float Chat', 'Real-time messaging application', 'Socket.io, Express, React', ['Real-time', 'Themes', 'Files', 'Encrypted']),
            ('mobapp', '📱', 'MOB-APP', 'Cross-platform mobile application', 'React Native, Expo', ['Cross-platform', 'Push Notifs', 'Location', 'Offline']),
            ('medix', '🏥', 'Medix Manager', 'Healthcare management system', 'Django, PostgreSQL', ['Records', 'Scheduling', 'Prescriptions', 'Analytics']),
        ]
        
        for proj_id, emoji, name, desc, tech, features in projects:
            save_svg(ASSETS_DIR / f'project-{proj_id}-{theme}.svg', generate_project_card_full(name, emoji, desc, tech, features, theme))
    
    print("\n" + "=" * 50)
    print("All assets generated successfully!")
    print(f"Assets saved to: {ASSETS_DIR.absolute()}")
    print("=" * 50)


if __name__ == '__main__':
    main()
