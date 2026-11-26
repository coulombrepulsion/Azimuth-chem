#!/usr/bin/env bash
# packaging/release.sh TAG FILE… — the files into the release of GitHub of TAG; the release is published once both
# installers are in it.
#
# Used by .github/workflows/release.yml (the user manual in PDF, seconds after the tag) and by build-windows.yml and
# build-macos.yml (each its installer, 15–30 minutes after). The release is made as a draft by the first of them
# (the words: packaging/release_notes.md) and stays a draft — not «latest» — while one installer is missing: the
# buttons of the site lead to releases/latest/download/… and give the files of the previous release till then, never
# a release with a hole. The one that finds both installers publishes it and makes it «latest».
set -euo pipefail
tag="$1"
shift
version="${tag#v}"
if ! gh release view "$tag" > /dev/null 2>&1; then
  sed "s/{version}/$version/g" packaging/release_notes.md > release-notes.md
  gh release create "$tag" --draft --verify-tag --title "Азимут $version" --notes-file release-notes.md
fi
gh release upload "$tag" "$@" --clobber
have="$(gh release view "$tag" --json assets --jq '.assets[].name')"
if grep -qx 'Azimuth-Setup-Windows-x64.exe' <<< "$have" && grep -qx 'Azimuth-macOS-arm64.dmg' <<< "$have"; then
  gh release edit "$tag" --draft=false --latest
  echo "the release $tag is published"
else
  echo "the release $tag stays a draft: an installer is not there yet"
fi
