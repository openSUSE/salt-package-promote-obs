#!/usr/bin/python3
"""
This scripts performs the promotion of Salt Bundle packages

Takes all packages at from a given organization in a Git server
and pushes from the specified source branch to a target branch
in the same repository (or different repository)
"""

import os
import subprocess
import sys
import tempfile

import scmutils

SOURCE_GIT_SERVER = "src.opensuse.org"
SOURCE_GIT_ORG = "saltbundle"
SOURCE_BRANCH = "bundle_testing"

TARGET_GIT_SERVER = "src.opensuse.org"
TARGET_GIT_ORG = "saltbundle"
TARGET_BRANCH = "bundle"

TARGET_REPO_TOKEN = os.environ.get("GITEA_TOKEN", "PUT-YOUR-ACCESS-TOKEN-HERE")
AUTH_HEADERS = {"Authorization": f"Bearer {TARGET_REPO_TOKEN}"}

REPOS_TO_EXCLUDE = ["_ObsPrj"]


stats = {"processed": 0, "promoted": [], "to_sync": [], "errors": []}
for repo in scmutils.get_repo_list(
    git_server=SOURCE_GIT_SERVER, org=SOURCE_GIT_ORG, exclude=REPOS_TO_EXCLUDE
):
    print(f"Processing package https://{SOURCE_GIT_SERVER}/{SOURCE_GIT_ORG}/{repo} ...")
    stats["processed"] += 1

    try:
        source_hash = scmutils.get_commit_hash(
            git_server=SOURCE_GIT_SERVER,
            org=SOURCE_GIT_ORG,
            repo_name=repo,
            branch=SOURCE_BRANCH,
        )
        print(f"---> HEAD ({SOURCE_BRANCH}): {source_hash}")
        target_hash = scmutils.get_commit_hash(
            git_server=TARGET_GIT_SERVER,
            org=TARGET_GIT_ORG,
            repo_name=repo,
            branch=TARGET_BRANCH,
        )
        print(f"---> HEAD ({TARGET_BRANCH}): {target_hash}")
    except Exception:
        print("---> ERROR: cannot get commit hash. Check configured access token!")
        stats["errors"].append(repo)
        continue

    if source_hash != target_hash:
        print(f"---> YAY!!! We need to promote '{SOURCE_BRANCH}' branch here!")
        stats["to_sync"].append(repo)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    scmutils.promote_package(
                        git_server=SOURCE_GIT_SERVER,
                        org=SOURCE_GIT_ORG,
                        repo_name=repo,
                        source_branch=SOURCE_BRANCH,
                        target_branch=TARGET_BRANCH,
                        auth_token=TARGET_REPO_TOKEN,
                        cwd=tmpdir,
                    )
                    stats["promoted"].append(repo)
                except subprocess.CalledProcessError as exc:
                    print(f"   Git Command failed: {exc.cmd}")
                    print(f"   STDOUT: {exc.stdout}")
                    print(f"   STDERR: {exc.stderr}")
                    stats["errors"].append(repo)
                    print()
                    continue
        except Exception as exc:
            print(f"---> ERROR: {exc}")
            stats["errors"].append(repo)
            print()
            continue
        print(
            f"---> Promoted '{SOURCE_BRANCH}' branch from https://{SOURCE_GIT_SERVER}/{SOURCE_GIT_ORG} to branch '{TARGET_BRANCH}' at https://{TARGET_GIT_SERVER}/{TARGET_GIT_ORG}"
        )
        print("---> Successfully promoted!")
    else:
        print("---> Nothing to promote here.")
    print()

print("----------------------------------------------------------------")
print(f" Total packages processed: {stats['processed']}")
print(" Packages that required to be promoted: ", end="")
if not stats["to_sync"]:
    print("(none)")
else:
    print(len(stats["to_sync"]))
print(" Packages that were successfully promoted: ", end="")
if not stats["promoted"]:
    print("(none)")
else:
    print()
    for pkg in stats["promoted"]:
        print(f" * {pkg}")
if stats["errors"]:
    print(" Packages with errors:")
    for pkg in stats["errors"]:
        print(f" * ERROR {pkg}")
print("----------------------------------------------------------------")

if stats["errors"]:
    sys.exit(1)
