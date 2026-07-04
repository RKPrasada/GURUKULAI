#!/bin/bash
# Build VidyaBot macOS app bundle
set -e

echo "=============================="
echo "  VidyaBot macOS Builder"
echo "=============================="

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "Installing dependencies..."
pip install -r requirements.txt pyinstaller

echo "Running PyInstaller..."
pyinstaller packaging/vidyabot.spec --distpath packaging/dist/mac --workpath packaging/build

echo "Creating macOS .app bundle..."
APP_DIR="packaging/dist/mac/VidyaBot.app"
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Copy the binary
cp -r packaging/dist/mac/VidyaBot/* "$APP_DIR/Contents/MacOS/"

# Info.plist
cat > "$APP_DIR/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>VidyaBot</string>
    <key>CFBundleIdentifier</key>
    <string>com.vidyabot.app</string>
    <key>CFBundleName</key>
    <string>VidyaBot</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

echo "Creating DMG..."
hdiutil create -volname "VidyaBot" \
    -srcfolder "$APP_DIR" \
    -ov -format UDZO \
    "packaging/dist/VidyaBot-macOS.dmg" 2>/dev/null || \
    echo "DMG creation failed (hdiutil missing). App bundle at: $APP_DIR"

echo ""
echo "✅ Build complete!"
echo "   App: $APP_DIR"
if [ -f "packaging/dist/VidyaBot-macOS.dmg" ]; then
    echo "   DMG: packaging/dist/VidyaBot-macOS.dmg"
fi
