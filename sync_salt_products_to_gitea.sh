#!/bin/bash
#
# sync_salt_products_to_gitea.sh
#
# Synchronizes contents of an OBS package to a specific branch
# in Gitea repository.
#
# Usage:
#   ./sync_salt_products_to_gitea.sh <OBS_PROJECT> <OBS_PACKAGE> <GIT_REPO_URL> <GIT_BRANCH>
#

set -e

if [ "$#" -ne 4 ]; then
    echo "Error: Incorrect number of arguments provided."
    echo ""
    echo "Usage: $0 <OBS_PROJECT> <OBS_PACKAGE> <GIT_REPO_URL> <GIT_BRANCH>"
    exit 1
fi

if [ ! -v GITEA_TOKEN ]; then
    echo "Error: You must define GITEA_TOKEN environment variable"
    exit 1
fi

OBS_PROJECT="$1"
OBS_PACKAGE="$2"
GIT_REPO_URL="$3"
GIT_BRANCH="$4"
COMMIT_AUTHOR="Salt Jenkins Automation <salt-ci@suse.de>"

# Setup and Cleanup
WORKSPACE=$(mktemp -d -t obs_sync_XXXXXX)
trap 'rm -rf "$WORKSPACE"' EXIT
echo "Created temporary workspace at $WORKSPACE"

# Fetch OBS Package Content
echo "----------------------------------------------------------------------------------"
echo "Checking out OBS package: $OBS_PROJECT/$OBS_PACKAGE"
echo "----------------------------------------------------------------------------------"
cd "$WORKSPACE"

# Checkout the package from OBS
osc checkout "$OBS_PROJECT" "$OBS_PACKAGE"

OBS_CONTENT_DIR="$WORKSPACE/$OBS_PROJECT/$OBS_PACKAGE"

if [ ! -d "$OBS_CONTENT_DIR" ]; then
    echo "Error: Failed to checkout OBS package. Directory not found."
    exit 1
fi

# Sync and push to Gitea
echo
echo "----------------------------------------------------------------------------------"
echo "Processing target Git repo: $GIT_REPO_URL (Branch: $GIT_BRANCH)"
echo "----------------------------------------------------------------------------------"

GIT_DIR="$WORKSPACE/git_repo"

# Clone the specific branch of the repository
echo "Cloning repository..."
git clone --branch "$GIT_BRANCH" --depth 1 "${GIT_REPO_URL/:\/\//:\/\/${GITEA_TOKEN}@}" "$GIT_DIR" > /dev/null

rsync -av --delete \
    --exclude='.git' \
    --exclude='.osc' \
    --exclude='.gitignore' \
    --exclude='.gitattributes' \
    "$OBS_CONTENT_DIR/" "$GIT_DIR/" > /dev/null

cd "$GIT_DIR"

# Stage all changes
git add -A

# Check if there are actual changes to commit
if git diff-index --quiet HEAD --; then
    echo "No changes detected. Skipping commit and push."
    exit 0
else
    echo "Changes detected. Committing..."
    git commit -m "Automated sync: Updates from OBS $OBS_PROJECT/$OBS_PACKAGE" --author="$COMMIT_AUTHOR"

    echo "Pushing to Git..."
    git push origin "$GIT_BRANCH" > /dev/null

    echo "=================================================================================="
    echo "Successfully synced $OBS_PACKAGE to $GIT_BRANCH!"
    echo "=================================================================================="
fi
