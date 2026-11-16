#!/bin/bash
set -euo pipefail

packaging=$(cd -- "$(dirname -- "$0")" && pwd)
repo=$(cd -- "$packaging/../.." && pwd)
version=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$packaging/Info.plist")
output=${1:-"$repo/dist/Medora-$version-arm64.dmg"}
if [[ $(uname -m) != arm64 ]]; then
    echo 'This package targets Apple Silicon. Run the build on an Apple Silicon Mac.' >&2
    exit 1
fi

docker=/Applications/Docker.app/Contents/Resources/bin/docker
if [[ ! -x "$docker" ]]; then
    docker="$HOME/Applications/Docker.app/Contents/Resources/bin/docker"
fi
if [[ ! -x "$docker" ]]; then
    echo 'Docker Desktop is required to build Medora.' >&2
    exit 1
fi
export DOCKER_CONTEXT=desktop-linux
unset DOCKER_HOST

work=$(mktemp -d "${TMPDIR:-/tmp}/medora-dmg.XXXXXXXX")
trap 'rm -rf -- "$work"' EXIT
stage="$work/stage"
app="$stage/Medora.app"
resources="$app/Contents/Resources"
mkdir -p "$app/Contents/MacOS" "$resources" "$(dirname -- "$output")"

echo 'Building the Medora container image…'
"$docker" build --platform linux/arm64 --file "$packaging/Dockerfile" --tag medora-desktop-app:build "$repo"
if ! "$docker" image inspect postgres:15-alpine >/dev/null 2>&1; then
    "$docker" image pull --platform linux/arm64 postgres:15-alpine
fi

tag_image() {
    local source=$1 repository=$2 digest tag
    digest=$("$docker" image inspect --format '{{.Id}}' "$source")
    tag="$repository:${digest:7:12}"
    "$docker" image tag "$source" "$tag"
    printf '%s\n' "$tag"
}

app_image=$(tag_image medora-desktop-app:build medora-desktop-app)
database_image=$(tag_image postgres:15-alpine medora-desktop-postgres)
printf 'MEDORA_APP_IMAGE=%s\nMEDORA_DATABASE_IMAGE=%s\n' "$app_image" "$database_image" > "$resources/images.env"

echo 'Bundling the container images…'
"$docker" image save --platform linux/arm64 "$app_image" "$database_image" | gzip -1 > "$resources/images.tar.gz"
cp "$packaging/Info.plist" "$app/Contents/Info.plist"
cp "$packaging/compose.yml" "$resources/compose.yml"
install -m 755 "$packaging/stack.sh" "$resources/stack.sh"

echo 'Building the macOS app…'
xcrun swiftc -swift-version 5 -target arm64-apple-macos13.0 -module-cache-path "$work/modules" \
    -O "$packaging/Medora.swift" -o "$app/Contents/MacOS/Medora"
xcrun swiftc -module-cache-path "$work/modules" "$packaging/Icon.swift" -o "$work/make-icon"
"$work/make-icon" "$work/Medora.png"
iconset="$work/Medora.iconset"
mkdir "$iconset"
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$work/Medora.png" --out "$iconset/icon_${size}x${size}.png" > /dev/null
    doubled=$((size * 2))
    sips -z "$doubled" "$doubled" "$work/Medora.png" --out "$iconset/icon_${size}x${size}@2x.png" > /dev/null
done
iconutil --convert icns --output "$resources/Medora.icns" "$iconset"

codesign --force --sign - "$app"
codesign --verify --strict "$app"
ln -s /Applications "$stage/Applications"

echo 'Creating the disk image…'
hdiutil create -format UDZO -imagekey zlib-level=1 -volname Medora -srcfolder "$stage" "$work/Medora.dmg"
mv -f -- "$work/Medora.dmg" "$output"
printf 'Created %s\n' "$output"
