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
        'contributions': []
    }
    
    try:
        # Fetch user data
        user_resp = requests.get(f'https://api.github.com/users/{USERNAME}', headers=headers)
        if user_resp.ok:
            user_data = user_resp.json()
            stats['followers'] = user_data.get('followers', 0)
            stats['following'] = user_data.get('following', 0)
            stats['public_repos'] = user_data.get('public_repos', 0)
        
        # Fetch repos for stars count
        repos_resp = requests.get(
            f'https://api.github.com/users/{USERNAME}/repos?per_page=100',
            headers=headers
        )
        if repos_resp.ok:
            repos = repos_resp.json()
            stats['total_stars'] = sum(repo.get('stargazers_count', 0) for repo in repos)
        
        # Fetch commit count (estimate from events)
        events_resp = requests.get(
            f'https://api.github.com/users/{USERNAME}/events?per_page=100',
            headers=headers
        )
        if events_resp.ok:
            events = events_resp.json()
            push_events = [e for e in events if e.get('type') == 'PushEvent']
            commits_count = sum(len(e.get('payload', {}).get('commits', [])) for e in push_events)
            stats['total_commits'] = commits_count if commits_count > 0 else 150  # fallback estimate
        
        # Fetch PRs
        search_resp = requests.get(
            f'https://api.github.com/search/issues?q=author:{USERNAME}+type:pr',
            headers=headers
        )
        if search_resp.ok:
            stats['total_prs'] = search_resp.json().get('total_count', 0)
        
        # Fetch issues
        search_resp = requests.get(
            f'https://api.github.com/search/issues?q=author:{USERNAME}+type:issue',
            headers=headers
        )
        if search_resp.ok:
            stats['total_issues'] = search_resp.json().get('total_count', 0)
            
        # Fetch contribution data using GraphQL
        if GH_TOKEN:
            graphql_query = """
            query($username: String!) {
                user(login: $username) {
                    contributionsCollection {
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
                calendar = data.get('data', {}).get('user', {}).get('contributionsCollection', {}).get('contributionCalendar', {})
                stats['total_contributions'] = calendar.get('totalContributions', 0)
                weeks = calendar.get('weeks', [])
                for week in weeks:
                    for day in week.get('contributionDays', []):
                        stats['contributions'].append({
                            'date': day.get('date'),
                            'count': day.get('contributionCount', 0)
                        })
    except Exception as e:
        print(f"Error fetching GitHub stats: {e}")
    
    return stats


def fetch_wakatime_stats():
    """Fetch WakaTime statistics"""
    if not WAKATIME_API_KEY:
        # Return cached data if available
        try:
            with open('wakatime_stats.json', 'r') as f:
                return json.load(f)
        except:
            return None
    
    try:
        headers = {'Authorization': f'Basic {WAKATIME_API_KEY}'}
        
        # Fetch stats summary
        resp = requests.get(
            'https://wakatime.com/api/v1/users/current/stats/last_7_days',
            headers=headers
        )
        
        if resp.ok:
            data = resp.json().get('data', {})
            
            stats = {
                'today_total': '0h 0m',
                'yesterday_total': '0h 0m',
                'this_week_total': data.get('human_readable_total', '0h 0m'),
                'last_week_total': '0h 0m',
                'week_change': '+0%',
                'daily_hours': [0] * 7,
                'daily_labels': [],
                'most_productive_day': 'N/A',
                'most_productive_hours': '0h',
                'top_language': data.get('languages', [{}])[0].get('name', 'N/A') if data.get('languages') else 'N/A',
                'top_editor': data.get('editors', [{}])[0].get('name', 'VS Code') if data.get('editors') else 'VS Code',
                'avg_daily': '0h',
                'active_days': 0
            }
            
            # Calculate daily stats
            days = data.get('days', [])
            if days:
                today = datetime.now().strftime('%Y-%m-%d')
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                
                daily_hours = []
                daily_labels = []
                max_hours = 0
                max_day = 'N/A'
                active_count = 0
                
                for day in days:
                    hours = day.get('total_seconds', 0) / 3600
                    daily_hours.append(round(hours, 2))
                    daily_labels.append(datetime.strptime(day.get('date', ''), '%Y-%m-%d').strftime('%a'))
                    
                    if hours > max_hours:
                        max_hours = hours
                        max_day = day.get('date', 'N/A')
                    
                    if hours > 0:
                        active_count += 1
                    
                    if day.get('date') == today:
                        hrs = int(hours)
                        mins = int((hours - hrs) * 60)
                        stats['today_total'] = f"{hrs}h {mins}m"
                    elif day.get('date') == yesterday:
                        hrs = int(hours)
                        mins = int((hours - hrs) * 60)
                        stats['yesterday_total'] = f"{hrs}h {mins}m"
                
                stats['daily_hours'] = daily_hours
                stats['daily_labels'] = daily_labels
                stats['most_productive_day'] = datetime.strptime(max_day, '%Y-%m-%d').strftime('%A') if max_day != 'N/A' else 'N/A'
                stats['most_productive_hours'] = f"{int(max_hours)}h"
                stats['active_days'] = active_count
                
                # Calculate average
                total_seconds = sum(day.get('total_seconds', 0) for day in days)
                avg_hours = (total_seconds / 3600) / len(days) if days else 0
                stats['avg_daily'] = f"{int(avg_hours)}h {int((avg_hours % 1) * 60)}m"
            
            # Save to file
            with open('wakatime_stats.json', 'w') as f:
                json.dump(stats, f, indent=2)
            
            return stats
    except Exception as e:
        print(f"Error fetching WakaTime stats: {e}")
    
    return None


def fetch_profile_views():
    """Fetch profile views from stored data"""
    try:
        with open('data/profile-views.json', 'r') as f:
            data = json.load(f)
            return data.get('total_views', 0)
    except:
        return 0


def generate_stat_card(title, value, icon, theme='dark'):
    """Generate a stat card SVG"""
    c = COLORS[theme]
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
  <defs>
    <linearGradient id="grad_{theme}_{title.replace(' ', '_')}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{c['accent_gradient'][0]};stop-opacity:0.2"/>
      <stop offset="100%" style="stop-color:{c['accent_gradient'][2]};stop-opacity:0.2"/>
    </linearGradient>
  </defs>
  <rect width="200" height="100" rx="12" fill="{c['bg_secondary']}"/>
  <rect x="2" y="2" width="196" height="96" rx="10" fill="url(#grad_{theme}_{title.replace(' ', '_')})" opacity="0.3"/>
  <text x="20" y="35" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="{c['text_secondary']}">{title}</text>
  <text x="20" y="70" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="bold" fill="{c['text']}">{value}</text>
  <text x="170" y="60" font-size="24">{icon}</text>
</svg>'''
    return svg


def generate_header_svg(theme='dark'):
    """Generate animated header SVG"""
    c = COLORS[theme]
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="120" viewBox="0 0 900 120">
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
  <rect width="900" height="120" fill="{c['bg']}"/>
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="48" font-weight="bold" fill="url(#headerGrad_{theme})">
    Hi there! I'm Arpan 👋
  </text>
  <text x="50%" y="85" dominant-baseline="middle" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="18" fill="{c['text_secondary']}">
    Full Stack Developer | Open Source Enthusiast | Tech Explorer
  </text>
</svg>'''
    return svg


def generate_footer_svg(theme='dark'):
    """Generate animated footer SVG"""
    c = COLORS[theme]
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="80" viewBox="0 0 900 80">
  <defs>
    <linearGradient id="footerGrad_{theme}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:{c['accent_gradient'][0]}"/>
      <stop offset="33%" style="stop-color:{c['accent_gradient'][1]}"/>
      <stop offset="66%" style="stop-color:{c['accent_gradient'][2]}"/>
      <stop offset="100%" style="stop-color:{c['accent_gradient'][3]}"/>
    </linearGradient>
  </defs>
  <rect width="900" height="2" fill="url(#footerGrad_{theme})"/>
  <rect y="78" width="900" height="2" fill="url(#footerGrad_{theme})"/>
  <text x="50%" y="45" dominant-baseline="middle" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{c['text_secondary']}">
    Thanks for visiting! Drop a ⭐ if you like my work
  </text>
</svg>'''
    return svg


def generate_social_badge(platform, theme='dark'):
    """Generate animated social badge SVG"""
    c = COLORS[theme]
    
    platforms = {
        'linkedin': {'color': '#0A66C2', 'icon': '🔗', 'text': 'LinkedIn'},
        'twitter': {'color': '#1DA1F2', 'icon': '🐦', 'text': 'Twitter'},
        'youtube': {'color': '#FF0000', 'icon': '📺', 'text': 'YouTube'},
        'email': {'color': '#EA4335', 'icon': '📧', 'text': 'Email'},
        'portfolio': {'color': '#8B5CF6', 'icon': '🌐', 'text': 'Portfolio'}
    }
    
    p = platforms.get(platform, {'color': c['accent'], 'icon': '🔗', 'text': platform})
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="140" height="45" viewBox="0 0 140 45">
  <defs>
    <linearGradient id="socialGrad_{platform}_{theme}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{p['color']};stop-opacity:0.8"/>
      <stop offset="100%" style="stop-color:{p['color']};stop-opacity:1"/>
    </linearGradient>
    <filter id="glow_{platform}_{theme}">
      <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <rect width="140" height="45" rx="22" fill="url(#socialGrad_{platform}_{theme})" filter="url(#glow_{platform}_{theme})">
    <animate attributeName="opacity" values="0.9;1;0.9" dur="2s" repeatCount="indefinite"/>
  </rect>
  <text x="25" y="28" font-size="18">{p['icon']}</text>
  <text x="50" y="29" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="bold" fill="white">{p['text']}</text>
</svg>'''
    return svg


def generate_skills_scroll(theme='dark'):
    """Generate horizontally scrolling skills SVG"""
    c = COLORS[theme]
    
    # Create skill badges
    skill_elements = []
    x = 0
    for skill, color in SKILLS:
        skill_elements.append(f'''
    <g transform="translate({x}, 0)">
      <rect width="100" height="36" rx="18" fill="{color}" opacity="0.9"/>
      <text x="50" y="24" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="bold" 
            fill="white" text-anchor="middle">{skill}</text>
    </g>''')
        x += 110
    
    total_width = x
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="60" viewBox="0 0 900 60">
  <defs>
    <clipPath id="skillsClip_{theme}">
      <rect width="900" height="60"/>
    </clipPath>
  </defs>
  <rect width="900" height="60" fill="{c['bg']}"/>
  <g clip-path="url(#skillsClip_{theme})">
    <g transform="translate(0, 12)">
      <animateTransform attributeName="transform" type="translate" 
                        from="0 12" to="-{total_width} 12" 
                        dur="30s" repeatCount="indefinite"/>
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
    
    # Ensure we have 7 values
    while len(hours) < 7:
        hours.append(0)
    while len(labels) < 7:
        labels.append('')
    
    max_hours = max(hours) if max(hours) > 0 else 1
    bar_width = 80
    spacing = 20
    chart_height = 200
    
    bars = []
    for i, (h, label) in enumerate(zip(hours[:7], labels[:7])):
        bar_height = (h / max_hours) * 150 if max_hours > 0 else 0
        x = i * (bar_width + spacing) + 60
        y = chart_height - bar_height
        
        gradient_id = f"barGrad_{i}_{theme}"
        
        bars.append(f'''
    <defs>
      <linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" style="stop-color:{c['accent_gradient'][i % 4]}"/>
        <stop offset="100%" style="stop-color:{c['accent_gradient'][(i+1) % 4]}"/>
      </linearGradient>
    </defs>
    <rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" rx="8" fill="url(#{gradient_id})">
      <animate attributeName="height" from="0" to="{bar_height}" dur="0.5s" fill="freeze"/>
      <animate attributeName="y" from="{chart_height}" to="{y}" dur="0.5s" fill="freeze"/>
    </rect>
    <text x="{x + bar_width/2}" y="{y - 10}" font-family="Segoe UI, Arial, sans-serif" font-size="12" 
          fill="{c['text']}" text-anchor="middle">{h:.1f}h</text>
    <text x="{x + bar_width/2}" y="{chart_height + 25}" font-family="Segoe UI, Arial, sans-serif" font-size="12" 
          fill="{c['text_secondary']}" text-anchor="middle">{label}</text>''')
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="280" viewBox="0 0 900 280">
  <rect width="900" height="280" fill="{c['bg']}" rx="16"/>
  <text x="450" y="30" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="bold" 
        fill="{c['text']}" text-anchor="middle">📊 Weekly Coding Activity</text>
  <g transform="translate(100, 40)">
    {''.join(bars)}
  </g>
</svg>'''
    return svg


def generate_github_stats_card(stats, theme='dark'):
    """Generate GitHub stats overview card"""
    c = COLORS[theme]
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="200" viewBox="0 0 900 200">
  <defs>
    <linearGradient id="statsCardGrad_{theme}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{c['accent_gradient'][0]};stop-opacity:0.1"/>
      <stop offset="100%" style="stop-color:{c['accent_gradient'][2]};stop-opacity:0.1"/>
    </linearGradient>
  </defs>
  <rect width="900" height="200" rx="16" fill="{c['bg_secondary']}"/>
  <rect x="2" y="2" width="896" height="196" rx="14" fill="url(#statsCardGrad_{theme})"/>
  
  <text x="450" y="35" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="bold" 
        fill="{c['text']}" text-anchor="middle">GitHub Statistics</text>
  
  <g transform="translate(60, 70)">
    <!-- Followers -->
    <g>
      <text x="0" y="0" font-size="24">👥</text>
      <text x="40" y="0" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{c['text_secondary']}">Followers</text>
      <text x="40" y="30" font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="bold" fill="{c['text']}">{stats.get('followers', 0)}</text>
    </g>
    
    <!-- Repos -->
    <g transform="translate(180, 0)">
      <text x="0" y="0" font-size="24">📦</text>
      <text x="40" y="0" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{c['text_secondary']}">Repositories</text>
      <text x="40" y="30" font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="bold" fill="{c['text']}">{stats.get('public_repos', 0)}</text>
    </g>
    
    <!-- Stars -->
    <g transform="translate(360, 0)">
      <text x="0" y="0" font-size="24">⭐</text>
      <text x="40" y="0" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{c['text_secondary']}">Total Stars</text>
      <text x="40" y="30" font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="bold" fill="{c['text']}">{stats.get('total_stars', 0)}</text>
    </g>
    
    <!-- Commits -->
    <g transform="translate(540, 0)">
      <text x="0" y="0" font-size="24">📝</text>
      <text x="40" y="0" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{c['text_secondary']}">Commits</text>
      <text x="40" y="30" font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="bold" fill="{c['text']}">{stats.get('total_commits', 0)}</text>
    </g>
    
    <!-- PRs -->
    <g transform="translate(720, 0)">
      <text x="0" y="0" font-size="24">🔀</text>
      <text x="40" y="0" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{c['text_secondary']}">Pull Requests</text>
      <text x="40" y="30" font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="bold" fill="{c['text']}">{stats.get('total_prs', 0)}</text>
    </g>
  </g>
</svg>'''
    return svg


def generate_contribution_heatmap(stats, theme='dark'):
    """Generate contribution heatmap SVG"""
    c = COLORS[theme]
    contributions = stats.get('contributions', [])
    
    # Generate last 52 weeks of data
    cell_size = 12
    cell_gap = 3
    weeks = 52
    days = 7
    
    # Create contribution map
    contrib_map = {c.get('date'): c.get('count', 0) for c in contributions}
    
    # Generate cells
    cells = []
    today = datetime.now()
    max_contrib = max([c.get('count', 0) for c in contributions]) if contributions else 1
    
    for week in range(weeks):
        for day in range(days):
            date = today - timedelta(days=(weeks - 1 - week) * 7 + (6 - day))
            date_str = date.strftime('%Y-%m-%d')
            count = contrib_map.get(date_str, 0)
            
            # Determine color level
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
            
            x = 50 + week * (cell_size + cell_gap)
            y = 40 + day * (cell_size + cell_gap)
            color = c['heatmap'][level]
            
            cells.append(f'''
    <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" rx="2" fill="{color}">
      <title>{date_str}: {count} contributions</title>
    </rect>''')
    
    # Day labels
    day_labels = ['', 'Mon', '', 'Wed', '', 'Fri', '']
    day_label_elements = []
    for i, label in enumerate(day_labels):
        if label:
            y = 40 + i * (cell_size + cell_gap) + cell_size/2 + 4
            day_label_elements.append(f'''
    <text x="40" y="{y}" font-family="Segoe UI, Arial, sans-serif" font-size="10" 
          fill="{c['text_secondary']}" text-anchor="end">{label}</text>''')
    
    # Month labels
    month_labels = []
    current_month = None
    for week in range(weeks):
        date = today - timedelta(days=(weeks - 1 - week) * 7)
        month = date.strftime('%b')
        if month != current_month:
            current_month = month
            x = 50 + week * (cell_size + cell_gap)
            month_labels.append(f'''
    <text x="{x}" y="30" font-family="Segoe UI, Arial, sans-serif" font-size="10" 
          fill="{c['text_secondary']}">{month}</text>''')
    
    total_contributions = sum(c.get('count', 0) for c in contributions)
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="180" viewBox="0 0 900 180">
  <rect width="900" height="180" fill="{c['bg']}" rx="16"/>
  <text x="450" y="20" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{c['text']}" text-anchor="middle">
    {total_contributions} contributions in the last year
  </text>
  {''.join(month_labels)}
  {''.join(day_label_elements)}
  {''.join(cells)}
  
  <!-- Legend -->
  <g transform="translate(750, 155)">
    <text x="-10" y="10" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="{c['text_secondary']}">Less</text>
    <rect x="25" y="0" width="{cell_size}" height="{cell_size}" rx="2" fill="{c['heatmap'][0]}"/>
    <rect x="{25 + cell_size + 4}" y="0" width="{cell_size}" height="{cell_size}" rx="2" fill="{c['heatmap'][1]}"/>
    <rect x="{25 + (cell_size + 4) * 2}" y="0" width="{cell_size}" height="{cell_size}" rx="2" fill="{c['heatmap'][2]}"/>
    <rect x="{25 + (cell_size + 4) * 3}" y="0" width="{cell_size}" height="{cell_size}" rx="2" fill="{c['heatmap'][3]}"/>
    <rect x="{25 + (cell_size + 4) * 4}" y="0" width="{cell_size}" height="{cell_size}" rx="2" fill="{c['heatmap'][4]}"/>
    <text x="{25 + (cell_size + 4) * 5 + 5}" y="10" font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="{c['text_secondary']}">More</text>
  </g>
</svg>'''
    return svg


def generate_project_card(name, emoji, description, theme='dark'):
    """Generate project card SVG"""
    c = COLORS[theme]
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="80" viewBox="0 0 420 80">
  <defs>
    <linearGradient id="projGrad_{name}_{theme}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{c['accent_gradient'][0]};stop-opacity:0.2"/>
      <stop offset="100%" style="stop-color:{c['accent_gradient'][2]};stop-opacity:0.2"/>
    </linearGradient>
  </defs>
  <rect width="420" height="80" rx="12" fill="{c['bg_secondary']}" stroke="{c['border']}" stroke-width="1"/>
  <rect x="2" y="2" width="416" height="76" rx="10" fill="url(#projGrad_{name}_{theme})" opacity="0.5"/>
  <text x="20" y="35" font-size="24">{emoji}</text>
  <text x="55" y="35" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="bold" fill="{c['text']}">{name}</text>
  <text x="55" y="55" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="{c['text_secondary']}">{description[:45]}...</text>
  <text x="390" y="45" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="{c['accent']}">→</text>
</svg>'''
    return svg


def generate_badge_svg(label, value, color, theme='dark'):
    """Generate a profile badge SVG"""
    c = COLORS[theme]
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="150" height="28" viewBox="0 0 150 28">
  <rect width="70" height="28" rx="4" fill="{c['bg_secondary']}"/>
  <rect x="70" width="80" height="28" rx="4" fill="{color}"/>
  <text x="35" y="18" font-family="Segoe UI, Arial, sans-serif" font-size="11" fill="{c['text']}" text-anchor="middle">{label}</text>
  <text x="110" y="18" font-family="Segoe UI, Arial, sans-serif" font-size="11" fill="white" text-anchor="middle" font-weight="bold">{value}</text>
</svg>'''
    return svg


def save_svg(filepath, content):
    """Save SVG content with UTF-8 encoding"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    print("Starting profile assets generation...")
    
    # Fetch all data
    print("Fetching GitHub stats...")
    github_stats = fetch_github_stats()
    
    print("Fetching WakaTime stats...")
    wakatime_stats = fetch_wakatime_stats()
    
    print("Fetching profile views...")
    profile_views = fetch_profile_views()
    
    # Generate assets for both themes
    for theme in ['dark', 'light']:
        print(f"\nGenerating {theme} theme assets...")
        
        # Header & Footer
        save_svg(ASSETS_DIR / f'header-{theme}.svg', generate_header_svg(theme))
        save_svg(ASSETS_DIR / f'footer-{theme}.svg', generate_footer_svg(theme))
        
        # Social badges
        for platform in ['linkedin', 'twitter', 'youtube', 'email', 'portfolio']:
            save_svg(ASSETS_DIR / f'social-{platform}-{theme}.svg', generate_social_badge(platform, theme))
        
        # Skills scroll
        save_svg(ASSETS_DIR / f'skills-scroll-{theme}.svg', generate_skills_scroll(theme))
        
        # Weekly activity chart
        save_svg(ASSETS_DIR / f'weekly-activity-{theme}.svg', generate_weekly_chart(wakatime_stats, theme))
        
        # GitHub stats card
        save_svg(ASSETS_DIR / f'github-stats-{theme}.svg', generate_github_stats_card(github_stats, theme))
        
        # Contribution heatmap
        save_svg(ASSETS_DIR / f'contribution-heatmap-{theme}.svg', generate_contribution_heatmap(github_stats, theme))
        
        # Profile badges
        save_svg(ASSETS_DIR / f'github-followers.svg', generate_badge_svg('Followers', str(github_stats.get('followers', 0)), '#58a6ff', 'dark'))
        save_svg(ASSETS_DIR / f'github-followers-light.svg', generate_badge_svg('Followers', str(github_stats.get('followers', 0)), '#0969da', 'light'))
        save_svg(ASSETS_DIR / f'github-stars.svg', generate_badge_svg('Stars', str(github_stats.get('total_stars', 0)), '#f0883e', 'dark'))
        save_svg(ASSETS_DIR / f'github-stars-light.svg', generate_badge_svg('Stars', str(github_stats.get('total_stars', 0)), '#bf8700', 'light'))
        save_svg(ASSETS_DIR / f'profile-views.svg', generate_badge_svg('Views', str(profile_views), '#a371f7', 'dark'))
        save_svg(ASSETS_DIR / f'profile-views-light.svg', generate_badge_svg('Views', str(profile_views), '#8250df', 'light'))
        
        # Stat cards for coding dashboard
        if wakatime_stats:
            stat_configs = [
                ('today', 'Today', wakatime_stats.get('today_total', '0h'), '⏰'),
                ('yesterday', 'Yesterday', wakatime_stats.get('yesterday_total', '0h'), '📆'),
                ('thisweek', 'This Week', wakatime_stats.get('this_week_total', '0h'), '📊'),
                ('lastweek', 'Last Week', wakatime_stats.get('last_week_total', '0h'), '📈'),
                ('productive', 'Most Productive', wakatime_stats.get('most_productive_day', 'N/A'), '🔥'),
                ('toplang', 'Top Language', wakatime_stats.get('top_language', 'N/A'), '💻'),
                ('editor', 'Editor', wakatime_stats.get('top_editor', 'VS Code'), '🛠️'),
                ('avgdaily', 'Daily Average', wakatime_stats.get('avg_daily', '0h'), '⌛'),
                ('activedays', 'Active Days', f"{wakatime_stats.get('active_days', 0)}/7", '📌'),
                ('weekchange', 'Week Change', wakatime_stats.get('week_change', '0%'), '📉'),
            ]
            
            for stat_id, title, value, icon in stat_configs:
                save_svg(ASSETS_DIR / f'stat-{stat_id}-{theme}.svg', generate_stat_card(title, value, icon, theme))
        
        # GitHub stats for dashboard
        save_svg(ASSETS_DIR / f'stat-commits-{theme}.svg', generate_stat_card('Total Commits', str(github_stats.get('total_commits', 0)), '📝', theme))
        save_svg(ASSETS_DIR / f'stat-prs-{theme}.svg', generate_stat_card('Pull Requests', str(github_stats.get('total_prs', 0)), '🔀', theme))
        
        # Project cards
        projects = [
            ('atmark', '📝', 'AtMark', 'Modern note-taking application'),
            ('tripbudget', '✈️', 'TripBudget', 'Travel expense tracking'),
            ('fitness', '💪', 'Fitness Dashboard', 'Track your fitness journey'),
            ('floatchat', '💬', 'Float Chat', 'Real-time messaging app'),
            ('mobapp', '📱', 'MOB-APP', 'Cross-platform mobile app'),
            ('medix', '🏥', 'Medix Manager', 'Healthcare management'),
        ]
        
        for proj_id, emoji, name, desc in projects:
            save_svg(ASSETS_DIR / f'project-{proj_id}-{theme}.svg', generate_project_card(name, emoji, desc, theme))
    
    print("\nAll assets generated successfully!")
    print(f"Assets saved to: {ASSETS_DIR.absolute()}")


if __name__ == '__main__':
    main()
