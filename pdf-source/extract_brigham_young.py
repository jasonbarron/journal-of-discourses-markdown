#!/usr/bin/env python3
"""
Extract all Brigham Young discourses from the complete Journal of Discourses file
"""
import re

def extract_brigham_young_discourses(input_file, output_file):
    """Extract all discourses by Brigham Young"""

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by discourse separators
    discourses = re.split(r'\n---\n', content)

    brigham_young_discourses = []
    volume_title = ""

    for i, discourse in enumerate(discourses):
        # First section might be the main title
        if i == 0:
            lines = discourse.split('\n')
            if lines and lines[0].startswith('#'):
                volume_title = lines[0]
            continue

        # Check if this discourse is by Brigham Young
        # Look for speaker line with BRIGHAM YOUNG
        if re.search(r'\*\*Speaker:\*\*.*BRIGHAM YOUNG', discourse, re.IGNORECASE):
            brigham_young_discourses.append(discourse)

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# BRIGHAM YOUNG DISCOURSES - JOURNAL OF DISCOURSES\n\n")
        f.write(f"Extracted from the complete Journal of Discourses (Volumes 1-26)\n\n")
        f.write(f"Total discourses by Brigham Young: {len(brigham_young_discourses)}\n\n")

        for discourse in brigham_young_discourses:
            f.write("---\n\n")
            f.write(discourse)
            f.write("\n\n")

    return len(brigham_young_discourses)

if __name__ == "__main__":
    input_file = "../Journal_of_Discourses_Complete.md"
    output_file = "../extraction-summaries/Brigham_Young_Discourses.md"

    print(f"Reading from: {input_file}")
    print(f"Writing to: {output_file}")

    count = extract_brigham_young_discourses(input_file, output_file)

    print(f"\nExtracted {count} discourses by Brigham Young")
    print(f"Output saved to: {output_file}")
