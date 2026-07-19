"""
Module de découverte pour localiser les noeuds n8n (natifs et personnalisés) dans l'installation.
"""

from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


def find_native_nodes(n8n_root: Path) -> List[Path]:
    """
    Parcourt récursivement l'installation n8n pour localiser tous les fichiers
    *.node.json représentant des noeuds (natifs et personnalisés).

    Args:
        n8n_root: Racine de l'installation n8n

    Returns:
        Liste des chemins vers les fichiers *.node.json des noeuds
    """
    logger.info("Recherche large des fichiers *.node.json dans l'installation n8n...")
    all_node_json_files = list(n8n_root.rglob("*.node.json"))

    # Filtrer pour exclure certains répertoires non pertinents
    filtered_files = []
    exclude_patterns = ["__tests__", "test", "docs", ".cache", ".git"]

    for file_path in all_node_json_files:
        # Vérifier si quelconque partie du chemin contient un motif d'exclusion
        if any(exclude in str(file_path) for exclude in exclude_patterns):
            continue
        filtered_files.append(file_path)

    logger.info(f"Trouvé {len(filtered_files)} noeuds potentiels après filtrage")
    return filtered_files


def get_node_directory(node_json_path: Path) -> Path:
    """
    Déduit le répertoire du noeud à partir du chemin du fichier .node.json.

    Args:
        node_json_path: Chemin vers le fichier *.node.json

    Returns:
        Chemin vers le répertoire contenant le noeud
    """
    # Le répertoire du noeud est le parent du fichier .node.json
    return node_json_path.parent