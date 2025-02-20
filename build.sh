#!/bin/bash

# Exit on error
set -e

echo "Building Skip Intro addon..."

# Set paths
ADDON_DIR="../plugin.video.skipintro"
REPO_DIR="$(pwd)"

# Get current version from addon.xml
ADDON_XML_PATH="$ADDON_DIR/addon.xml"
if [ ! -f "$ADDON_XML_PATH" ]; then
    echo "Error: addon.xml not found at $ADDON_XML_PATH"
    exit 1
fi

VERSION=$(xmllint --xpath "string(/addon/@version)" "$ADDON_XML_PATH")
if [ -z "$VERSION" ]; then
    echo "Error: Could not extract version from addon.xml"
    exit 1
fi
echo "Current version: $VERSION"

# Check version consistency in README
README_PATH="$ADDON_DIR/README.md"
if [ -f "$README_PATH" ]; then
    README_VERSION=$(grep -E '^### v[0-9.]+' "$README_PATH" | head -1 | sed -E 's/^### v([0-9.]+).*/\1/')
    if [ -n "$README_VERSION" ]; then
        if [ "$VERSION" != "$README_VERSION" ]; then
            echo "Warning: Version mismatch between addon.xml ($VERSION) and README.md ($README_VERSION)"
        else
            echo "Version consistency check passed"
        fi
    else
        echo "Warning: Could not extract version from README.md"
    fi
else
    echo "Warning: README.md not found at $README_PATH"
fi

# Create release directory if it doesn't exist
RELEASE_DIR="$REPO_DIR/release"
mkdir -p "$RELEASE_DIR"
echo "Release directory: $RELEASE_DIR"

# Clean up old files
rm -f "$RELEASE_DIR"/plugin.video.skipintro-*.zip
rm -f "$RELEASE_DIR"/repository.plugin.video.skipintro.xml
rm -f "$RELEASE_DIR"/repository.plugin.video.skipintro.zip

# Create temporary build directory
BUILD_DIR=$(mktemp -d)
TEMP_ADDON_DIR="$BUILD_DIR/plugin.video.skipintro"
echo "Build directory: $BUILD_DIR"
echo "Temporary addon directory: $TEMP_ADDON_DIR"

# Create addon directory structure
mkdir -p "$TEMP_ADDON_DIR"

# Copy files
echo "Copying files..."
cp -R "$ADDON_DIR"/* "$TEMP_ADDON_DIR/" && echo "Copied addon files" || echo "Failed to copy addon files"

# Create zip file
echo "Creating zip file..."
cd "$BUILD_DIR"
zip -r "$RELEASE_DIR/plugin.video.skipintro-$VERSION.zip" "plugin.video.skipintro"
ZIP_RESULT=$?
cd -

if [ $ZIP_RESULT -eq 0 ]; then
    echo "Successfully created zip file: $RELEASE_DIR/plugin.video.skipintro-$VERSION.zip"
else
    echo "Failed to create zip file. Error code: $ZIP_RESULT"
    exit 1
fi

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
