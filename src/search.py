import pydantic
import settings
import pandas as pd
from typing import List
from .ai import query_model
from .prompts import *
from .index import HFSTIndex


def search_sections(
        sections: pd.DataFrame,
        keyword: List[str] = [],
        regex: str = "",
        search_query: str = "",
        use_llm: bool = False, 
        num_sections: int = 10,
        similarity_threshold: float = 0.0
):
    """ 
    Search for sections in RFCs.

    Args:
        sections(pd.DataFrame): DataFrame containing section data.
        keyword(str, optional): Keyword to search for.
        regex(str, optional): Regular expression to search for.
        search_query(str, optional): Either description of contents for LLM search or input for semantic search
        use_llm(bool, optional): Whether to use llm search or semantic search if search_query is provided
        num_sections(int, optional): Number of semantically similar sections to extract
        similarity_threshold(float, optional): Threshold for semantic similarity used to filter sections
    """

    if keyword:
        return pd.concat([sections, sections[sections["content"].str.contains(keyword, na=False)]], ignore_index=True)
    if regex:
        return pd.concat([sections, sections[sections["content"].str.contains(regex, na=False)]], ignore_index=True)
    
    if search_query and use_llm:
            selected_sections = []

            for idx, section in sections.iterrows():
                response, _ = query_model(
                    settings.MODEL, 
                    messages=[{
                        "role": "user",
                        "content": SEARCH_PROMPT_TEMPLATE.format(description=search_query, section=section["content"])
                    }])
                if "YES" in response: selected_sections.append(idx)
                    
            return sections[selected_sections]
    elif search_query:
        index = HFSTIndex(sections, index_src_col="content")
        results, scores = index.semantic_search(search_query, k=num_sections)

        return 
    else:
        return pd.DataFrame()


def extract_context(
        sections: pd.DataFrame, 
        filter: pydantic.BaseModel 
):
    """
    Search for context in RFC sections.
    Args:
        sections(pd.DataFrame): DataFrame containing section data.
        filter(str, optional): Description of which context the llm should search for.
    """

    return query_model(
        settings.MODEL, 
        messages=[{
            "role": "user",
            "content": FILTER_PROMPT_TEMPLATE.format(info=filter.model_json_schema(), section=sections["content"])
        }],
        format=filter,
        parse_json=True
    )[1]
