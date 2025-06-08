import re
import settings
import pandas as pd
from .ai import query_model
from .prompts import *
from .rfc import setup_rfc_datasets


def reference_search(
        rfcs_to_search, 
        referenced_rfcs, 
        use_llm: bool = False,
        rfc_only: bool = False,
        section_only: bool = False
    ):
    """ 
    Search for references.
    
    Args:
        rfcs_to_search: List of RFCs to search through.
        referenced_rfcs: List of RFCs to which references should be extracted.
    """

    rfc_df, section_df = setup_rfc_datasets(rfcs_to_search)
    references = []

    if use_llm:
        references = []
        for idx, row in section_df.iterrows():
            prompt = REFERENCE_EXTRACTION.format(section=row["content"])
            _, reference_list = query_model(
                settings.MODEL, 
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                parse_json=True
            )
            for reference in reference_list:
                rfc, section = reference
                if rfc in referenced_rfcs:
                    references.append({
                        "rfc": rfc,
                        "section": section,
                        "title": row["title"],
                        "content": row["content"],
                        "word_count": row["word_count"]
                    })
    else:
        for idx, row in section_df.iterrows():
            patterns = [
                r"Section (\d+(?:\.\d+)*) of \[RFC(\d{3,5})\]", 
                r"\[RFC(\d{3,5})\], Section (\d+(?:\.\d+)*)"
            ]

            if rfc_only:
                patterns.append(r"\[RFC(\d{3,5})\]()")

            if section_only:
                patterns.append(r"()Section (\d+(?:\.\d+)*)")

            for pattern in patterns:
                references.extend(re.findall(pattern, row["content"]))

    for reference in references:
        rfc, section = reference

        if rfc not in referenced_rfcs:
            continue

        reference = {
            "rfc": rfc,
            "section": section,
            "title": row["title"],
            "content": row["content"],
            "word_count": row["word_count"]
        }

    return references


def find_sections(
        section_df: pd.DataFrame, 
        keyword: str = "", 
        regex: str = "", 
        llm_prompt: str = ""):
    """ 
    Search for sections in RFCs.

    Args:
        section_df(pd.DataFrame): DataFrame containing section data.
        keyword(str, optional): Keyword to search for.
        regex(str, optional): Regular expression to search for.
        llm_prompt(str, optional): Description of which sections the LLM should search for.
    """
    sections = pd.DataFrame()

    if keyword:
        sections = pd.concat([sections, section_df[section_df["content"].str.contains(keyword, na=False)]], ignore_index=True)
    if regex:
        sections = pd.concat([sections, section_df[section_df["content"].str.contains(regex, na=False)]], ignore_index=True)
    
    if llm_prompt:
        for idx, section in section_df.iterrows():
            response, _ = query_model(
                settings.MODEL, 
                messages=[{
                    "role": "user",
                    "content": SEARCH_PROMPT.format(description=llm_prompt, section=section["content"])
                }])
            if "YES" in response:
                sections = pd.concat([sections, section_df.iloc[[idx]]], ignore_index=True)
    
    return sections


def extract_definition(
        section_df: pd.DataFrame, 
        keyword: str = ""
):
    """ 
    Search for definitions in RFC sections.
    Args:
        section_df(pd.DataFrame): DataFrame containing section data.
        keyword(str, optional): Keyword to search for. Without it, all definitions are returned.
    """
    definitions = []

    for _, row in section_df.iterrows():
        if not keyword or keyword in row["content"]:
            prompt = DEFINITION_EXTRACTION_PROMPT_KEYWORD.format(keyword=keyword, section=row["content"]) if keyword else DEFINITION_EXTRACTION_PROMPT.format(section=row["content"])
            _, definition_list = query_model(
                settings.MODEL, 
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                parse_json=True
            )
            for definition in definition_list:
                definitions.append({
                    "section": row["number"],
                    "title": row["title"],
                    "keyword": keyword,
                    "definition": definition
                })

    return definitions


def extract_context(
        section_df: pd.DataFrame, 
        context: str,
        keyword: str = "" 
        
):
    """
    Search for context in RFC sections.
    Args:
        section_df(pd.DataFrame): DataFrame containing section data.
        keyword(str, optional): Keyword for which context should be extracted.
        context(str, optional): Description of which context the llm should search for.
    """
    if keyword:
        return query_model(
            settings.MODEL, 
            messages=[{
                "role": "user",
                "content": CONTEXT_EXTRACTION_KEYWORD.format(keyword=keyword, context=context, section=section_df["content"])
            }],
            parse_json=True
        )[1]
    else:
        return query_model(
            settings.MODEL, 
            messages=[{
                "role": "user",
                "content": CONTEXT_EXTRACTION.format(context=context, section=section_df["content"])
            }],
            parse_json=True
        )[1]
