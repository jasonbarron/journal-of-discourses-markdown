#!/usr/bin/env python3
"""
Clean extraction of Journal of Discourses PDF to Markdown
Uses structural analysis rather than keyword matching
"""
import re
import pypdf

def extract_pdf_pages(pdf_path):
    """Extract text from each page"""
    reader = pypdf.PdfReader(pdf_path)
    pages = []

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        pages.append({
            'number': page_num + 1,
            'text': text,
            'lines': text.split('\n')
        })

    return pages

def is_page_header_footer(line):
    """Check if line is a page header or footer to remove"""
    line = line.strip()

    if not line:
        return True

    if line.isdigit():
        return True

    if re.match(r'^\d+\s+JOURNAL OF DISCOURSES\.$', line):
        return True

    if line == "JOURNAL OF DISCOURSES.":
        return True

    # Running header with page number: "TITLE. ###"
    if re.match(r'^[A-Z\s\-\',]+\.\s+\d+\s*$', line):
        return True

    return False

def clean_page_text(page_lines):
    """Clean a single page's lines"""
    cleaned = []
    for line in page_lines:
        line = line.strip()
        if not is_page_header_footer(line):
            cleaned.append(line)
    return cleaned

def fix_hyphenation(lines):
    """Fix hyphenated words split across lines"""
    fixed = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if i + 1 < len(lines):
            match = re.search(r'(\w+)-\s*$', line)
            if match:
                next_line = lines[i + 1].strip()
                if next_line and next_line[0].islower():
                    word_start = match.group(1)
                    line = line[:match.start()] + word_start + next_line
                    i += 2
                    fixed.append(line)
                    continue

        fixed.append(line)
        i += 1

    return fixed

def find_discourse_boundaries(lines):
    """
    Find discourse boundaries by looking for ALL CAPS blocks with speaker names.
    More flexible than keyword matching.
    """
    boundaries = []
    last_boundary_end = -1  # Track last found boundary to avoid overlaps

    i = 0
    while i < len(lines):
        # Skip if we're too close to the last boundary (avoid duplicates)
        if i < last_boundary_end + 3:
            i += 1
            continue
        line = lines[i].strip()

        # Skip empty lines, "Amen", and other non-content
        if line in ["", "AMEN", "AMEN."]:
            i += 1
            continue

        # Check if this line is ALL CAPS and looks like it could be part of a title/header
        if not line.isupper() or len(line) < 5:
            i += 1
            continue

        # Skip running headers with page numbers
        if re.search(r'\.\s+\d{2,3}$', line):
            i += 1
            continue

        # Found an ALL CAPS line - collect the full title block
        title_lines = []
        start_idx = i

        # Look backward to see if there are more title lines (skip Amen)
        lookback = i - 1
        while lookback >= 0:
            prev_line = lines[lookback].strip()
            # Skip empty lines and "Amen"
            if prev_line in ["", "AMEN", "AMEN."]:
                lookback -= 1
                continue
            # Add valid title line (but never include AMEN even if part of line)
            if prev_line.isupper() and len(prev_line) > 3 and not re.search(r'\.\s+\d{2,3}$', prev_line):
                # Don't add lines that contain AMEN
                if "AMEN" not in prev_line:
                    title_lines.insert(0, prev_line)
                    start_idx = lookback
                lookback -= 1
            else:
                break

        # Now collect forward
        j = i
        while j < len(lines):
            curr_line = lines[j].strip()

            # Skip if it's a running header or empty
            if not curr_line or re.search(r'\.\s+\d{2,3}$', curr_line):
                j += 1
                if j - i > 10:  # Don't look too far
                    break
                continue

            # If line is all caps, add to title block (but skip AMEN)
            if curr_line.isupper():
                # Don't add lines containing AMEN
                if curr_line not in title_lines and "AMEN" not in curr_line:
                    title_lines.append(curr_line)
                # Skip AMEN lines entirely
                elif "AMEN" in curr_line:
                    j += 1
                    continue
                j += 1

                # Check if we've found a speaker indicator
                speaker_found = has_speaker_indicator(curr_line)
                location_found = has_location_indicator(curr_line)

                # If we have both title and speaker/location info, this is likely a discourse
                if speaker_found or location_found:
                    # MUST have "REPORTED BY" as strong verification
                    # (unless it's a legal document with "BEFORE THE HON.")
                    verified = False
                    for k in range(j, min(j + 8, len(lines))):
                        check_line = lines[k].strip()
                        if 'REPORTED BY' in check_line:
                            verified = True
                            break
                        # Alternative: legal documents with judge
                        if 'BEFORE THE HON.' in check_line and 'JUDGE' in check_line:
                            verified = True
                            break

                    if verified and len(title_lines) > 0:
                        boundaries.append({
                            'start': start_idx,
                            'title_end': j,
                            'title_lines': title_lines
                        })
                        last_boundary_end = j
                        i = j
                        break
            else:
                # Hit a non-caps line, check if we have enough for a discourse
                if len(title_lines) >= 1 and any(has_speaker_indicator(tl) for tl in title_lines):
                    # Still need to verify with REPORTED BY
                    verified = False
                    for k in range(j, min(j + 8, len(lines))):
                        check_line = lines[k].strip()
                        if 'REPORTED BY' in check_line or ('BEFORE THE HON.' in check_line and 'JUDGE' in check_line):
                            verified = True
                            break
                    if verified:
                        boundaries.append({
                            'start': start_idx,
                            'title_end': j,
                            'title_lines': title_lines
                        })
                        last_boundary_end = j
                break

            # Don't look too far
            if j - i > 15:
                break

        i = j if j > i else i + 1

    return boundaries

