import os
import json
import ollama
import requests

from typing import List, Union
from pydantic import BaseModel, Field
from parse_llm_code import extract_code_blocks, extract_first_code
from langchain_core.tools import StructuredTool
from langchain_community.llms.huggingface_hub import HuggingFaceHub
from langchain_community.chat_models.huggingface import ChatHuggingFace
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import Tool, initialize_agent, AgentType
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser


def setup_langchain_llm(
        name: str,
        api_key: str = "",
        args: object = {}
):
    if "openai" in name:
        assert api_key, "Selecting an openai model requires api_key."
        model = ChatOpenAI(
            openai_api_key=api_key,
            model_name=name.split("/")[-1],
            **args
        )
    elif "anthropic" in name:
        assert api_key, "Selecting an anthropic model requires an api_key."
        os.environ["ANTHROPIC_API_KEY"] = api_key
        model = ChatAnthropic(
            model=name.split("/")[-1]
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
    start = text.index("[")
    last = rindex(text, "]")

    return json.loads(text[start:last + 1])


"""    
    model: (required) the model name
    prompt: the prompt to generate a response for
    suffix: the text after the model response
    images: (optional) a list of base64-encoded images (for multimodal models such as llava)
    format: the format to return a response in. Format can be json or a JSON schema
    options: additional model parameters listed in the documentation for the Modelfile such as temperature
    system: system message to (overrides what is defined in the Modelfile)
    template: the prompt template to use (overrides what is defined in the Modelfile)
    stream: if false the response will be returned as a single response object, rather than a stream of objects
    raw: if true no formatting will be applied to the prompt. You may choose to use the raw parameter if you are specifying a full templated prompt in your request to the API
    keep_alive: controls how long the model will stay loaded into memory following the request (default: 5m)
    context (deprecated): the context parameter returned from a previous request to /generate, this can be used to keep a short conversational memory
"""

"""
    mirostat 	Enable Mirostat sampling for controlling perplexity. (default: 0, 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0) 	int 	mirostat 0
    mirostat_eta 	Influences how quickly the algorithm responds to feedback from the generated text. A lower learning rate will result in slower adjustments, while a higher learning rate will make the algorithm more responsive. (Default: 0.1) 	float 	mirostat_eta 0.1
    mirostat_tau 	Controls the balance between coherence and diversity of the output. A lower value will result in more focused and coherent text. (Default: 5.0) 	float 	mirostat_tau 5.0
    num_ctx 	Sets the size of the context window used to generate the next token. (Default: 2048) int 	num_ctx 4096
    repeat_last_n 	Sets how far back for the model to look back to prevent repetition. (Default: 64, 0 = disabled, -1 = num_ctx) 	int 	repeat_last_n 64
    repeat_penalty 	Sets how strongly to penalize repetitions. A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 0.9) will be more lenient. (Default: 1.1) 	float 	repeat_penalty 1.1
    temperature 	The temperature of the model. Increasing the temperature will make the model answer more creatively. (Default: 0.8) 	float 	temperature 0.7
    seed 	Sets the random number seed to use for generation. Setting this to a specific number will make the model generate the same text for the same prompt. (Default: 0) 	int 	seed 42
    stop 	Sets the stop sequences to use. When this pattern is encountered the LLM will stop generating text and return. Multiple stop patterns may be set by specifying multiple separate stop parameters in a modelfile. 	string 	stop "AI assistant:"
    num_predict 	Maximum number of tokens to predict when generating text. (Default: -1, infinite generation) 	int 	num_predict 42
    top_k 	Reduces the probability of generating nonsense. A higher value (e.g. 100) will give more diverse answers, while a lower value (e.g. 10) will be more conservative. (Default: 40) 	int top_k 40
    top_p 	Works together with top-k. A higher value (e.g., 0.95) will lead to more diverse text, while a lower value (e.g., 0.5) will generate more focused and conservative text. (Default: 0.9) 	float 	top_p 0.9
    min_p 	Alternative to the top_p, and aims to ensure a balance of quality and variety. The parameter p represents the minimum probability for a token to be considered, relative to the probability of the most likely token. For example, with p=0.05 and the most likely token having a probability of 0.9, logits with a value less than 0.045 are filtered out. (Default: 0.0) 	float 	min_p 0.05
"""
def query_model(
        model, 
        messages,
        parse_code: bool = False,
        parse_json: bool = False,
        schema: BaseModel = None,
        tools: List = [],
        options: dict = {}
    ):
    available_functions = { tool.__name__: tool for tool in tools }
    assert not (len(tools) > 0) or not parse_json,  "Tools can only be used in non-parsing mode" 

    if type(model) == str:
        if schema:
            response = ollama.chat(
                model,
                messages=messages,
                tools=tools,
                options=options,
                schema=schema
            )
        else:
            response = ollama.chat(
                model,
                messages=messages,
                tools=tools,
                options=options
            )

        if parse_json:
            try:
                parser = JsonOutputParser(pydantic_model=schema)
                json_output = parser.parse(response.message.content)
            except Exception:
                try:
                    json_output = parse_json_list_from_text(response.message.content)
                except Exception:
                    json_output = []
            return response.message, json_output
        elif parse_code:
            code = extract_first_code(response.message.content)
            return response.message, code
        else:
            tool_results = []
            for tool in response.message.tool_calls or []:
                function_to_call = available_functions.get(tool.function.name)
                if function_to_call:
                    tool_results.append(function_to_call(**tool.function.arguments))

            return response.message, tool_results
    else:
        if tools:
            tools = [StructuredTool.from_function(tool, parse_docstring=True) for tool in tools]

            model_with_tools = model.bind_tools(tools)
            response = model_with_tools.invoke(messages)

            tool_outputs = []
            for tool in response.tool_calls:
                function_to_call = available_functions.get(tool["name"])
                if function_to_call:
                    tool_outputs.append(function_to_call(**tool["args"]))

            return response, tool_outputs
        else:
            if schema:
                model = model.with_structured_output(schema)
            
            response = model.invoke(messages)
    
            if parse_json:
                try:
                    parser = JsonOutputParser(pydantic_model=schema)
                    return response, parser.parse(response.content)
                except Exception:
                    return response, []
            elif parse_code:
                code = extract_first_code(response.content)
                return response, code
            else:
                return response, None
