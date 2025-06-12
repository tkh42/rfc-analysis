import re
import requests
import pandas as pd
from sentence_transformers import SentenceTransformer, util

def parse_rfc_header(text):
    header_text = text.split("\n\n", 1)[0]
    lines = header_text.strip().splitlines()
    
    rfc_info = {
        "group": None, "rfc_number": None, "obsoletes": [],
        "updates": [], "category": None, "date": None, "authors": [],
    }

    for line in lines:
        parts = re.split(r"\s{2,}", line.strip(), 1)
        left = parts[0]
        right = parts[1] if len(parts) > 1 else ""

        if left.startswith("Request for Comments:"):
            rfc_info["rfc_number"] = int(re.search(r'\d+', left).group())
        elif left.startswith("Obsoletes:"):
            rfc_info["obsoletes"] = [int(x) for x in re.findall(r'\d+', left)]
        elif left.startswith("Updates:"):
            rfc_info["updates"] = [int(x) for x in re.findall(r'\d+', left)]
        elif left.startswith("Published:") or left.startswith("Date:"):
             rfc_info["date"] = left.split(":", 1)[1].strip()
        elif left.startswith("Category:"):
            rfc_info["category"] = left.split(":", 1)[1].strip()
        elif left.startswith("ISSN:"):
            rfc_info["issn"] = left.split(":", 1)[1].strip()
        elif not any(key in left for key in ["Request for Comments", "Obsoletes", "Updates", "Published", "Category", "ISSN"]):
            if left.strip():
                rfc_info["group"] = left.strip()

        if right and not re.match(r'^[A-Za-z]+\s+\d{4}$', right):
            rfc_info["authors"].append(right)
        elif right and re.match(r'^[A-Za-z]+\s+\d{4}$', right):
             rfc_info["date"] = right

    return rfc_info


def clean_up_rfc_text(text):
    text = re.sub(r'.*\f.*', '', text) # Remove form feeds and lines containing them
    text = re.sub(r'RFC \d+.*[A-Za-z]+\s+\d{4}\n', '', text) # Remove headers
    text = re.sub(r'\[Page \d+\]', '', text) # Remove page markers
    return text.strip()


def extract_sections(text):
    # Regex to find section numbers and titles, accommodating multi-line titles
    pattern = re.compile(r"^\s*(\d+(\.\d+)*)\.?\s+([A-Z][^\n]*(\n(?!\s*\d+\.\d+\s)[^\n]*)*)", re.MULTILINE)
    
    titles = [(match.group(1), re.sub(r'\s+', ' ', match.group(3).strip())) for match in pattern.finditer(text)]
    
    sections = []
    for i, (number, title) in enumerate(titles):
        start_pos = re.search(re.escape(title), text).end()
        
        end_pos = None
        if i + 1 < len(titles):
            next_number, next_title = titles[i+1]
            # Search for the next title's start
            end_match = re.search(r"^\s*" + re.escape(next_number) + r"\.?\s+" + re.escape(next_title), text[start_pos:], re.MULTILINE)
            if end_match:
                end_pos = start_pos + end_match.start()

        content = text[start_pos:end_pos].strip()
        sections.append({
            "number": number, "title": title, "content": content,
            "word_count": len(content.split())
        })
    return sections


def setup_rfc_datasets(rfc_ids):
    rfc_data, section_data = [], []
    for rfc in rfc_ids:
        try:
            response = requests.get(f"https://www.ietf.org/rfc/rfc{rfc}.txt")
            response.raise_for_status()
            text = response.text
        except requests.RequestException as e:
            print(f"Failed to download RFC {rfc}: {e}")
            continue

        header_info = parse_rfc_header(text)
        text = clean_up_rfc_text(text)
        header_info.update({"rfc_number": rfc, "text": text})
        rfc_data.append(header_info)

        for section in extract_sections(text):
            section.update({"rfc": rfc, "updated_by": [], "obsoleted_by": []})
            section_data.append(section)

    if not section_data:
        return pd.DataFrame(), pd.DataFrame()

    rfc_df = pd.DataFrame(rfc_data)
    section_df = pd.DataFrame(section_data)
    
    # Use a semantic model to find relationships
    model = SentenceTransformer('all-MiniLM-L6-v2')

    for _, rfc_info in rfc_df.iterrows():
        for updated_rfc in rfc_info["updates"]:
            old_df = section_df[section_df.rfc == updated_rfc]
            new_df = section_df[section_df.rfc == rfc_info["rfc_number"]]
            if old_df.empty or new_df.empty: continue
            
            old_embeddings = model.encode(old_df['content'].tolist(), convert_to_tensor=True)
            new_embeddings = model.encode(new_df['content'].tolist(), convert_to_tensor=True)
            
            cos_scores = util.cos_sim(old_embeddings, new_embeddings)
            for i in range(len(old_df)):
                best_match_idx = cos_scores[i].argmax().item()
                if cos_scores[i, best_match_idx] > 0.6: # Similarity threshold
                    old_section_idx = old_df.index[i]
                    new_section_num = new_df.iloc[best_match_idx]['number']
                    section_df.loc[old_section_idx, "updated_by"].append((rfc_info["rfc_number"], new_section_num))

    return rfc_df, section_df