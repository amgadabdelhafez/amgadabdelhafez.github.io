#!/bin/bash

# Exit on error
set -e

echo "Building Skip Intro addon..."

# Get current version from addon.xml
VERSION=$(grep -oP 'id="plugin\.video\.skipintro"[^>]*version="\K[^"]+' addon.xml)
echo "Current version: $VERSION"

# Check version consistency in README
README_VERSION=$(grep -oP '### v\K[0-9.]+' README.md | head -1)
if [ "$VERSION" != "$README_VERSION" ]; then
    echo "Error: Version mismatch!"
    echo "addon.xml: $VERSION"
    echo "README.md: $README_VERSION"
    exit 1
fi

echo "Version consistency check passed"

# Create release directory if it doesn't exist
mkdir -p release

# Clean up old files
rm -f release/plugin.video.skipintro-*.zip
rm -f release/repository.plugin.video.skipintro.xml
rm -f release/repository.plugin.video.skipintro.zip

# Create temporary build directory
BUILD_DIR=$(mktemp -d)
ADDON_DIR="$BUILD_DIR/plugin.video.skipintro"

# Create addon directory structure
mkdir -p "$ADDON_DIR/resources/language/resource.language.en_gb"

# Copy files
cp addon.xml "$ADDON_DIR/"
cp default.py "$ADDON_DIR/"
cp README.md "$ADDON_DIR/"
cp resources/settings.xml "$ADDON_DIR/resources/"
cp resources/language/resource.language.en_gb/strings.po "$ADDON_DIR/resources/language/resource.language.en_gb/"

# Create zip file
cd "$BUILD_DIR"
zip -r "../release/plugin.video.skipintro-$VERSION.zip" "plugin.video.skipintro"
cd -

# Create addons.xml
cat > release/addons.xml << EOF
<?xml version="1.0" encoding="UTF-8"?>
<addons>
    $(cat addon.xml)
</addons>
EOF

# Generate MD5
cd release
md5sum addons.xml > addons.xml.md5
cd -

# Create repository XML
cat > release/repository.plugin.video.skipintro.xml << EOF
<?xml version="1.0" encoding="UTF-8"?>
<addon id="repository.plugin.video.skipintro" 
       name="Skip Intro Repository" 
       version="$VERSION" 
       provider-name="Amgad Abdelhafez">
    <extension point="xbmc.addon.repository" name="Skip Intro Repository">
        <info compressed="false">https://github.com/amgadabdelhafez/plugin.video.skipintro/raw/main/repository.xml</info>
        <checksum>https://github.com/amgadabdelhafez/plugin.video.skipintro/raw/main/repository.md5</checksum>
        <datadir zip="true">https://github.com/amgadabdelhafez/plugin.video.skipintro/raw/main/</datadir>
        <assets>
            <icon>https://github.com/amgadabdelhafez/plugin.video.skipintro/raw/main/icon.png</icon>
            <fanart>https://github.com/amgadabdelhafez/plugin.video.skipintro/raw/main/fanart.jpg</fanart>
        </assets>
    </extension>
    <extension point="xbmc.addon.metadata">
        <summary lang="en">Repository for Skip Intro Addon</summary>
        <description lang="en">This repository provides updates for the Skip Intro Addon.</description>
        <platform>all</platform>
    </extension>
</addon>
EOF

# Create repository zip
cd release
zip -r repository.plugin.video.skipintro.zip repository.plugin.video.skipintro.xml
cd -

# Clean up
rm -rf "$BUILD_DIR"

echo "Build complete!"
echo "Created: release/plugin.video.skipintro-$VERSION.zip"
echo "Created: release/repository.plugin.video.skipintro.xml"
echo "Created: release/repository.plugin.video.skipintro.zip"
