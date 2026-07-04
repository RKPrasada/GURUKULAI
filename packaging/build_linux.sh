#!/bin/bash
# Build VidyaBot Linux .tar.gz and AppImage
set -e

echo "=============================="
echo "  VidyaBot Linux Builder"
echo "=============================="

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "Installing dependencies..."
pip install -r requirements.txt pyinstaller

echo "Running PyInstaller..."
pyinstaller packaging/vidyabot.spec --distpath packaging/dist/linux --workpath packaging/build

DIST_DIR="packaging/dist/linux/VidyaBot"

echo "Creating .tar.gz archive..."
cd packaging/dist/linux
tar -czf "../VidyaBot-Linux-x86_64.tar.gz" VidyaBot/
cd "$ROOT"

echo "Creating .desktop launcher file..."
cat > "packaging/dist/linux/VidyaBot.desktop" << 'DESKTOP'
[Desktop Entry]
Version=1.0
Type=Application
Name=VidyaBot
GenericName=AI Tutor
Comment=Personalized AI Tutor for Indian Competitive Exams
Exec=VidyaBot/VidyaBot
Icon=VidyaBot
Terminal=false
Categories=Education;
Keywords=exam;tutor;RRB;JEE;NEET;NDA;
DESKTOP

echo ""
echo "✅ Build complete!"
echo "   Archive: packaging/dist/VidyaBot-Linux-x86_64.tar.gz"
echo "   To install: extract the .tar.gz and run ./VidyaBot/VidyaBot"