def has_speaker_indicator(line):
    """Check if line contains a speaker indicator"""
    speaker_patterns = [
        r'\bBY\s+(?:PRESIDENT|ELDER|HON\.|ESQ\.|MR\.|PROFESSOR)',
        r'\bPRESIDENT\s+[A-Z]',
        r'\bELDER\s+[A-Z]',
        r'\bHON\.\s+[A-Z]',
        r'\bESQ\.\s*,',
        r'\bDELIVERED\s+BY',
        r'\bBEFORE\s+THE\s+HON\.',
    ]
    for pattern in speaker_patterns:
        if re.search(pattern, line):
            return True
    return False

def has_location_indicator(line):
    """Check if line contains a location indicator"""
    location_patterns = [
        r'\bDELIVERED\s+(?:IN|AT)',
        r'\bGREAT\s+SALT\s+LAKE',
        r'\bTABERNACLE',
    ]
    for pattern in location_patterns:
        if re.search(pattern, line):
            return True
    return False

def has_date(line):
    """Check if line contains a date"""
    return bool(re.search(r'[A-Z]+\s+\d{1,2}(?:TH|ST|ND|RD)?,\s+\d{4}', line))

def extract_metadata_from_block(lines, start_idx, end_idx):
    """Extract title, speaker, location, date from a discourse block"""
    metadata = {
        'title': '',
        'speaker': '',
        'location': '',
        'date': '',
        'reporter': ''
    }

    # Collect all the metadata lines
    block_lines = [lines[i].strip() for i in range(start_idx, min(end_idx + 5, len(lines)))
                   if lines[i].strip()]

    title_parts = []
    speaker_parts = []
    location_parts = []

    for line in block_lines:
        # Check for reporter
        if line.startswith('REPORTED BY'):
            metadata['reporter'] = line.replace('REPORTED BY', '').strip().rstrip('.')
            break

        # Check for date
        date_match = re.search(r'([A-Z]+\s+\d{1,2}(?:TH|ST|ND|RD)?,\s+\d{4})', line)
        if date_match and not metadata['date']:
            metadata['date'] = date_match.group(1)

        # Check if this line has speaker info
        if has_speaker_indicator(line):
            speaker_parts.append(line)
        elif has_location_indicator(line):
            location_parts.append(line)
        elif not metadata['date'] and line.isupper() and 'BEFORE' not in line:
            # Likely part of title (but skip AMEN)
            if not re.search(r'\.\s+\d{2,3}$', line) and 'AMEN' not in line:  # Not a running header or AMEN
                title_parts.append(line.rstrip('.'))

    # Parse speaker from speaker_parts
    speaker_text = ' '.join(speaker_parts)
    speaker = extract_speaker_name(speaker_text)
    if speaker:
        metadata['speaker'] = normalize_speaker_name(speaker)

    # Parse location
    location_text = ' '.join(location_parts + speaker_parts)
    location, extracted_date = extract_location_and_date(location_text)
    if location:
        metadata['location'] = location
    if extracted_date and not metadata['date']:
        metadata['date'] = extracted_date

    # Build title from remaining parts
    if title_parts:
        metadata['title'] = ' '.join(title_parts)

    return metadata

