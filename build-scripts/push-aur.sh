#!/usr/bin/env bash
# ===========================================================================
# push-aur.sh
# Aggiorna il repository AUR con il PKGBUILD corrente.
# Da eseguire DOPO che la GitHub Release è stata creata e i .deb sono online.
# ===========================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Leggi dal PKGBUILD ───────────────────────────────────────
PROJECT_NAME=$(grep -Po '^pkgname=\K.*' PKGBUILD)
AUR_REPO_DIR="${AUR_REPO_DIR:-./${PROJECT_NAME}}"

if [ -z "$PROJECT_NAME" ]; then
    echo -e "${RED}❌ Impossibile leggere pkgname dal PKGBUILD${NC}"
    exit 1
fi

echo -e "${BLUE}🔄 AUR Push — ${PROJECT_NAME}${NC}"
echo "=================================="

# ── Clona il repo AUR se non esiste ──────────────────────────
if [ ! -d "$AUR_REPO_DIR" ]; then
    echo -e "${YELLOW}⚠ Directory $AUR_REPO_DIR non trovata. Clonazione repo AUR...${NC}"
    if ! git clone "ssh://aur@aur.archlinux.org/${PROJECT_NAME}.git" "$AUR_REPO_DIR"; then
        echo -e "${RED}❌ Errore nella clonazione. Configura la chiave SSH per AUR.${NC}"
        exit 1
    fi
fi

# ── Pulisci artefatti precedenti ─────────────────────────────
rm -rf pkg/ src/ ./*.pkg.*

# ── Aggiorna checksum SHA256 ─────────────────────────────────
echo -e "${YELLOW}🔍 Aggiornamento checksum con updpkgsums...${NC}"
if command -v updpkgsums &> /dev/null; then
    updpkgsums
    echo -e "${GREEN}✅ Checksum aggiornati${NC}"
else
    echo -e "${YELLOW}⚠ updpkgsums non trovato. Installa pacman-contrib.${NC}"
    echo -e "   I checksum nel PKGBUILD potrebbero non essere aggiornati."
fi

# ── Genera .SRCINFO ──────────────────────────────────────────
echo -e "${YELLOW}📄 Generazione .SRCINFO...${NC}"
makepkg --printsrcinfo > .SRCINFO
echo -e "${GREEN}✅ .SRCINFO generato${NC}"

# ── Copia file nel repo AUR ──────────────────────────────────
echo -e "${YELLOW}📁 Copia file nel repository AUR...${NC}"
cp PKGBUILD .SRCINFO "$AUR_REPO_DIR/"

# ── Commit e push ─────────────────────────────────────────────
echo -e "${YELLOW}🚀 Commit e push su AUR...${NC}"
cd "$AUR_REPO_DIR"
git add -A

if ! git diff --staged --quiet; then
    VERSION=$(grep -Po '^pkgver=\K.*' PKGBUILD)
    git commit -m "Update to v${VERSION}"
    git push
    echo -e "${GREEN}✅ Push completato su AUR${NC}"
else
    echo -e "${YELLOW}⚠ Nessuna modifica da pushare${NC}"
fi
