# src/ai.py

import os
import json
import ollama

from typing import List
from pydantic import BaseModel
from parse_llm_code import extract_first_code
from langchain_core.tools import StructuredTool
from langchain_community.llms.huggingface_hub import HuggingFaceHub
from langchain_community.chat_models.huggingface import ChatHuggingFace
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser


def setup_llm(
        name: str,
        api_key: str = "",
        args: object = {}
):
    """
    Sets up a LangChain chat model based on the provided name.
    """
    if "openai" in name:
        assert api_key, "Selecting an OpenAI model requires an api_key."
        model = ChatOpenAI(
            openai_api_key=api_key,
            model_name=name.split("/")[-1],
            **args
        )
    elif "anthropic" in name:
        assert api_key, "Selecting an Anthropic model requires an api_key."
        os.environ["ANTHROPIC_API_KEY"] = api_key
        model = ChatAnthropic(
            model=name.split("/")[-1]
        )
    elif "google" in name or "gemini" in name:
        assert api_key, "Selecting a Google model requires an api_key."
        os.environ["GOOGLE_API_KEY"] = api_key
        model = ChatGoogleGenerativeAI(
            model=name.split("/")[-1],
            **args
        )
    else:
        llm = HuggingFaceHub(
            repo_id=name,
            task="text-generation",
            model_kwargs=args
        )
        model = ChatHuggingFace(llm)

    return model


def rindex(array, value) -> int:
    if value not in array:
        return -1
    i = array[::-1].index(value)
    return len(array) - i - 1


def parse_json_list_from_text(text):
    start = text.find("[")
    last = rindex(list(text), "]")
    if start == -1 or last == -1:
        return []
    return json.loads(text[start:last + 1])


def query_model(
        model,
        messages,
        parse_code: bool = False,
        parse_json: bool = False,
        schema: BaseModel = None,
        tools: List = [],
        options: dict = {}
    ):
    """
    Queries an LLM and handles response parsing, tool calls, and JSON validation.
    """
    available_functions = {tool.__name__: tool for tool in tools}
    assert not (len(tools) > 0 and parse_json), "Tools and JSON parsing cannot be used simultaneously."

    if isinstance(model, str):  # Ollama case
        response = ollama.chat(
            model=model,
            messages=messages,
            tools=tools if tools else [],
            format='json' if schema else '',
            options=options
        )
        message = response['message']

        if schema:
            try:
                # The 'content' is already a JSON string when format='json'
                json_output = json.loads(message['content'])
                if schema:
                    validated_output = schema.model_validate(json_output)
                    return message, validated_output
                return message, json_output
            except Exception as e:
                print(f"JSON/Pydantic parsing failed: {e}")
                return message, None
        elif parse_json:
            try:
                json_output = parse_json_list_from_text(message['content'])
                return message, json_output
            except Exception:
                return message, []
        elif parse_code:
            code = extract_first_code(message['content'])
            return message, code
        
        tool_results = []
        if message.get('tool_calls'):
            for tool_call in message['tool_calls']:
                function_to_call = available_functions.get(tool_call['function']['name'])
                if function_to_call:
                    args = tool_call['function']['arguments']
                    tool_results.append(function_to_call(**args))
        return message, tool_results

    else:  # LangChain case
        if tools:
            lc_tools = [StructuredTool.from_function(tool, parse_docstring=True) for tool in tools]
            model_with_tools = model.bind_tools(lc_tools)
            response = model_with_tools.invoke(messages)
            
            tool_outputs = []
            for tool_call in response.tool_calls:
                function_to_call = available_functions.get(tool_call["name"])
                if function_to_call:
                    tool_outputs.append(function_to_call(**tool_call["args"]))
            return response, tool_outputs
        
        if schema:
            model = model.with_structured_output(schema)
        
        response = model.invoke(messages)

        if schema:
            # The response is already a Pydantic object
            return response, response
        elif parse_json:
            try:
                # For LangChain, content is typically a string
                json_output = json.loads(response.content)
                return response, json_output
            except (json.JSONDecodeError, AttributeError):
                 return response, []
        elif parse_code:
            code = extract_first_code(response.content)
            return response, code
        else:
            return response, None