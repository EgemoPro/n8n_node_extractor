#!/usr/bin/env python3
"""
Script pour extraire et indexer les métadonnées des noeuds n8n (natifs et personnalisés)
afin de créer un référentiel optimisé pour la génération de workflows par LLM.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import json

# Import des modules locaux
from discovery import find_native_nodes, get_node_directory
from metadata_extractor import (
    extract_basic_metadata,
    extract_input_parameters,
    extract_output_schemas
)
from data_structurer import build_node_info, infer_data_types
from output_generator import (
    generate_json_output,
    generate_markdown_output,
    generate_llm_prompt
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_node(node_json_path: Path, n8n_root: Path) -> Dict[str, Any]:
    """
    Traite un seul noeud n8n et extrait toutes ses métadonnées.

    Args:
        node_json_path: Chemin vers le fichier *.node.json du noeud
        n8n_root: Racine de l'installation n8n

    Returns:
        Dictionnaire contenant toutes les métadonnées structurées du noeud
    """
    logger.debug(f"Traitement du noeud: {node_json_path}")

    try:
        # 1. Extraire les métadonnées de base depuis .node.json
        basic_metadata = extract_basic_metadata(node_json_path)

        # 2. Obtenir le répertoire du noeud
        node_dir = get_node_directory(node_json_path)

        # 3. Extraire les paramètres d'entrée depuis *.node.js
        input_parameters = extract_input_parameters(node_dir)

        # 4. Extraire les schémas de sortie depuis __schema__
        schema_dir = node_dir / "__schema__"
        output_schemas = {}
        if schema_dir.exists():
            output_schemas = extract_output_schemas(schema_dir)
        else:
            logger.debug(f"Pas de répertoire __schema__ pour {node_json_path.name}")

        # 5. Structurer et normaliser les données
        node_info = build_node_info(
            basic_metadata=basic_metadata,
            input_parameters=input_parameters,
            output_schemas=output_schemas
        )

        # 6. Enrichir avec des inférences de types utiles pour le LLM
        node_info = infer_data_types(node_info)

        return node_info

    except Exception as e:
        logger.error(f"Erreur lors du traitement de {node_json_path}: {e}")
        # Retourner une structure minimale pour ne pas interrompre le traitement
        return {
            "node_name": node_json_path.stem,
            "error": str(e),
            "category": "unknown",
            "version": "unknown"
        }


def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(
        description="Extracteur de métadonnées pour noeuds n8n (natifs et personnalisés) optimisé pour LLM"
    )
    parser.add_argument(
        "--n8n-path",
        type=Path,
        default=Path("/home/venom/.nvm/versions/node/v24.4.1/lib/node_modules/n8n"),
        help="Chemin vers l'installation n8n (défaut: %(default)s)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./n8n_nodes_index"),
        help="Répertoire de sortie pour les fichiers générés (défaut: %(default)s)"
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=["json", "markdown", "llm-prompt"],
        default=["json", "markdown", "llm-prompt"],
        help="Formats de sortie à générer (défaut: tous)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limiter le nombre de noeuds à traiter (0 = pas de limite, défaut: %(default)s)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Niveau de logging (défaut: %(default)s)"
    )

    args = parser.parse_args()

    # Configuration du niveau de logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Vérification du chemin n8n
    if not args.n8n_path.exists():
        logger.error(f"Le chemin n8n spécifié n'existe pas: {args.n8n_path}")
        sys.exit(1)

    # Création du répertoire de sortie
    args.output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Démarrage de l'extraction des noeuds n8n depuis: {args.n8n_path}")
    logger.info(f"Sortie dans: {args.output_dir}")

    # 1. Découverte des noeuds
    logger.info("Découverte des noeuds n8n...")
    node_json_paths = find_native_nodes(args.n8n_path)
    logger.info(f"Trouvé {len(node_json_paths)} noeuds potentiels")

    # Appliquer la limite si spécifiée
    if args.limit > 0:
        node_json_paths = node_json_paths[:args.limit]
        logger.info(f"Limite appliquée : traitement de {args.limit} noeuds appliquée")

    # 2. Traitement de chaque noeud
    nodes_data = []
    processed = 0
    errors = 0

    for node_json_path in node_json_paths:
        try:
            node_info = process_node(node_json_path, args.n8n_path)
            if "error" not in node_info:
                nodes_data.append(node_info)
                processed += 1
            else:
                errors += 1
                logger.debug(f"Noeud ignoré à cause d'erreur: {node_info.get('node_name', 'unknown')}")
        except Exception as e:
            errors += 1
            logger.error(f"Erreur inattendue lors du traitement de {node_json_path}: {e}")

    logger.info(f"Traitement terminé: {processed} noeuds réussis, {errors} erreurs")

    if not nodes_data:
        logger.error("Aucun noeud n'a été traité avec succès. Arrêt.")
        sys.exit(1)

    # 3. Génération des formats de sortie
    logger.info("Génération des formats de sortie...")

    if "json" in args.formats:
        json_path = args.output_dir / "n8n_nodes_complete.json"
        generate_json_output(nodes_data, json_path)
        logger.info(f"Index JSON complet généré: {json_path}")

    if "markdown" in args.formats:
        md_path = args.output_dir / "n8n_nodes_documentation.md"
        generate_markdown_output(nodes_data, md_path)
        logger.info(f"Documentation Markdown générée: {md_path}")

    if "llm-prompt" in args.formats:
        prompt_path = args.output_dir / "n8n_llm_prompt.txt"
        generate_llm_prompt(nodes_data, prompt_path)
        logger.info(f"Prompt optimisé pour LLM généré: {prompt_path}")

    logger.info("Extraction terminée avec succès!")


if __name__ == "__main__":
    main()