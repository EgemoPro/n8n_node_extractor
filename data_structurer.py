"""
Module de structuration des données pour créer un format optimisé pour LLM.
"""

from typing import Any, Dict, List
import json


def build_node_info(
    basic_metadata: Dict[str, Any],
    input_parameters: List[Dict[str, Any]],
    output_schemas: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Normalise les données extraites dans un format intermédiaire cohérent.

    Args:
        basic_metadata: Métadonnées de base depuis .node.json
        input_parameters: Paramètres d'entrée depuis description.properties
        output_schemas: Schémas de sortie depuis __schema__

    Returns:
        Dictionnaire contenant toutes les métadonnées structurées du noeud
    """
    # Construire la structure de base
    node_info = {
        "node_name": basic_metadata.get("class_name", "unknown"),
        "node_id": basic_metadata.get("node_id", ""),
        "version": basic_metadata.get("node_version", "unknown"),
        "codex_version": basic_metadata.get("codex_version", ""),
        "category": basic_metadata.get("categories", ["Uncategorized"])[0] if basic_metadata.get("categories") else "Uncategorized",
        "all_categories": basic_metadata.get("categories", []),
        "description": basic_metadata.get("details", ""),
        "documentation": {
            "short": basic_metadata.get("details", ""),
            "links": basic_metadata.get("documentation_links", [])
        },
        "input_parameters": input_parameters,
        "output_schemas": output_schemas,
        "metadata_source": "static_extraction"
    }

    # Ajouter des informations d'exécution utiles pour le chaînage
    node_info["execution_context"] = _build_execution_context(
        input_parameters, output_schemas
    )

    return node_info


def _build_execution_context(
    input_parameters: List[Dict[str, Any]],
    output_schemas: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Construit des informations sur le contexte d'exécution utiles pour le LLM
    lorsqu'il doit chaîner des noeuds.

    Args:
        input_parameters: Liste des paramètres d'entrée
        output_schemas: Schémas de sortie structurés

    Returns:
        Dictionnaire contenant le contexte d'exécution
    """
    # Extraire les types de données des paramètres d'entrée
    input_types = list(set(
        param.get("type", "unknown")
        for param in input_parameters
    ))

    # Extraire les types de données des schémas de sortie
    output_types = _extract_output_types(output_schemas)

    return {
        "input_types": list(set(input_types)),
        "output_types": list(set(output_types)),
        "has_credentials": any(
            param.get("type") in ["credentials", "credentialType"]
            for param in input_parameters
        ),
        "has_json_input": any(
            param.get("type") == "json"
            for param in input_parameters
        )
    }


def _extract_output_types(schemas: Dict[str, Any]) -> List[str]:
    """
    Extrait récursivement les types de données depuis les schémas de sortie.

    Args:
        schemas: Schémas de sortie structurés

    Returns:
        Liste des types de données trouvés dans les schémas
    """
    types = set()

    def _extract_from_schema(schema_obj):
        if isinstance(schema_obj, dict):
            # Chercher le type dans le schéma JSON
            if "type" in schema_obj:
                types.add(str(schema_obj["type"]))

            # Parcourir récursivement les propriétés
            if "properties" in schema_obj and isinstance(schema_obj["properties"], dict):
                for prop_value in schema_obj["properties"].values():
                    _extract_from_schema(prop_value)

            # Parcourir les éléments d'un tableau
            if "items" in schema_obj:
                _extract_from_schema(schema_obj["items"])

            # Parcourir les propriétés supplémentaires
            if "additionalProperties" in schema_obj:
                _extract_from_schema(schema_obj["additionalProperties"])

        elif isinstance(schema_obj, list):
            for item in schema_obj:
                _extract_from_schema(item)

    # Parcourir toute la structure des schémas
    for version_data in schemas.values():
        if isinstance(version_data, dict):
            for resource_data in version_data.values():
                if isinstance(resource_data, dict):
                    for operation_schema in resource_data.values():
                        _extract_from_schema(operation_schema)

    return list(types)


def infer_data_types(node_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrichit les informations du noeud avec des inférences utiles pour le LLM.

    Args:
        node_info: Informations de base du noeud

    Returns:
        Informations du noeud enrichies avec des inférences
    """
    # Créer une copie pour éviter de modifier l'original
    enriched = node_info.copy()

    # Inférer la complexité du noeud basée sur le nombre de paramètres
    param_count = len(enriched.get("input_parameters", []))
    if param_count <= 3:
        enriched["complexity"] = "simple"
    elif param_count <= 7:
        enriched["complexity"] = "moderate"
    else:
        enriched["complexity"] = "complex"

    # Inférer si le noeud est probablement un noeud de déclenchement (trigger)
    # Les trigger ont souvent des paramètres spécifiques comme des webhooks ou des cron
    input_params = enriched.get("input_parameters", [])
    trigger_indicators = ["webhook", "webhook", " cron ", "interval", "trigger"]
    is_probable_trigger = False

    for param in input_params:
        param_name = param.get("name", "").lower()
        param_desc = param.get("description", "").lower()
        if any(indicator in param_name or indicator in param_desc for indicator in trigger_indicators):
            is_probable_trigger = True
            break

    enriched["is_probable_trigger"] = is_probable_trigger

    # Inférer les types de données communes pour faciliter le chaînage
    input_types = enriched.get("execution_context", {}).get("input_types", [])
    output_types = enriched.get("execution_context", {}).get("output_types", [])

    # Déterminer si le noeud accepte des entrées génériques
    accepts_generic = any(
        t in ["json", "string", "object", "binary"]
        for t in input_types
    )
    enriched["accepts_generic_input"] = accepts_generic

    # Déterminer si le noeud produit des sorties communes
    produces_common = any(
        t in ["json", "string", "object", "array", "binary"]
        for t in output_types
    )
    enriched["produces_common_output"] = produces_common

    # Créer une description simplifiée pour les prompts LLM
    enriched["llm_summary"] = _create_llm_summary(enriched)

    return enriched


def _create_llm_summary(node_info: Dict[str, Any]) -> str:
    """
    Crée une description concise optimisée pour les prompts LLM.

    Args:
        node_info: Informations du noeud

    Returns:
        Chaîne de caractères décrivant le noeud de manière concise
    """
    name = node_info.get("node_name", "Unknown")
    category = node_info.get("category", "Uncategorized")
    description = node_info.get("description", "")

    # Limiter la description à une longueur raisonnable
    if len(description) > 100:
        description = description[:97] + "..."

    # Construire le résumé
    summary_parts = [
        f"Noeud: {name}",
        f"Catégorie: {category}"
    ]

    if description:
        summary_parts.append(f"Description: {description}")

    # Ajouter les paramètres requis importants
    required_params = [
        p.get("display_name", p.get("name", ""))
        for p in node_info.get("input_parameters", [])
        if p.get("required", False)
    ]

    if required_params:
        summary_parts.append(f"Paramètres requis: {', '.join(required_params[:3])}")
        if len(required_params) > 3:
            summary_parts[-1] += "..."

    # Ajouter ce que le noeud produit
    output_types = node_info.get("execution_context", {}).get("output_types", [])
    if output_types:
        summary_parts.append(f"Produit: {', '.join(output_types[:3])}")

    return " - ".join(summary_parts)