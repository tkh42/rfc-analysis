from pydantic import BaseModel, Field
from typing import Annotated, List, Optional


# Keywords and Keyword Lists

KEYWORDS = {
    "AVAILABILITY": ["timeout", "availab", "drop", "alive", "denial", "degrade"],
    "X.509_TERMS": ["element", "attribute", "field"],
    "CER_USAGE": ["CER"],
    "RFC_RELATION": ["differ", "relate"]
}


# Regular Expressions

REGEXES = {
    "RFC_REFERENCES": r'\[\d{4}\]'
}


# Search Queries
# Description of the content of the section we are looking for, "Section contains, ..."

SEARCH_QUERIES = {
    "DEFINITIONS": """ 
        defitions for any keywords, either in natural language, 
        e.g., meaning of a keyword, description of its structure or contents, 
        or as formal ASN.1 definition like:

        Person DEFINITIONS ::= BEGIN PersonRecord ::= SEQUENCE { name UTF8String, age INTEGER } END

    """
}


# Filters
# Pydantic models describing what information should be in a selected section


class AvailabilityRequirement(BaseModel):
    requirement: Annotated[str, Field(description="A requirement on the availability of a service, such as bit rates, timeouts, or error conditions; but also general descriptions.")]

class TermUsage(BaseModel):
    keyword: Annotated[str, Field(description="Keyword the terms 'Field', 'Attribute' or 'Element' refer to in this section.")]

class CERUsage(BaseModel):
    usage: Annotated[str, Field(description="Requirement on whether CER MUST/SHOULD be supported")]
 

class RFCRelation(BaseModel):
    relationship: Annotated[str, Field(description="Text describing how the contents of the section relate/differ to the contents/specification of a referenced section.")]