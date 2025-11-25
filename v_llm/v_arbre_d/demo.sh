#!/bin/bash
# Script de démonstration du système

echo "==================================================================="
echo "DÉMONSTRATION - Assistant Médical d'Aide à la Prescription"
echo "==================================================================="
echo ""
echo "Ce script va lancer le programme avec un exemple pré-configuré."
echo ""
echo "Pour une utilisation interactive normale, lancez :"
echo "  python3 source/main.py"
echo ""
echo "==================================================================="
echo ""

# Afficher les statistiques des fichiers JSON
echo "📊 STATISTIQUES DES ARBRES DÉCISIONNELS"
echo "-------------------------------------------------------------------"
echo "Thorax :"
python3 -c "
import json
with open('data/thorax.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    print(f'  • {len(data)} entrées JSON')
    pathologies = set(e.get('pathologie', '') for e in data)
    print(f'  • {len(pathologies)} pathologies différentes')
"

echo ""
echo "Digestif :"
python3 -c "
import json
with open('data/digestif.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    print(f'  • {len(data)} entrées JSON')
    pathologies = set(e.get('pathologie', '') for e in data)
    print(f'  • {len(pathologies)} pathologies différentes')
"

echo ""
echo "==================================================================="
echo "Pour tester le programme en mode interactif :"
echo "  python3 source/main.py"
echo "==================================================================="
