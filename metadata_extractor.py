"""
Module d'extraction des métadonnées depuis les fichiers n8n.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)


def extract_basic_metadata(node_json_path: Path) -> Dict[str, Any]:
    """
    Lit et parse le fichier *.node.json pour extraire les métadonnées de base.

    Args:
        node_json_path: Chemin vers le fichier *.node.json

    Returns:
        Dictionnaire contenant les métadonnées de base du noeud
    """
    try:
        with open(node_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extraire les champs pertinents
        metadata = {
            "node_id": data.get("node", ""),
            "node_version": data.get("nodeVersion", ""),
            "codex_version": data.get("codexVersion", ""),
            "details": data.get("details", ""),
            "categories": data.get("categories", []),
            "class_name": data.get("node", "").split(".")[-1] if "." in data.get("node", "") else data.get("node", ""),
        }

        # Extraire les ressources de documentation
        resources = data.get("resources", {})
        metadata["documentation_links"] = []

        # Documentation des credentials
        cred_docs = resources.get("credentialDocumentation", [])
        for doc in cred_docs:
            if isinstance(doc, dict) and "url" in doc:
                metadata["documentation_links"].append(doc["url"])

        # Documentation principale
        primary_docs = resources.get("primaryDocumentation", [])
        for doc in primary_docs:
            if isinstance(doc, dict) and "url" in doc:
                metadata["documentation_links"].append(doc["url"])

        return metadata

    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing JSON dans {node_json_path}: {e}")
        return {"error": f"Invalid JSON: {e}"}
    except Exception as e:
        logger.error(f"Erreur lors de la lecture de {node_json_path}: {e}")
        return {"error": str(e)}


def extract_input_parameters(node_path: Path) -> List[Dict[str, Any]]:
    """
    Analyse le fichier *.node.js pour récupérer la propriété description.properties
    qui contient la définition des paramètres d'entrée configurables.

    Args:
        node_path: Chemin vers le répertoire du noeud ou vers le fichier *.node.js

    Returns:
        Liste de dictionnaires décrivant chaque paramètre d'entrée (displayName, name, type, required, description)
    """
    print(f"[DEBUG] extract_input_parameters called with {node_path}")
    try:
        # Determine if we got a file or a directory
        if node_path.is_file() and node_path.name.endswith('.node.js'):
            node_js_path = node_path
            node_dir = node_path.parent
        else:
            # Treat as directory
            node_dir = node_path
            logger.debug(f"Searching for .node.js files in {node_dir}")
            # Find the .node.js file in the node directory
            node_js_files = list(node_dir.glob("*.node.js"))
            if not node_js_files:
                logger.debug(f"No .node.js files found via glob in {node_dir}, trying rglob")
                node_js_files = list(node_dir.rglob("*.node.js"))
            if not node_js_files:
                logger.debug(f"Aucun fichier .node.js trouvé dans {node_dir}")
                return []
            node_js_path = node_js_files[0]
            logger.debug(f"Using .node.js file: {node_js_path}")

        # Create a}")

        # Create a temporary JavaScript file to extract description.properties via Node.js
        js_code = '''
const path = process.argv[1];
try {
  const mod = require(path);
  let description = null;
  // Try to find exported class with description on prototype
  for (const key in mod) {
    if (mod.hasOwnProperty(key) && typeof mod[key] === 'function' && mod[key].prototype && mod[key].prototype.description) {
      description = mod[key].prototype.description;
      break;
    }
  }
  if (!description && typeof mod.description !== 'undefined') {
    description = mod.description;
  }
  if (!description || !Array.isArray(description.properties)) {
    console.log(JSON.stringify([]));
    process.exit(0);
  }
  const props = description.properties.map(p => ({
    displayName: p.displayName ?? p.name ?? '',
    name: p.name ?? '',
    type: p.type ?? '',
    required: p.required ?? false,
    description: p.description ?? ''
  }));
  console.log(JSON.stringify(props));
} catch (err) {
  console.error(err.message);
  console.log(JSON.stringify([]));
  process.exit(1);
}
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as tmp:
            tmp.write(js_code)
            tmp_path = tmp.name
        # Run node script
        result = subprocess.run(['node', tmp_path, str(node_js_path)], capture_output=True, text=True, timeout=10)
        os.unlink(tmp_path)
        if result.returncode != 0:
            logger.warning(f"Node extraction failed for {node_js_path}: {result.stderr}")
            return []
        try:
            props = json.loads(result.stdout.strip())
            if isinstance(props, list):
                logger.debug(f"Extracted {len(props)} input parameters from {node_js_path.name}")
                return props
            else:
                logger.warning(f"Unexpected output from node extraction: {props}")
                return []
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from node extraction: {e}")
            return []
    except Exception as e:
        logger.error(f"Error extracting input parameters from {node_path}: {e}")
        return []


def extract_output_schemas(schema_dir: Path) -> Dict[str, Any]:
    """
    Parcourt récursivement le répertoire __schema__ pour extraire tous les schémas de sortie.

    Args:
        schema_dir: Chemin vers le répertoire __schema__

    Returns:
        Dictionnaire structuré contenant les schémas par version/ressource/opération
    """
    if not schema_dir.exists() or not schema_dir.is_dir():
        return {}

    schemas = {}

    try:
        # Parcourir : __schema__/<version>/<ressource>/<operation>.json
        for version_dir in schema_dir.iterdir():
            if not version_dir.is_dir():
                continue

            version = version_dir.name
            schemas[version] = {}

            for resource_dir in version_dir.iterdir():
                if not resource_dir.is_dir():
                    continue

                resource = resource_dir.name
                schemas[version][resource] = {}

                for schema_file in resource_dir.glob("*.json"):
                    operation = schema_file.stem  # Nom du fichier sans extension
                    try:
                        with open(schema_file, 'r', encoding='utf-8') as f:
                            schema_data = json.load(f)
                        schemas[version][resource][operation] = schema_data
                    except json.JSONDecodeError as e:
                        logger.warning(f"Erreur de parsing JSON dans {schema_file}: {e}")
                    except Exception as e:
                        logger.warning(f"Erreur lors de la lecture de {schema_file}: {e}")

    except Exception as e:
        logger.error(f"Erreur lors du parcours du ré schéma {schema_dir}: {e}")

    return schemas