#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/Users/greavet/src/compunet-reborn"
BUNDLE_FILE="compunet-reborn.bundle"
REMOTE_URL="git@github.com:tgreaves/compunet-reborn.git"
CONTAINER_NAME="repo-transfer-sim"

# Only push branches that should exist on the remote
BRANCHES="main 94-partyline-cursor-keys-history-scrolling-crash-other-updates"

echo "==> Bundling repository (active branches + tags)..."
cd "$REPO_DIR"
BUNDLE_REFS=""
for b in $BRANCHES; do
    BUNDLE_REFS="$BUNDLE_REFS refs/heads/$b"
done
git bundle create "$BUNDLE_FILE" $BUNDLE_REFS --tags
echo "    Created $BUNDLE_FILE"

echo "==> Starting Docker container (with SSH agent forwarding)..."
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
docker run -d --name "$CONTAINER_NAME" \
    --mount type=bind,src=/run/host-services/ssh-auth.sock,target=/run/host-services/ssh-auth.sock \
    -e SSH_AUTH_SOCK=/run/host-services/ssh-auth.sock \
    alpine:latest sleep 3600

echo "==> Installing git in container..."
docker exec "$CONTAINER_NAME" apk add --no-cache git openssh

echo "==> Copying bundle into container..."
docker cp "$REPO_DIR/$BUNDLE_FILE" "$CONTAINER_NAME:/tmp/$BUNDLE_FILE"

echo "==> Setting up repo from bundle inside container..."
docker exec "$CONTAINER_NAME" sh -c 'git init /repo && cd /repo && git fetch /tmp/'"$BUNDLE_FILE"' "refs/heads/*:refs/heads/*" "refs/tags/*:refs/tags/*"'

echo "==> Adding remote '$REMOTE_URL'..."
docker exec -w /repo "$CONTAINER_NAME" git remote add origin "$REMOTE_URL"

echo "==> Pushing branches to remote..."
docker exec -w /repo "$CONTAINER_NAME" \
    sh -c 'GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no" git push origin '"$BRANCHES"''
docker exec -w /repo "$CONTAINER_NAME" \
    sh -c 'GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no" git push origin --tags'

echo "==> Cleaning up..."
docker rm -f "$CONTAINER_NAME"
rm -f "$REPO_DIR/$BUNDLE_FILE"

echo "==> Done! All branches and tags pushed to $REMOTE_URL"