def extract_speaker_name(text):
    """Extract speaker name from text"""
    # Try various patterns
    patterns = [
        r'BY\s+((?:PRESIDENT|ELDER|HON\.|ESQ\.|MR\.|PROFESSOR)\s+[A-Z\s\.]+?)(?:,|\s+DELIVERED|\s+BEFORE|\s+ON)',
        r'((?:PRESIDENT|ELDER|HON\.|ESQ\.)\s+[A-Z\s\.]+?)(?:,|\s+DELIVERED|\s+BEFORE)',
        r'BY\s+([A-Z\s\.]+?)(?:,|\s+DELIVERED|\s+BEFORE)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip().rstrip(',.')

    return ''

def normalize_speaker_name(speaker):
    """Normalize speaker names for consistency"""
    # Fix spacing issues (e.g., "G EORGE A. S MITH" -> "GEORGE A. SMITH")
    speaker = re.sub(r'(?<=\s)([A-Z])\s+([A-Z]{2,})', r'\1\2', speaker)
    speaker = re.sub(r'(?<=\.)(\s*)([A-Z])\s+([A-Z]{2,})', r'\1\2\3', speaker)

    # Normalize abbreviated names
    speaker = re.sub(r'\bB\.\s*YOUNG\b', 'BRIGHAM YOUNG', speaker)
    speaker = re.sub(r'H\.\s*C\.\s*KIMBALL', 'HEBER C. KIMBALL', speaker)
    speaker = speaker.replace('H. C. KIMBALL', 'HEBER C. KIMBALL')
    speaker = re.sub(r'\bP\.\s*P\.\s*PRATT\b', 'PARLEY P. PRATT', speaker)

    # Add ELDER if missing title
    if speaker == "PARLEY P. PRATT":
        speaker = "ELDER " + speaker

    # Normalize titles
    speaker = speaker.replace("PROFESSOR ", "ELDER ")
    speaker = speaker.replace("MR. ", "ELDER ")
    speaker = speaker.replace("HON. ", "ELDER ")
    speaker = speaker.replace("ESQ.", "ESQ.,")  # Keep ESQ. but normalize punctuation
    if "ESQ.," in speaker:
        speaker = speaker.replace("ESQ.,", "").strip()
        speaker = "ELDER " + speaker if not speaker.startswith("ELDER") else speaker

    return speaker.strip()

def extract_location_and_date(text):
    """Extract location and date from text"""
    location = ''
    date = ''

    # Extract date first
    date_match = re.search(r'([A-Z]+\s+\d{1,2}(?:TH|ST|ND|RD)?,\s+\d{4})', text)
    if date_match:
        date = date_match.group(1)
        # Remove date from text for location parsing
        text = text.replace(date, '')

    # Extract location
    # Look for pattern after DELIVERED/AT/IN/BEFORE
    location_match = re.search(r'(?:DELIVERED|AT|IN|BEFORE)\s+(?:THE\s+)?([A-Z\s,\.]+?)(?=,\s*[A-Z]+\s+\d|$|REPORTED)', text)
    if location_match:
        location = location_match.group(1).strip()

    # Clean up location
    location = re.sub(r'\s*,\s*\.', '', location)
    location = re.sub(r',\s*,', ',', location)
    location = re.sub(r'\s+', ' ', location)
    location = location.strip(',. ')

    return location, date

def find_all_discourses(lines):
    """Find all discourse boundaries"""
    boundaries = find_discourse_boundaries(lines)

    discourses = []
    for i, boundary in enumerate(boundaries):
        # Determine content range
        content_start = boundary['title_end']
        content_end = boundaries[i + 1]['start'] if i + 1 < len(boundaries) else len(lines)

        # Extract metadata
        metadata = extract_metadata_from_block(lines, boundary['start'], boundary['title_end'])

        # Get content
        content_lines = lines[content_start:content_end]

        # Remove title repetitions and any ALL CAPS lines from title block
        if metadata['title']:
            # Split title into parts for better matching
            title_parts = set()
            title_parts.add(metadata['title'])
            title_parts.add(metadata['title'] + '.')
            # Also add individual lines from title in case they appear
            for part in metadata['title'].split():
                if len(part) > 3:
                    title_parts.add(part)

            # Filter out title lines and any ALL CAPS lines at the start
            filtered_lines = []
            started_content = False
            for l in content_lines:
                line_stripped = l.strip()
                # Once we hit lowercase content, we've started the actual discourse
                if not line_stripped.isupper() or started_content:
                    started_content = True
                    # Still check if it's an exact title match
                    if line_stripped not in [metadata['title'], metadata['title'] + '.']:
                        filtered_lines.append(l)
                # Skip ALL CAPS lines that might be title remnants
                elif not any(part in line_stripped for part in ['REPORTED BY', 'DELIVERED']):
                    continue
            content_lines = filtered_lines

        # Join paragraphs
        content = join_paragraphs(content_lines)

        discourses.append({
            'metadata': metadata,
            'content': content
        })

    return discourses

def join_paragraphs(lines):
    """Join lines into paragraphs, preserving original paragraph breaks"""
    paragraphs = []
    current = []

    for i, line in enumerate(lines):
        line = line.strip()

        if not line:
            # Empty line = definite paragraph break
            if current:
                para_text = ' '.join(current)
                para_text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', para_text)
                paragraphs.append(para_text)
                current = []
        else:
            # Check if this should start a new paragraph
            # New paragraph if previous line ended with sentence punctuation
            # AND this line starts with capital or is indented content
            if current:
                prev_line = current[-1]
                # Check if previous ended with sentence-ending punctuation
                ends_sentence = prev_line.rstrip().endswith(('.', '!', '?', ':', ';'))
                # Check if current starts with capital or quotation
                starts_new = line and line[0].isupper() or line.startswith('"')

                # If previous ended sentence and current starts new, consider paragraph break
                if ends_sentence and starts_new and len(current) > 2:
                    # Save current paragraph
                    para_text = ' '.join(current)
                    para_text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', para_text)
                    paragraphs.append(para_text)
                    current = [line]
                else:
                    current.append(line)
            else:
                current.append(line)

    if current:
        para_text = ' '.join(current)
        para_text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', para_text)
        paragraphs.append(para_text)

    return '\n\n'.join(paragraphs)

def format_markdown(discourses):
    """Format as markdown"""
    md = "# JOURNAL OF DISCOURSES - VOLUME 1\n\n"

    for i, discourse in enumerate(discourses, 1):
        meta = discourse['metadata']
        content = discourse['content']

        md += "---\n\n"
        md += f"## Discourse {i}\n\n"

        if meta['title']:
            md += f"# {meta['title']}\n\n"

        if meta['speaker']:
            md += f"**Speaker:** {meta['speaker']}  \n"

        if meta['location'] or meta['date']:
            md += "**Delivered:** "
            if meta['location']:
                md += meta['location']
            if meta['location'] and meta['date']:
                md += ", "
            if meta['date']:
                md += meta['date']
            md += "  \n"

        if meta['reporter']:
            md += f"**Reported by:** {meta['reporter']}  \n"

        md += f"\n{content}\n\n"

    return md

def main():
    import sys

    # Get PDF filename from command line, or default to JoD01.pdf
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    else:
        pdf_file = 'JoD01.pdf'

    # Determine volume number and output filename
    import re
    match = re.search(r'JoD(\d+)', pdf_file)
    if match:
        volume_num = match.group(1)
        output_file = f'JoD{volume_num}_clean.md'
        volume_title = f"JOURNAL OF DISCOURSES - VOLUME {volume_num}"
    else:
        output_file = pdf_file.replace('.pdf', '_clean.md')
        volume_title = "JOURNAL OF DISCOURSES"

    print(f"Processing {pdf_file}...")
    print("Extracting pages from PDF...")
    pages = extract_pdf_pages(pdf_file)
    print(f"Extracted {len(pages)} pages")

    print("Cleaning page text...")
    all_lines = []
    for page in pages:
        cleaned = clean_page_text(page['lines'])
        all_lines.extend(cleaned)

    print(f"Total lines after cleaning: {len(all_lines)}")

    print("Fixing hyphenation...")
    all_lines = fix_hyphenation(all_lines)

    print("Finding discourses using structural analysis...")
    discourses = find_all_discourses(all_lines)
    print(f"Found {len(discourses)} discourses")

    print("Formatting markdown...")
    # Update format_markdown to accept volume title
    markdown = format_markdown_with_title(discourses, volume_title)

    print(f"Writing output to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)

    print(f"\nDone! Created {output_file} with {len(discourses)} discourses")

def format_markdown_with_title(discourses, volume_title):
    """Format as markdown with custom volume title"""
    md = f"# {volume_title}\n\n"

    for i, discourse in enumerate(discourses, 1):
        meta = discourse['metadata']
        content = discourse['content']

        md += "---\n\n"
        md += f"## Discourse {i}\n\n"

        if meta['title']:
            md += f"# {meta['title']}\n\n"

        if meta['speaker']:
            md += f"**Speaker:** {meta['speaker']}  \n"

        if meta['location'] or meta['date']:
            md += "**Delivered:** "
            if meta['location']:
                md += meta['location']
            if meta['location'] and meta['date']:
                md += ", "
            if meta['date']:
                md += meta['date']
            md += "  \n"

        if meta['reporter']:
            md += f"**Reported by:** {meta['reporter']}  \n"

        md += f"\n{content}\n\n"

    return md

if __name__ == "__main__":
    main()
