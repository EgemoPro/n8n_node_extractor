# n8n_node_extractor

A Python utility to extract and index metadata from n8n nodes (both native and custom) to create an LLM‑optimized reference for generating n8n workflows.

## Features

- Discovers **all** `*.node.json` files in an n8n installation (native nodes from `@n8n/n8n-nodes-base` and any custom nodes installed via npm or placed elsewhere under the n8n root)
- Extracts:
  - Basic metadata (`node_id`, `version`, `categories`, `description`, documentation links)
  - Input parameters from the corresponding `.node.js` file (display name, name, type, required flag, description)
  - Output schemas from the `__schema__` directory (if present)
- Normalizes and enriches the data:
  - Infers complexity (simple/moderate/complex) based on number of input parameters
  - Detects probable trigger nodes
  - Determines accepted/generic input types and produced output types
  - Generates a concise LLM‑friendly summary (`llm_summary`)
- Generates multiple output formats:
  - **JSON** – complete index with metadata and nodes list (ideal for programmatic consumption)
  - **Markdown** – human‑readable documentation with a table of contents, sections per category, and detailed tables for each node
  - **LLM Prompt** – a ready‑to‑paste prompt that instructs an LLM on how to use the nodes, includes a categorized index, examples of common chains, and tips for diversified workflow generation
- Handles errors gracefully: a single node that fails to parse will not stop the whole extraction.
- Configurable via command‑line arguments:
  - `--n8n-path`: root of the n8n installation (default points to a typical nvm‑based install)
  - `--output-dir`: where to write the generated files
  - `--formats`: choose which output formats to generate (`json`, `markdown`, `llm-prompt`)
  - `--limit`: process only the first N nodes (useful for testing)
  - `--log-level`: control verbosity

## Installation

The script only depends on the Python standard library and a working Node.js executable (used to safely extract parameters from `.node.js` files). No extra Python packages are required.

```bash
# Clone the repository
git clone https://github.com/EgemoPro/n8n_node_extractor.git
cd n8n_node_extractor

# (Optional) create a virtual environment
python3 -m venv venv
source venv/bin/activate
```

Make sure `node` is in your PATH (the script calls `node` to run a small helper script).

## Usage

```bash
python3 main.py \
    --n8n-path /path/to/your/n8n \
    --output-dir ./n8n_nodes_index \
    --formats json markdown llm-prompt \
    --limit 0 \
    --log-level INFO
```

### Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--n8n-path` | Filesystem path to the n8n installation (the directory that contains `package.json`, `node_modules`, etc.) | `/home/venom/.nvm/versions/node/v24.4.1/lib/node_modules/n8n` |
| `--output-dir` | Directory where the generated files will be written | `./n8n_nodes_index` |
| `--formats` | Space‑separated list of output formats to generate. Choose from `json`, `markdown`, `llm-prompt` | all three |
| `--limit` | Maximum number of nodes to process. `0` means no limit. | `0` |
| `--log-level` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |

### Example: Quick test on 5 nodes

```bash
python3 main.py --limit 5 --log-level DEBUG
```

This will create a folder `n8n_nodes_index` containing:
- `n8n_nodes_complete.json`
- `n8n_nodes_documentation.md`
- `n8n_llm_prompt.txt`

## Output Details

### JSON (`n8n_nodes_complete.json`)

```json
{
  "metadata": {
    "generated_by": "n8n_node_extractor",
    "version": "1.0.0",
    "total_nodes": 432,
    "nodes_by_category": {
      "Development": 86,
      "Communication": 87,
      // …
    }
  },
  "nodes": [
    {
      "node_name": "httpRequest",
      "node_id": "n8n-nodes-base.httpRequest",
      "version": "1.0",
      "codex_version": "1.0",
      "category": "Communication",
      "all_categories": ["Communication"],
      "description": "Makes HTTP requests",
      "documentation": {
        "short": "Makes HTTP requests",
        "links": [
          "https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.httpRequest/"
        ]
      },
      "input_parameters": [
        {
          "displayName": "URL",
          "name": "url",
          "type": "string",
          "required": true,
          "description": "The URL to request"
        },
        // …
      ],
      "output_schemas": {
        "v1.0.0": {
          "main": {
            "type": "object",
            // …
          }
        }
      },
      // enriched fields:
      "execution_context": { … },
      "complexity": "moderate",
      "is_probable_trigger": false,
      "accepts_generic_input": true,
      "produces_common_output": true,
      "llm_summary": "Noeud: httpRequest - Communication - Description: Makes HTTP requests - Paramètres requis: URL, Method - Produit: object, array ..."
    }
    // …
  ]
}
```

### Markdown (`n8n_nodes_documentation.md`)

- A table of contents listing each category with node counts.
- For each category, a section with a table per node showing:
  - Name and category
  - Description
  - Input parameters (Name, Type, Required, Description)
  - Available output schema versions/resources
  - Documentation links (up to three shown)
- Clear separation with horizontal rules.

### LLM Prompt (`n8n_llm_prompt.txt`

- Begins with instructions for the LLM on how to generate valid n8n workflows.
- Presents an index of nodes grouped by category, each entry containing:
  - Node name and category
  - LLM‑friendly summary
  - List of required parameters
  - Data types produced
- Includes examples of common chains (e.g., “HTTP Request → Function → Google Sheets”) and tips for diversifying workflows.

## How It Works

1. **Discovery** (`discovery.find_native_nodes`) walks the whole `--n8n-path` tree for `*.node.json` files, filters out test/documentation folders, and returns the list.
2. For each node file:
   - Basic metadata is read directly from the `.node.json` (`metadata_extractor.extract_basic_metadata`).
   - The node’s directory is located (`discovery.get_node_directory`).
   - Input parameters are extracted by spawning a Node.js process that loads the corresponding `.node.js` file and reads `description.properties` (`metadata_extractor.extract_input_parameters`).
   - Output schemas are read from the `__schema__` subdirectory, if present (`metadata_extractor.extract_output_schemas`).
   - Data is normalized into an intermediate structure (`data_structurer.build_node_info`).
   - The structure is enriched with inferred fields useful for LLMs (`data_structurer.infer_data_types`).
3. After processing all nodes, the collected data is handed to the output generators:
   - `output_generator.generate_json_output`
   - `output_generator.generate_markdown_output`
   - `output_generator.generate_llm_prompt`

## Design Notes

- **Robustness**: Extraction of input parameters relies on a temporary Node.js script that runs in a subprocess; any error in a particular node’s `.node.js` is caught and results in an empty parameter list for that node, but processing continues.
- **Extensibility**: Adding new output formats or enrichment steps only requires touching the respective generator or the `infer_data_types` function.
- **No External Python Dependencies**: Keeps the tool lightweight and easy to run in any environment with Python 3.8+ and Node.js ≥ 12.

## Limitations & Future Work

- The current input‑parameter extraction works well for the typical n8n node structure (exported class with a `description` property). Highly dynamic or unconventional node implementations might need a more sophisticated JavaScript parser.
- Only basic JSON Schema types are extracted from output schemas; facets like `format`, `pattern`, `minimum`, `maximum`, or `enum` are not yet propagated to the LLM context.
- The tool assumes the Node.js version used to run n8n is compatible with the helper script (ES2020‑ish). If you encounter syntax errors, please open an issue.

## License

This project is released under the MIT License – see the `LICENSE` file for details.

## Acknowledgements

- Built for the n8n community to empower AI‑assisted workflow creation.
- Inspired by the need for a structured, LLM‑readable catalogue of n8n nodes.

---

Enjoy generating smarter n8n workflows with LLMs!