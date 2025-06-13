import re
import requests
import pandas as pd


def parse_rfc_header(text):
    header_text = text.split("\n\n", 1)[0]  # Get the header part
    lines = header_text.strip().splitlines()
    
    rfc_info = {
        "group": None,
        "rfc_number": None,
        "obsoletes": [],
        "updates": [],
        "category": None,
        "date": None,
        "authors": [],  # List of (name, affiliation)
    }

    for line in lines:
        # Split line into two columns based on position
        left, right = re.split(r"\s{2,}", line, 1)[0:2] if "  " in line else (line.strip(), "")

        # Parse left side
        if left.startswith("Request for Comments:"):
            rfc_info["rfc_number"] = int(left.split(":")[1].strip())
        elif left.startswith("Obsoletes:"):
            rfc_info["obsoletes"] = [
                int(x.strip()) for x in left.split(":")[1].split(",") if x.strip().isdigit()
            ]
        elif left.startswith("Updates:"):
            rfc_info["updates"] = [
                int(x.strip()) for x in left.split(":")[1].split(",") if x.strip().isdigit()
            ]
        elif left.startswith("Published"):
            rfc_info["date"] = left.split(":")[1].strip()
        elif left.startswith("Category:"):
            rfc_info["category"] = left.split(":")[1].strip()
        elif left.startswith("ISSN:"):
            rfc_info["issn"] = left.split(":")[1].strip()
        else:
            if left.strip():
                rfc_info["group"] = left.strip()

        # Collect right column lines (authors + affiliations)
        if right:
            # Detect date as the last line if it looks like "Month Year"
            if re.match(r'^[A-Za-z]+\s+\d{4}$', right):
                rfc_info["date"] = right
            else:
                rfc_info["authors"].append(right)

    return rfc_info


def clean_up_rfc_text(text):
    result = ""
    lines = text.splitlines()
    last_line_was_empty = False


    for line in lines:
        # Skip empty lines
        if not line.strip():
            if last_line_was_empty:
                continue
            last_line_was_empty = True
            result += "\n"
            continue
        else:
            last_line_was_empty = False
            
        if re.search(r"\[Page \d+\]", line):
            continue

        if re.search(r"^RFC \d{4}", line) and re.search(r"January|February|March|April|May|June|July|August|September|October|November|December", line):
            continue
        
        result += line + "\n"
        
    return result


def extract_sections(text):
    section_titles = []
    try:
        parts = re.split(r"1.\s*Introduction\s+\n", text)
        pre = parts[0]
        post = "1. Introduction\n" + "1. Introduction\n".join(parts[1:])
        table_of_contents = pre.split("Table of Contents")[1]

        for row in re.split(r"\d+\n", table_of_contents):
            if match := re.search(r"(\d+\.(?:\d+\.)*)\s+(.*?)(?=(?:\s*\d+\.)?\.\s*)*$)", row, re.DOTALL):
                number = match.group(1)
                title = re.sub(r"\s+", " ", re.split(r"\s*\.*$", match.group(2))[0]).strip()
                section_titles.append((number, title))
    except Exception as e:
        section_titles = re.findall(r"\n(\d+\.(?:\d+\.)*)\s+(.*)\n", text)

    sections = []
    for idx, (number, title) in enumerate(section_titles):
        pattern = re.escape(number) + r'\s*' + r'[\s\r\n]*'.join(re.escape(char) for char in title if char not in ["\n", "\r"])  # Allow spaces between characters
        try:
            content = re.split(pattern, post)[1]
        except Exception:
            try:
                alternative_pattern = r'\s*' + r'[\s\r\n]*'.join(re.escape(char) for char in title if char not in ["\n", "\r"])  
                content = re.split(alternative_pattern, post)[1]
            except Exception:
                continue
        if idx < len(section_titles) - 1:
            pattern = re.escape(section_titles[idx + 1][0]) + r'\s*' + r'[\s\r\n]*'.join(re.escape(char) for char in section_titles[idx + 1][1] if char not in ["\n", "\r"])
            content = re.split(pattern, content)[0]
        sections.append({
            "number": number, 
            "title": title, 
            "content": content, 
            "word_count": len(re.split(r"\s+", content))
        })

    return sections


def setup_rfc_datasets(rfc_ids):
    rfc_data = []
    section_data = []

    for rfc in rfc_ids:
        # Download RFC text
        text = requests.get(f"https://www.ietf.org/rfc/rfc{rfc}.txt").text
        # Remove Page Numbers etc. and split sections
        text = clean_up_rfc_text(text)
        # Parse RFC header to extract obsoletes/updates etc.
        header_info = parse_rfc_header(text)
        header_info["rfc_number"] = rfc
        header_info["text"] = text

        rfc_data.append(header_info)

        # Split text into sections
        sections = extract_sections(text)
        
        for section in sections:
            section["rfc"] = rfc
            section["updated_by"] = []
            section["obsoleted_by"] = []
            section_data.append(section)

    rfc_df = pd.DataFrame(rfc_data)
    section_df = pd.DataFrame(section_data)

    for _, rfc_info in rfc_df.iterrows():
        # Identify updated and obsoleted sections
        for updated in rfc_info["updates"]:
            old_sections = section_df[section_df.rfc == updated]
            for idx, old_section in old_sections.iterrows():
                for _, potential_new_section in section_df[section_df.rfc == rfc_info["rfc_number"]].iterrows():
                    if old_section["number"] in potential_new_section["title"] or old_section["number"] in potential_new_section["content"]:
                        # Mark as updated.
                        section_df.loc[idx, "updated_by"].append((rfc_info["rfc_number"], potential_new_section["number"]))                        

        for obsoleted in rfc_info["obsoletes"]:
            old_sections = section_df[section_df.rfc == obsoleted]
            for idx, old_section in old_sections.iterrows():
                for _, potential_new_section in section_df[section_df.rfc == rfc_info["rfc_number"]].iterrows():
                    if old_section["title"] == potential_new_section["title"]:
                        section_df.loc[idx, "obsoleted_by"].append((rfc_info["rfc_number"], potential_new_section["number"]))

    return rfc_df, section_df