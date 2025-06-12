# rfc-analysis

## Setup

Clone repository
Install requirements.txt

- Setup LLM in settings.py by setting MODEL to either one created using setup_llm() from ai.py, allows accessing Anthropic, Google and OpenAI API through langchain, or a model name if a local ollama instance is running, see [here]().
- Decide which set of RFCs to analyze, set RFCs to a list in settings.py or enter single one when using the tool
- templates.py constains examples of keywords, regexes and descriptions used in our analysis of rpki-rfcs, for application to other rfcs entries in the same format can be added and will then be available in the tool

Run main.py

## Functionality

- Search for RFC sections in the selected RFC database containing either a keyword or regular expression, or matching a description of contents provided to the LLM (e.g., search for all sections containing ASN.1 definitions)
- Skip through sections, highlight references, allow opening referenced sections in split screen, as well as comparing to updated/obsoleted sections + diff in text
- Use LLM to filter candidate sections based on provided template, describe patterns to look for in a section LLM decides if they are contained and highlights the accodring text in the display
- save results during analysis

## Screenshots

