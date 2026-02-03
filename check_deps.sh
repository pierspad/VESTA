#!/bin/bash

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Checking dependencies for SRT Tools...${NC}"

# Detect Package Manager
PM=""
if command -v pacman &> /dev/null; then
    PM="pacman"
    echo -e "Detected Arch Linux (pacman)"
    GST_PLUGINS=(
        "gst-plugins-good"
        "gst-plugins-bad"
        "gst-plugins-ugly"
        "gst-libav"
    )
    WEBKIT_PKG="webkit2gtk-4.1" # or similar
elif command -v dpkg &> /dev/null; then
    PM="dpkg"
     echo -e "Detected Debian/Ubuntu (dpkg)"
    GST_PLUGINS=(
        "gstreamer1.0-plugins-good"
        "gstreamer1.0-plugins-bad"
        "gstreamer1.0-plugins-ugly"
        "gstreamer1.0-libav"
        "gstreamer1.0-tools"
    )
    WEBKIT_PKG="libwebkit2gtk-4"
else
    echo -e "${RED}Unknown package manager. Performing generic checks.${NC}"
fi

# Check for GStreamer plugins
echo -e "\n${YELLOW}Checking GStreamer plugins...${NC}"

MISSING_GST=0

if [ "$PM" == "pacman" ]; then
    for pkg in "${GST_PLUGINS[@]}"; do
        if pacman -Q "$pkg" &> /dev/null; then
            echo -e "${GREEN}✓ $pkg is installed${NC}"
        else
            echo -e "${RED}✗ $pkg is missing${NC}"
            MISSING_GST=1
        fi
    done
elif [ "$PM" == "dpkg" ]; then
    for pkg in "${GST_PLUGINS[@]}"; do
        if dpkg -l | grep -q "$pkg"; then
            echo -e "${GREEN}✓ $pkg is installed${NC}"
        else
            echo -e "${RED}✗ $pkg is missing${NC}"
            MISSING_GST=1
        fi
    done
else
    # Fallback to gst-inspect-1.0
    if command -v gst-inspect-1.0 &> /dev/null; then
         echo -e "${GREEN}✓ gst-inspect-1.0 found${NC}"
    else
         echo -e "${RED}✗ gst-inspect-1.0 missing${NC}"
         MISSING_GST=1
    fi
fi

# Check if we can run gst-inspect-1.0 for H.264
if command -v gst-inspect-1.0 &> /dev/null; then
    echo -e "\n${YELLOW}Checking for h264 decoder...${NC}"
    if gst-inspect-1.0 | grep -i "h264" &> /dev/null; then
        echo -e "${GREEN}✓ H.264 decoder found (via gst-inspect)${NC}"
    else
         echo -e "${RED}✗ H.264 decoder NOT found${NC}"
    fi
fi

if [ $MISSING_GST -eq 1 ]; then
    echo -e "\n${RED}Some GStreamer plugins are missing. Video playback might fail.${NC}"
    if [ "$PM" == "pacman" ]; then
        echo -e "Try: sudo pacman -S gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-libav"
    elif [ "$PM" == "dpkg" ]; then
        echo -e "Try: sudo apt install gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav"
    fi
else
    echo -e "\n${GREEN}All GStreamer dependencies seem to be installed.${NC}"
fi

chmod +x "$0"
