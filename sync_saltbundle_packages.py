#!/usr/bin/python3
"""
This script takes care of the automation to keep the
packages from https://src.opensuse.org/saltbundle/ in sync
with the packages at https://src.suse.de/Galaxy/

The SOURCE_BRANCH for each package (at SOURCE_GIT_SERVER/SOURCE_GIT_ORG)
will be pushed to TARGET_BRANCHES (at TARGET_GIT_SERVER/TARGET_GIT_ORG).

An access token for TARGET_GIT_SERVER/TARGET_GIT_ORG is required
with the following permissions:
  - "repository/package/organization": read/write
  - "user": read only
"""

import os
import subprocess
import sys
import tempfile

import scmutils

SOURCE_GIT_SERVER = "src.opensuse.org"
SOURCE_GIT_ORG = "saltbundle"
SOURCE_BRANCH = "bundle"

TARGET_GIT_SERVER = "src.suse.de"
TARGET_GIT_ORG = "Galaxy"
TARGET_BRANCHES = ["mlmtools-main", "mlmtools-stable"]

TARGET_REPO_TOKEN = os.environ.get("GITEA_TOKEN", "PUT-YOUR-ACCESS-TOKEN-HERE")
AUTH_HEADERS = {"Authorization": f"Bearer {TARGET_REPO_TOKEN}"}

REPOS_TO_EXCLUDE = ["_ObsPrj"]


stats = {"processed": 0, "synced": [], "to_sync": [], "errors": []}
for repo in scmutils.get_repo_list(
    git_server=SOURCE_GIT_SERVER, org=SOURCE_GIT_ORG, exclude=REPOS_TO_EXCLUDE
):
    print(f"Processing package https://{SOURCE_GIT_SERVER}/{SOURCE_GIT_ORG}/{repo} ...")
    stats["processed"] += 1
    force_sync = False

    try:
        source_hash = scmutils.get_commit_hash(
            git_server=SOURCE_GIT_SERVER,
            org=SOURCE_GIT_ORG,
            repo_name=repo,
            branch=SOURCE_BRANCH,
        )
        print(f"---> HEAD ({SOURCE_BRANCH}): {source_hash}")
        for tgt in TARGET_BRANCHES:
            target_hash = scmutils.get_commit_hash(
                git_server=TARGET_GIT_SERVER,
                org=TARGET_GIT_ORG,
                repo_name=repo,
                branch=tgt,
                headers=AUTH_HEADERS,
            )
            print(f"---> HEAD ({tgt}): {target_hash}")
            if source_hash != target_hash:
                print(f"---> YAY!!! We need to sync branch {tgt} here!")
                force_sync = True
    except Exception:
        print("---> ERROR: cannot get commit hash. Check configured access token!")
        print()
        stats["errors"].append(repo)
        continue

    if force_sync:
        print(
            f"---> A sync is needed here against https://{TARGET_GIT_SERVER}/{TARGET_GIT_ORG}/{repo} !!!"
        )
        stats["to_sync"].append(repo)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    scmutils.sync_branches_for_repo(
                        source_git_server=SOURCE_GIT_SERVER,
                        source_org=SOURCE_GIT_ORG,
                        repo_name=repo,
                        source_branch=SOURCE_BRANCH,
                        target_git_server=TARGET_GIT_SERVER,
                        target_org=TARGET_GIT_ORG,
                        target_branches=TARGET_BRANCHES,
                        auth_token=TARGET_REPO_TOKEN,
                        cwd=tmpdir,
                    )
                    stats["synced"].append(repo)
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
            f"---> Pushed branch '{SOURCE_BRANCH}' from {SOURCE_GIT_SERVER} to branches '{TARGET_BRANCHES}' at {TARGET_GIT_SERVER}"
        )
        print("---> Successfully synced!")
    else:
        print("---> Nothing to sync here.")
    print()

print("----------------------------------------------------------------")
print(f" Total packages processed: {stats['processed']}")
print(" Packages that required a sync: ", end="")
if not stats["to_sync"]:
    print("(none)")
else:
    print(len(stats["to_sync"]))
print(" Packages that were successfully synced: ", end="")
if not stats["synced"]:
    print("(none)")
else:
    print(len(stats["synced"]))
    for pkg in stats["synced"]:
        print(f" * {pkg}")
print(" Packages with errors: ", end="")
if not stats["errors"]:
    print("(none)")
else:
    print(len(stats["errors"]))
    for pkg in stats["errors"]:
        print(f" * ERROR {pkg}")
print("----------------------------------------------------------------")

if stats["errors"]:
    sys.exit(1)
