# RFC-Analysis

**RFC-Analysis** is a suite of tools designed to simplify the analysis and exploration of RFCs (Request for Comments). It assists in identifying critical sections, exploring relationships and references, and performing structured filtering—leveraging LLMs (Large Language Models) for enhanced semantic understanding.

---

## 🛠️ Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/rfc-analysis.git
cd rfc-analysis
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the LLM

Edit `settings.py`:

* Set the `MODEL` variable:

  * For remote models (Anthropic, Google, OpenAI), use `setup_llm()` from `ai.py` (based on [LangChain](https://github.com/langchain-ai/langchain)).
  * For local models (e.g., via Ollama), provide the model name as a string (e.g., `"llama3"`). See [Ollama Setup](#) for more details.


## 🔍 Functionality

### 📑 Section Search

Search for RFC sections using:

* **Keywords or Regexes**
  Locate relevant sections containing specific terms or matching patterns.

* **Semantic Similarity**
  Find semantically similar sections based on sentence embeddings (e.g., compare section text with other similar content).

* **LLM-Based Descriptions**
  Provide a natural language description (e.g., "Sections containing ASN.1 definitions")—the LLM determines which sections match.

> 🧠 Examples of search queries are available in `templates.py`.

---

### 🧮 Section Filtering

Combine search with **LLM-based filtering** for structured analysis.

* Define filter templates in `templates.py` using `pydantic.BaseModel`.
* The LLM attempts to extract the specified information from the section; if the relevant data is missing, the section is filtered out, the other sections will be returned with the structured LLM output as additional information.

**Example: Filtering for Availability Requirements**

```python
class AvailabilityRequirement(BaseModel):
    requirement: Annotated[str, Field(description="Requirement on the availability of a service: bit rates, timeouts, general expectations, error codes")]
```

🔎 Sections mentioning availability are processed by the LLM. If availability requirements are found, they are extracted.

---

## 📄 License

MIT License. See `LICENSE` file for details.


