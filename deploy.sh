#!/bin/bash
# Deploy to live GitHub Pages site.
# Run this after every commit that should go live.
# Usage: ./deploy.sh [optional: branch name, defaults to current branch]

set -e

LIVE_BRANCH="claude/hansen-solubility-planning-D5iok"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
SOURCE_BRANCH="${1:-$CURRENT_BRANCH}"

echo "Deploying $SOURCE_BRANCH → live site ($LIVE_BRANCH)..."

# Push feature branch to origin (required by session rules)
git push -u origin "$SOURCE_BRANCH"

# Push to github remote live branch
git push github "$SOURCE_BRANCH:$LIVE_BRANCH"

echo "Done. Live site updated: https://jtreeder.github.io/Materialism/"
