import pydantic
import settings
import pandas as pd
from typing import List
from .ai import query_model
from .prompts import *
from .index import HFSTIndex


def search_sections(
        sections: pd.DataFrame,
        keywords: List[str] = [],
        regex: str = "",
        search_query: str = "",
        use_llm: bool = False, 
        num_sections: int = 10,
        similarity_threshold: float = 100.0
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

    if keywords:
        result = pd.DataFrame()
        for keyword in keywords:
            result = pd.concat([result, sections[sections["content"].str.contains(keyword, na=False)]], ignore_index=True)

        return result
    if regex:
        return sections[sections["content"].str.contains(regex, na=False)]
    
    if search_query and use_llm:
            selected_sections = []

            for idx, section in sections.iterrows():
                response, _ = query_model(
                    settings.MODEL, 
                    messages=[{
                        "role": "user",
                        "content": SEARCH_PROMPT_TEMPLATE.format(description=search_query, section=section["content"])
                    }],
                    options={
                        "num_ctx": 100000
                    })
                
                if "YES" in response.content: selected_sections.append(idx)
                    
            return sections.loc[selected_sections]
    elif search_query:
        index = HFSTIndex(sections, index_src_col="content", overwrite_existing=True)
        results, scores = index.semantic_search(search_query, k=num_sections)
        results = pd.DataFrame(results[0])
        scores = pd.DataFrame(scores[0], columns=["score"])

        joined = pd.concat([results, scores], axis=1)
        return joined[joined.score < similarity_threshold]
    else:
        return pd.DataFrame()


def extract_context(
        section: pd.DataFrame, 
        filter: pydantic.BaseModel 
):
    """
    Search for context in RFC sections.
    Args:
        sections(pd.DataFrame): DataFrame containing section data.
        filter(str, optional): Description of which context the llm should search for.
    """

    _, json_output = query_model(
        settings.MODEL, 
        messages=[{
            "role": "user",
            "content": FILTER_PROMPT_TEMPLATE.format(info=filter.model_json_schema(), section=section["content"])
        }],
        parse_json=True
    )

    return json_output


def filter_and_analyze_sections(
    sections: pd.DataFrame,
    filter: pydantic.BaseModel
):
    # Apply filter to each section
    sections['analysis'] = sections.apply(extract_context, axis=1, args=(filter,))

    sections_exploded = sections.explode('analysis')
    sections_exploded = sections.dropna(subset=["analysis"])
    analysis_df = pd.json_normalize(sections_exploded['analysis'])

    # Reset the index of both DataFrames to ensure a clean join
    sections_exploded.reset_index(drop=True, inplace=True)
    analysis_df.reset_index(drop=True, inplace=True)

    # Concatenate the original data (minus the unneeded columns) with the new analysis data
    return pd.concat([sections_exploded.drop(columns=['analysis']), analysis_df], axis=1)

