#!/usr/bin/env python3
"""
Script de test pour vérifier le fonctionnement de l'extracteur de noeuds n8n
sur un petit sous-ensemble de noeuds.
"""

import sys
from pathlib import Path

# Ajouter le répertoire courant au path pour importer nos modules
sys.path.insert(0, str(Path(__file__).parent))

from discovery import find_native_nodes, get_node_directory
from metadata_extractor import extract_basic_metadata, extract_input_parameters, extract_output_schemas
from data_structurer import build_node_info, infer_data_types

def test_single_node(node_json_path: Path, n8n_root: Path) -> None:
    """
    Test l'extraction sur un seul noeud et affiche les résultats.
    """
    print(f"\n=== Test du noeud: {node_json_path.name} ===")

    # 1. Métadonnées de base
    basic_metadata = extract_basic_metadata(node_json_path)
    print(f"Métadonnées de base: {basic_metadata.get('node_id', 'N/A')}")
    print(f"Catégories: {basic_metadata.get('categories', [])}")

    # 2. Répertoire du noeud
    node_dir = get_node_directory(node_json_path)
    print(f"Répertoire du noeud: {node_dir.name}")

    # 3. Paramètres d'entrée
    # Chercher le fichier .node.js correspondant
    node_js_path = node_dir / f"{basic_metadata.get('class_name', 'unknown')}.node.js"
    if not node_js_path.exists():
        node_js_path = node_dir / f"{node_json_path.stem}.node.js"
    if not node_js_path.exists():
        # Fallback: chercher tout fichier .node.js dans le répertoire du nœud
        possible = list(node_dir.glob("*.node.js"))
        if possible:
            node_js_path = possible[0]
        else:
            node_js_path = None

    input_parameters = []
    if node_js_path and node_js_path.exists():
        input_parameters = extract_input_parameters(node_js_path)
        print(f"Paramètres d'entrée trouvés: {len(input_parameters)}")
        for param in input_parameters[:3]:  # Montrer les 3 premiers
            print(f"  - {param.get('display_name', param.get('name'))}: {param.get('type')} (requis: {param.get('required', False)})")
    else:
        print("Fichier .node.js non trouvé")

    # 4. Schémas de sortie
    schema_dir = node_dir / "__schema__"
    output_schemas = {}
    if schema_dir.exists():
        output_schemas = extract_output_schemas(schema_dir)
        print(f"Schémas de sortie trouvés: {len(output_schemas)} versions")
        for version, resources in output_schemas.items():
            print(f"  Version {version}: {len(resources)} ressources")
    else:
        print("Pas de répertoire __schema__")

    # 5. Structuration complète
    try:
        node_info = build_node_info(basic_metadata, input_parameters, output_schemas)
        node_info = infer_data_types(node_info)
        print(f"\nNoeud structuré:")
        print(f"  Nom: {node_info.get('node_name')}")
        print(f"  Catégorie: {node_info.get('category')}")
        print(f"  Complexité: {node_info.get('complexity')}")
        print(f"  Résumé LLM: {node_info.get('llm_summary', 'N/A')[:100]}...")
    except Exception as e:
        print(f"Erreur lors de la structuration: {e}")

def main():
    """Fonction principale du test."""
    n8n_path = Path("/home/venom/.nvm/versions/node/v24.4.1/lib/node_modules/n8n")

    if not n8n_path.exists():
        print(f"ERREUR: Chemin n8n non trouvé: {n8n_path}")
        return 1

    print(f"Recherche des noeuds n8n dans: {n8n_path}")

    # Trouver les noeuds
    node_json_paths = find_native_nodes(n8n_path)
    print(f"Trouvé {len(node_json_paths)} noeuds potentiels")

    # Tester sur les 3 premiers noeuds
    test_count = min(3, len(node_json_paths))
    print(f"\nTest sur les {test_count} premiers noeuds...")

    for i in range(test_count):
        test_single_node(node_json_paths[i], n8n_path)

    print(f"\nTest terminé.")
    return 0

if __name__ == "__main__":
    sys.exit(main())