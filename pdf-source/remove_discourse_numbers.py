#!/usr/bin/env python3
"""
Remove 'Discourse X' numbering from the Brigham Young discourses file
"""
import re

def remove_discourse_numbers(file_path):
    """Remove all '## Discourse X' lines from the file"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove all lines that match "## Discourse X" pattern
    # This regex matches lines like "## Discourse 1", "## Discourse 123", etc.
    content = re.sub(r'^## Discourse \d+\n\n', '', content, flags=re.MULTILINE)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Removed discourse numbering from: {file_path}")

if __name__ == "__main__":
    file_path = "../extraction-summaries/Brigham_Young_Discourses.md"
    remove_discourse_numbers(file_path)
    print("Done!")
