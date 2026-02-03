#!/bin/bash

# Script per compilare SRT Tools GUI in modalità release (ottimizzata e veloce)

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Controlla se siamo nella root
if [ ! -d "srt-gui" ]; then
    echo -e "${RED}❌ Errore: Esegui questo script dalla root del progetto (dove c'è la cartella srt-gui).${NC}"
    echo -e "   Percorso attuale: $(pwd)"
    exit 1
fi

echo -e "${BLUE}🔨 Compilazione SRT Tools GUI in modalità release...${NC}"
echo -e "${YELLOW}   Questo creerà un eseguibile ottimizzato e veloce all'avvio.${NC}"
echo ""

cd srt-gui

# Controlla se Node.js è installato
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ Errore: npm non trovato. Installa Node.js per continuare.${NC}"
    exit 1
fi

# Installa dipendenze se mancano
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installazione dipendenze frontend...${NC}"
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Errore durante l'installazione delle dipendenze.${NC}"
        exit 1
    fi
    echo ""
fi

echo -e "${BLUE}🏗️  Compilazione in corso...${NC}"
echo -e "${YELLOW}   (Può richiedere qualche minuto al primo build)${NC}"
echo ""

# Build in modalità release
npm run tauri build -- --debug

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Build completato con successo!${NC}"
    echo -e "${BLUE}   Eseguibile creato in: target/release/srt-gui${NC}"
    echo -e "${GREEN}   Ora puoi usare ./run_gui.sh per un avvio veloce!${NC}"
else
    echo ""
    echo -e "${RED}❌ Errore durante la compilazione.${NC}"
    exit 1
fi
