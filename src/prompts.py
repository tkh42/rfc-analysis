SEARCH_PROMPT_TEMPLATE = """ 
    # ROLE

    You are a research assistant specialized in information extraction from RFC texts.

    # TASK

    You will be provided with an RFC section, 
    your task is to decide whether the section contains

    {description}

    If yes, please include YES in your answer, else NO.

    # INPUT

    Here is the section you should analyze:

    {section}
"""

FILTER_PROMPT_TEMPLATE = """
    # ROLE

    You are a research assistant specialized in information extraction from RFC texts.

    # TASK

    You will be provided with an RFC section, your task is to search the text for the following information:

    {info}

    You should return a JSON list with objects adhering to the schema above where the fields are filled in with excerpts
    from the text matching the description. If there are multiple matching excerpts return multiple objects, if the
    required information is not in the text, return an empty list.

    # INPUT

    {section}
"""