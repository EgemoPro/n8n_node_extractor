"""
Module de génération des différents formats de sortie pour l'index des noeuds n8n.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def generate_json_output(nodes_data: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Génère un fichier JSON complet contenant toutes les métadonnées des noeuds.

    Args:
        nodes_data: Liste des informations structurées des noeuds
        output_path: Chemin où écrire le fichier JSON
    """
    try:
        # Préparer les données pour la sérialisation JSON
        output_data = {
            "metadata": {
                "generated_by": "n8n_node_extractor",
                "version": "1.0.0",
                "total_nodes": len(nodes_data),
                "nodes_by_category": _count_nodes_by_category(nodes_data)
            },
            "nodes": nodes_data
        }

        # Écrire le fichier JSON avec indentation pour lisibilité
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Fichier JSON écrit: {output_path}")

    except Exception as e:
        logger.error(f"Erreur lors de la génération du fichier JSON {output_path}: {e}")
        raise


def generate_markdown_output(nodes_data: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Génère un fichier Markdown contenant une documentation lisible des noeuds.

    Args:
        nodes_data: Liste des informations structurées des noeuds
        output_path: Chemin où écrire le fichier Markdown
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # En-tête du document
            f.write("# Index des Noeuds Natifs n8n\n\n")
            f.write(f"*Généré par n8n_node_extractor - {len(nodes_data)} noeuds indexés*\n\n")

            # Table des matières par catégorie
            f.write("## Table des Matières\n\n")
            categories = _get_unique_categories(nodes_data)
            for category in sorted(categories):
                count = len([n for n in nodes_data if n.get("category") == category])
                f.write(f"- [{category}](#{category.lower().replace(' ', '-')} ({count} noeuds))\n")
            f.write("\n---\n\n")

            # Section pour chaque catégorie
            for category in sorted(categories):
                category_nodes = [n for n in nodes_data if n.get("category") == category]
                f.write(f"## {category} ({len(category_nodes)} noeuds)\n\n")

                for node in sorted(category_nodes, key=lambda x: x.get("node_name", "")):
                    _write_node_markdown_section(f, node)

                f.write("\n---\n\n")

        logger.debug(f"Fichier Markdown écrit: {output_path}")

    except Exception as e:
        logger.error(f"Erreur lors de la génération du fichier Markdown {output_path}: {e}")
        raise


def generate_llm_prompt(nodes_data: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Génère un prompt optimisé pour LLM décrivant les noeuds disponibles et comment les utiliser.

    Args:
        nodes_data: Liste des informations structurées des noeuds
        output_path: Chemin où écrire le fichier de prompt
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Prompt Optimisé pour LLM - Génération de Workflows n8n\n\n")
            f.write("Utilisez ce contexte pour générer des workflows n8n valides et diversifiés.\n\n")

            # Instructions générales
            f.write("## Instructions pour le LLM\n\n")
            f.write("Lorsque vous générez un workflow n8n, suivez ces lignes directrices:\n\n")
            f.write("1. **Comprendre le noeud** : Lisez la description et la catégorie pour comprendre son rôle\n")
            f.write("2. **Configurer les paramètres requis** : Tous les paramètres marqués comme requis doivent être fournis\n")
            f.write("3. **Respecter les types de données** : Assurez-vous que les types de données sortants correspondent aux types attendus en entrée\n")
            f.write("4. **Chaîner logiquement** : Connectez les noeuds où la sortie d'un a du sens comme entrée de l'autre\n")
            f.write("5. **Utiliser les références** : Consultez la documentation officielle pour les cas d'usage spécifiques\n\n")

            # Index des noeuds par catégorie
            f.write("## Index des Noeuds Disponibles\n\n")
            f.write("Format: `[Nom] (Catégorie)` - Description\n")
            f.write("Paramètres requis: [liste]\n")
            f.write("Types de données produits: [liste]\n\n")

            categories = _get_unique_categories(nodes_data)
            for category in sorted(categories):
                f.write(f"### {category}\n\n")
                category_nodes = [n for n in nodes_data if n.get("category") == category]
                for node in sorted(category_nodes, key=lambda x: x.get("node_name", "")):
                    f.write(f"**{node.get('node_name', 'Unknown')}** ")
                    f.write(f"({node.get('category', 'Uncategorized')})\n")
                    f.write(f"- {node.get('llm_summary', 'Pas de résumé disponible')}\n")

                    # Liste concise des paramètres requis
                    required_params = [
                        p.get('display_name', p.get('name', ''))
                        for p in node.get('input_parameters', [])
                        if p.get('required', False)
                    ]
                    if required_params:
                        f.write(f"- **Paramètres requis**: {', '.join(required_params)}\n")
                    else:
                        f.write(f"- **Paramètres requis**: Aucun\n")

                    # Types de données produits
                    output_types = node.get('execution_context', {}).get('output_types', [])
                    if output_types:
                        f.write(f"- **Produit**: {', '.join(output_types)}\n")
                    else:
                        f.write(f"- **Produit**: Type inconnu\n")

                    f.write("\n")

            # Exemples de chaînes de connexion
            f.write("## Exemples de Chaînes de Connexion Courantes\n\n")
            f.write("Ces exemples montrent comment connecter logiquement des noeuds:\n\n")
            f.write("1. **Données externes → Traitement → Sauvegarde**\n")
            f.write("   - HTTP Request (GET) → Function (traitement JSON) → Set (formatage) → Google Sheets (écriture)\n\n")
            f.write("2. **Déclencheur → Validation → Action**\n")
            f.write("   - Cron (tous les jours à 9h) → IF (vérification condition) → Email Send (notification)\n\n")
            f.write("3. **API → Transformation → Notification**\n")
            f.write("   - Shopify (nouvelle commande) → Function (calcul taxes) → Slack (notification équipe)\n\n")

            # Conseils pour la génération de workflows diversifiés
            f.write("## Conseils pour Générer des Workflows Diversifiés\n\n")
            f.write("- **Mixez les catégories** : Combinez des noeuds de différentes catégories pour des workflows riches\n")
            f.write("- **Utilisez les noeuds de base** : Function, Set, IF, SplitInBatches sont essentiels pour la logique\n")
            f.write("- **Pensez au flux de données** : Visualisez comment les données se transforment d'un noeud à l'autre\n")
            f.write("- **Testez les connexions** : Assurez-vous que la sortie de A peut être consommée par B\n")
            f.write("- **Commencez simple** : Un workflow avec 2-3 noeuds bien connectés vaut mieux qu'un complexe mal connecté\n\n")

        logger.debug(f"Fichier de prompt LLM écrit: {output_path}")

    except Exception as e:
        logger.error(f"Erreur lors de la génération du fichier de prompt LLM {output_path}: {e}")
        raise


def _count_nodes_by_category(nodes_data: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Compte le nombre de noeuds par catégorie.

    Args:
        nodes_data: Liste des informations structurées des noeuds

    Returns:
        Dictionnaire mapping catégorie → nombre de noeuds
    """
    counts = {}
    for node in nodes_data:
        category = node.get("category", "Uncategorized")
        counts[category] = counts.get(category, 0) + 1
    return counts


def _get_unique_categories(nodes_data: List[Dict[str, Any]]) -> List[str]:
    """
    Récupère la liste unique des catégories présentes.

    Args:
        nodes_data: Liste des informations structurées des noeuds

    Returns:
        Liste triée des catégories uniques
    """
    categories = set()
    for node in nodes_data:
        category = node.get("category", "Uncategorized")
        categories.add(category)
    return sorted(list(categories))


def _write_node_markdown_section(file_handle, node: Dict[str, Any]) -> None:
    """
    Écrit la section Markdown pour un noeud individuel.

    Args:
        file_handle: Handle du fichier ouvert en écriture
        node: Informations structurées du noeud
    """
    name = node.get("node_name", "Unknown")
    category = node.get("category", "Uncategorized")
    description = node.get("description", "")

    # Titre du noeud
    file_handle.write(f"### {name} ({category})\n\n")

    # Description
    if description:
        file_handle.write(f"**Description**\n{description}\n\n")

    # Paramètres d'entrée
    input_params = node.get("input_parameters", [])
    if input_params:
        file_handle.write("**Paramètres d'entrée**\n")
        file_handle.write("| Nom | Type | Requis | Description |\n")
        file_handle.write("|-----|------|--------|-------------|\n")
        for param in input_params:
            param_name = param.get("display_name", param.get("name", ""))
            param_type = param.get("type", "unknown")
            required = "Oui" if param.get("required", False) else "Non"
            param_desc = param.get("description", "")
            # Limiter la longueur de la description pour le tableau
            if len(param_desc) > 50:
                param_desc = param_desc[:47] + "..."
            file_handle.write(f"| {param_name} | {param_type} | {required} | {param_desc} |\n")
        file_handle.write("\n")

    # Schémas de sortie (version simplifiée)
    output_schemas = node.get("output_schemas", {})
    if output_schemas:
        file_handle.write("**Sorties disponibles**\n")
        # Montrer juste la structure générale
        versions = list(output_schemas.keys())
        if versions:
            file_handle.write(f"- Versions de schéma disponibles: {', '.join(versions)}\n")
            # Prendre la première version pour montrer un exemple
            first_version = versions[0]
            resources = list(output_schemas[first_version].keys())
            if resources:
                file_handle.write(f"- Ressources disponibles (v{first_version}): {', '.join(resources[:5])}")
                if len(resources) > 5:
                    file_handle.write("...")
                file_handle.write("\n")
        file_handle.write("\n")

    # Liens de documentation
    doc_links = node.get("documentation", {}).get("links", [])
    if doc_links:
        file_handle.write("**Documentation**\n")
        for link in doc_links[:3]:  # Limiter à 3 liens pour éviter la surcharge
            file_handle.write(f"- {link}\n")
        if len(doc_links) > 3:
            file_handle.write(f"- Et {len(doc_links) - 3} autres liens...\n")
        file_handle.write("\n")