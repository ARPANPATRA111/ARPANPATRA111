#!/usr/bin/env python3
"""
Generate weekly activity SVG charts from WakaTime stats.
Creates both dark and light themed versions.
"""

import json
import os
from pathlib import Path


def generate_weekly_activity_svg(stats: dict, theme: str = "dark") -> str:
    """
    Generate a beautiful weekly activity bar chart SVG.
    
    Args:
        stats: Dictionary containing wakatime stats with daily_hours and daily_labels
        theme: Either "dark" or "light"
    
    Returns:
        SVG string
    """
    daily_hours = stats.get("daily_hours", [0] * 7)
    daily_labels = stats.get("daily_labels", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    
    # Ensure we have 7 days
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
    
    # Gradient colors for bars (beautiful rainbow-like gradients)
    bar_gradients = [
        ("ff6b6b", "ff8e53"),   # Coral to Orange
        ("feca57", "48dbfb"),   # Yellow to Cyan
        ("5f27cd", "48dbfb"),   # Purple to Cyan
        ("ff6b81", "a55eea"),   # Pink to Purple
        ("ff6348", "ffa502"),   # Red to Orange
        ("ffd32a", "7bed9f"),   # Yellow to Green
        ("70a1ff", "5352ed"),   # Light Blue to Blue
    ]
    
    # SVG dimensions
    width = 800
    height = 350
    padding = 60
    chart_width = width - (padding * 2)
    chart_height = height - (padding * 2) - 40  # Extra space for labels
    
    max_hours = max(daily_hours) if max(daily_hours) > 0 else 8
    max_hours = max(max_hours, 1)  # Avoid division by zero
    
    # Find most productive day
    max_idx = daily_hours.index(max(daily_hours)) if daily_hours else 0
    
    # Bar settings
    bar_width = chart_width / 7 * 0.6
    bar_spacing = chart_width / 7
    
    # Build SVG
    svg_parts = []
    
    # SVG header
    svg_parts.append(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>''')
    
    # Define gradients for each bar
    for i, (color1, color2) in enumerate(bar_gradients):
        svg_parts.append(f'''
    <linearGradient id="grad{i}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#{color1};stop-opacity:1" />
      <stop offset="100%" style="stop-color:#{color2};stop-opacity:1" />
    </linearGradient>''')
    
    svg_parts.append('''
  </defs>
  
  <!-- Background -->''')
    
    # Background
    svg_parts.append(f'''
  <rect width="{width}" height="{height}" fill="{bg_color}" rx="16" ry="16"/>
  <rect x="1" y="1" width="{width-2}" height="{height-2}" fill="none" stroke="{border_color}" stroke-width="1" rx="15" ry="15"/>''')
    
    # Title
    svg_parts.append(f'''
  
  <!-- Title -->
  <text x="{width/2}" y="35" text-anchor="middle" fill="{text_color}" font-family="'Segoe UI', system-ui, sans-serif" font-size="18" font-weight="600"></text>''')
    
    # Grid lines (horizontal)
    svg_parts.append(f'''
  
  <!-- Grid Lines -->''')
    
    for i in range(5):
        y = padding + 30 + (chart_height / 4 * i)
        hours_label = round(max_hours - (max_hours / 4 * i), 1)
        svg_parts.append(f'''
  <line x1="{padding}" y1="{y}" x2="{width - padding}" y2="{y}" stroke="{grid_color}" stroke-width="1" stroke-dasharray="5,5" opacity="0.5"/>
  <text x="{padding - 10}" y="{y + 4}" text-anchor="end" fill="{secondary_text}" font-family="'Segoe UI', system-ui, sans-serif" font-size="11">{hours_label}h</text>''')
    
    # Bars
    svg_parts.append(f'''
  
  <!-- Activity Bars -->''')
    
    for i, (label, hours) in enumerate(zip(daily_labels, daily_hours)):
        bar_x = padding + (bar_spacing * i) + (bar_spacing - bar_width) / 2
        bar_height = (hours / max_hours) * chart_height if max_hours > 0 else 0
        bar_y = padding + 30 + chart_height - bar_height
        
        # Minimum bar height for visibility
        if hours > 0 and bar_height < 10:
            bar_height = 10
            bar_y = padding + 30 + chart_height - bar_height
        
        gradient_id = i % len(bar_gradients)
        
        # Add star for most productive day
        star = "⭐" if i == max_idx and hours > 0 else ""
        
        if hours > 0:
            svg_parts.append(f'''
  <rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" fill="url(#grad{gradient_id})" rx="8" ry="8">
    <animate attributeName="height" from="0" to="{bar_height}" dur="0.5s" fill="freeze"/>
    <animate attributeName="y" from="{padding + 30 + chart_height}" to="{bar_y}" dur="0.5s" fill="freeze"/>
  </rect>''')
        
        # Hour labels above bars
        text_y = bar_y - 10 if hours > 0 else padding + 30 + chart_height - 20
        svg_parts.append(f'''
  <text x="{bar_x + bar_width/2}" y="{text_y}" text-anchor="middle" fill="{text_color}" font-family="'Segoe UI', system-ui, sans-serif" font-size="13" font-weight="500">{hours:.1f}h {star}</text>''')
        
        # Day labels below bars
        svg_parts.append(f'''
  <text x="{bar_x + bar_width/2}" y="{height - 20}" text-anchor="middle" fill="{secondary_text}" font-family="'Segoe UI', system-ui, sans-serif" font-size="12" font-weight="500">{label}</text>''')
    
    # Close SVG
    svg_parts.append('''
</svg>''')
    
    return "".join(svg_parts)


def main():
    """Main function to generate SVG assets."""
    # Get workspace paths
    workspace_root = Path(os.getcwd())
    stats_file = workspace_root / "wakatime_stats.json"
    assets_dir = workspace_root / "assets"
    
    # Ensure assets directory exists
    assets_dir.mkdir(exist_ok=True)
    
    # Load stats
    if stats_file.exists():
        with open(stats_file, "r", encoding="utf-8") as f:
            stats = json.load(f)
        print(f"✅ Loaded stats from {stats_file}")
    else:
        print(f"⚠️ Stats file not found at {stats_file}, using defaults")
        stats = {
            "daily_hours": [0, 0, 0, 0, 0, 0, 0],
            "daily_labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        }
    
    # Generate dark theme SVG
    dark_svg = generate_weekly_activity_svg(stats, theme="dark")
    dark_file = assets_dir / "weekly-activity-dark.svg"
    with open(dark_file, "w", encoding="utf-8") as f:
        f.write(dark_svg)
    print(f"✅ Generated {dark_file}")
    
    # Generate light theme SVG
    light_svg = generate_weekly_activity_svg(stats, theme="light")
    light_file = assets_dir / "weekly-activity-light.svg"
    with open(light_file, "w", encoding="utf-8") as f:
        f.write(light_svg)
    print(f"✅ Generated {light_file}")
    
    print("\n🎉 All assets generated successfully!")


if __name__ == "__main__":
    main()
