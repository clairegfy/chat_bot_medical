#!/bin/bash
# Script de test automatisé pour le chatbot médical

echo "=========================================="
echo "TESTS AUTOMATISÉS - CHATBOT MÉDICAL"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# Vérifier syntaxe Python
echo "1️⃣  Vérification syntaxe Python..."
python3 -m py_compile source/main.py
if [ $? -eq 0 ]; then
    echo "✅ Syntaxe OK"
else
    echo "❌ Erreur de syntaxe"
    exit 1
fi
echo ""

# Vérifier intégrité JSON
echo "2️⃣  Vérification intégrité JSON..."
for file in data/*.json; do
    python3 -c "import json; json.load(open('$file'))" 2>/dev/null
    if [ $? -eq 0 ]; then
        count=$(python3 -c "import json; print(len(json.load(open('$file'))))")
        echo "✅ $(basename $file): $count entrées"
    else
        echo "❌ $(basename $file): INVALIDE"
        exit 1
    fi
done
echo ""

# Lancer tests unitaires
echo "3️⃣  Exécution tests unitaires..."
python3 tests/test_chatbot.py -v
TEST_UNIT_CODE=$?
echo ""

# Lancer tests scénarios cliniques
echo "4️⃣  Exécution tests scénarios cliniques..."
python3 tests/test_scenarios_cliniques.py -v
TEST_SCENARIOS_CODE=$?
echo ""

# Lancer tests qualité prescription
echo "5️⃣  Exécution tests qualité prescription..."
python3 tests/test_prescription_quality.py
TEST_QUALITY_CODE=$?
echo ""

# Résumé
echo "=========================================="
if [ $TEST_UNIT_CODE -eq 0 ] && [ $TEST_SCENARIOS_CODE -eq 0 ] && [ $TEST_QUALITY_CODE -eq 0 ]; then
    echo "✅ TOUS LES TESTS PASSENT (98 tests)"
    echo "   • 43 tests unitaires"
    echo "   • 33 tests scénarios cliniques"
    echo "   • 22 tests qualité prescription"
    echo "=========================================="
    exit 0
else
    echo "❌ CERTAINS TESTS ÉCHOUENT"
    echo "=========================================="
    exit 1
fi
