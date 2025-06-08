CONTEXT_EXTRACTION = """
You will be given a section of an RFC.
Read the text carefully and then create a JSON object filled in with excerpts from the text filling in the following fields:

{description}


Section:

{section}
"""


CONTEXT_EXTRACTION_KEYWORD = """
You will be given a section of an RFC.
Read the text carefully and then create a JSON object filled in with excerpts from the text related to the keyword "{keyword}" filling in the following fields:

{description}


Section:

{section}
"""


DEFINITION_EXTRACTION_PROMPT_KEYWORD = """
You will be given a section of an RFC.
Read the text carefully and extract all keyword definitions found in the text.

Return a JSON list with an object like this with the definition of the keyword "{keyword}":

{{
    "keyword": "", # The keyword that is defined
    "definition": "", # The definition of the keyword
}}

If there is no definition please return an empty list.

Keyword definitions can either occur as natural langue definitions, like this:

...

or as more formal definitions, e.g. as an ASN.1 type definition like this.

...

For such a definition, please not only extract the whole definition but also each individual field, 
your output for the example should look like this:

...
"""

DEFINITION_EXTRACTION_PROMPT = """
You will be given a section of an RFC.
Read the text carefully and extract all keyword definitions found in the text.

Return a JSON list with an object like this for each definition you find:

{{
    "keyword": "", # The keyword that is defined
    "definition": "", # The definition of the keyword
}}

If there are no definitions please return an empty list.

Keyword definitions can either occur as natural langue definitions, like this:

...

or as more formal definitions, e.g. as an ASN.1 type definition like this.

...

For such a definition, please not only extract the whole definition but also each individual field, 
your output for the example should look like this:

...
"""



SEARCH_PROMPT = """ 
You will be given a section of an RFC.

If the section's contents match the following description:

{description}

Please respond with "YES". Otherwise, respond with "NO".

Section:

{section}
"""


REFERENCE_EXTRACTION = """
You will be given a section of an RFC.
Read the text carefully and extract all references found in the text.
Return a JSON list with an object like this for each reference you find:

{{
    "rfc": "", # Number of the referenced RFC (if included)
    "section": "", # Section of the referenced RFC (if included)
}}

If there are no references please return an empty list.

Section:

{section}
"""