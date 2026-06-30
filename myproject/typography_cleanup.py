import os
import re

BASE_DIR = r"c:\Users\rudra\Downloads\E-Commerce-Website\myproject"

def process_html_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 1. Remove font imports
    content = re.sub(r"@import url\('https://fonts\.googleapis\.com/css2\?family=Bangers&family=Comic\+Neue.*?\'\);", "", content)
    
    # 2. Remove font-family rules
    content = re.sub(r"font-family:\s*'Bangers',\s*cursive;?", "", content)
    content = re.sub(r"font-family:\s*'Comic Neue',\s*cursive;?", "", content)
    content = re.sub(r"font-family:\s*'Comic Neue',\s*sans-serif;?", "", content)
    
    # 3. Remove text-strokes and text-shadows
    content = re.sub(r"-webkit-text-stroke:.*?;", "", content)
    content = re.sub(r"text-shadow:.*?;", "", content)

    # 4. Inject global CSS link before </head> if not already there
    link_tag = """<link rel="stylesheet" href="{% static 'shop/css/global.css' %}">"""
    if link_tag not in content and "</head>" in content.lower():
        # Case insensitive replace for </head>
        content = re.sub(r"(</head>)", f"    {link_tag}\n\\1", content, flags=re.IGNORECASE)

    # 5. Ensure {% load static %} is at the top if we injected the link
    if link_tag in content and "{% load static %}" not in content:
        content = "{% load static %}\n" + content

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {filepath}")

def main():
    for root, dirs, files in os.walk(BASE_DIR):
        # Skip env/venv/static/media dirs
        if any(skip in root for skip in ['venv', '.venv', 'env', '.git', 'static', 'media']):
            continue
            
        for file in files:
            if file.endswith('.html'):
                process_html_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
