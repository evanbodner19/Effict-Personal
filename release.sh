#!/usr/bin/env bash
set -e

# Usage: ./release.sh 1.0.1 "Release notes here"
VERSION="$1"
NOTES="${2:-Update}"

if [ -z "$VERSION" ]; then
  echo "Usage: ./release.sh <version> [notes]"
  exit 1
fi

cd "$(dirname "$0")/flutter_app"

# Bump version in pubspec.yaml
sed -i "s/^version: .*/version: $VERSION+1/" pubspec.yaml

# Build APK
C:/Users/EvBod/flutter/bin/flutter.bat build apk --release \
  --dart-define=SUPABASE_URL=https://bjwmbvkhundjnjyypbov.supabase.co \
  --dart-define=SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJqd21idmtodW5kam5qeXlwYm92Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyMTg5MDgsImV4cCI6MjA5MTc5NDkwOH0.flbM0uP_H9RG17rQBp5hq4hf8eJ6rsY0O4CorwrSdGA \
  --dart-define=BACKEND_URL=https://effict-personal-api.onrender.com

cd ..

# Commit and tag
git add flutter_app/pubspec.yaml
git commit -m "chore: bump version to $VERSION"
git tag "v$VERSION"
git push && git push --tags

# Create GitHub release with APK
gh release create "v$VERSION" \
  flutter_app/build/app/outputs/flutter-apk/app-release.apk \
  --title "v$VERSION" \
  --notes "$NOTES"

echo "Released v$VERSION"
