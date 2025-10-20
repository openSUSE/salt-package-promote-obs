#!/usr/bin/python3
#
# This script takes care of the automation to keep the 
# packages from https://src.opensuse.org/saltbundle/ in sync
# with the packages at https://src.suse.de/Galaxy/
#
# The SOURCE_BRANCH for each package (at SOURCE_GIT_REPO/SOURCE_GIT_ORG)
# will be pushed to TARGET_BRANCHES (at TARGET_GIT_REPO/TARGET_GIT_ORG)
# with force.
#
# An access token for TARGET_GIT_REPO/TARGET_GIT_ORG is required
# with the following permissions:
#   - "repository/package/organization": read/write
#   - "user": read only
#

import json
import subprocess
import sys
import tempfile
from typing import List, Dict

import requests

SOURCE_GIT_REPO = "src.opensuse.org"
SOURCE_GIT_ORG = "saltbundle"
SOURCE_BRANCH = "bundle"

TARGET_GIT_REPO = "src.suse.de"
TARGET_GIT_ORG = "Galaxy"
TARGET_BRANCHES = ["mlmtools-main", "mlmtools-stable"]

TARGET_REPO_TOKEN = "PUT-YOUR-ACCESS-TOKEN-HERE"
AUTH_HEADERS = {"Authorization": f"Bearer {TARGET_REPO_TOKEN}"}

REPOS_TO_EXCLUDE = ["_ObsPrj"]


def _fetch_repos_json(git_repo: str, org: str) -> str:
    output = []
    keep_fetching = True
    page = 1

    while keep_fetching:
        ret = requests.get(
            f"https://{git_repo}/api/v1/users/{org}/repos?limit=100&page={page}"
        ).json()
        if not ret:
            keep_fetching = False
        else:
            page = page + 1
            output.extend(ret)

    return output


def _get_commit_hash(
    git_repo: str, org: str, repo_name: str, branch: str, headers: Dict = {}
) -> str:
    ret = None
    try:
        ret = requests.get(
            f"https://{git_repo}/api/v1/repos/{org}/{repo_name}/branches/{branch}",
            headers=headers,
        ).json()["commit"]["id"]
        return ret
    except Exception:
        print("---> ERROR: cannot get commit hash. Check configured access token!")
        sys.exit(1)


def _run_git(command: str, cwd: str = None):
    _cmd = f"git {command}"
    try:
        result = subprocess.run(
            _cmd, shell=True, check=True, capture_output=True, text=True, cwd=cwd
        )
        return result
    except subprocess.CalledProcessError as exc:
        print(f"   Git Command failed: {exc.cmd}")
        print(f"   STDOUT: {exc.stdout}")
        print(f"   STDERR: {exc.stderr}")
        sys.exit(1)


def _sync_branches_for_repo(repo_name: str):
    _run_git("init --bare --object-format=sha256", cwd=tmpdir)
    _run_git(
        f"remote add source https://{SOURCE_GIT_REPO}/{SOURCE_GIT_ORG}/{repo_name}",
        cwd=tmpdir,
    )
    _run_git(
        f"remote add target https://{TARGET_REPO_TOKEN}@{TARGET_GIT_REPO}/{TARGET_GIT_ORG}/{repo_name}",
        cwd=tmpdir,
    )
    _run_git(f"fetch source {SOURCE_BRANCH}:{SOURCE_BRANCH}", cwd=tmpdir)
    for tgt in TARGET_BRANCHES:
        _run_git(f"push target +{SOURCE_BRANCH}:{tgt}", cwd=tmpdir)


def get_repo_list(exclude: List[str]) -> List[str]:
    repos_json = _fetch_repos_json(SOURCE_GIT_REPO, SOURCE_GIT_ORG)
    return [repo["name"] for repo in repos_json if repo["name"] not in REPOS_TO_EXCLUDE]


with tempfile.TemporaryDirectory() as tmpdir:
    stats = {"processed": 0, "synced": []}
    for repo in get_repo_list(REPOS_TO_EXCLUDE):
        if "deb" not in repo:
            continue
        print(
            f"Processing package https://{SOURCE_GIT_REPO}/{SOURCE_GIT_ORG}/{repo} ..."
        )
        stats["processed"] += 1

        source_hash = _get_commit_hash(
            SOURCE_GIT_REPO, SOURCE_GIT_ORG, repo, SOURCE_BRANCH
        )
        print(f"---> HEAD ({SOURCE_BRANCH}): {source_hash}")
        force_sync = False
        for tgt in TARGET_BRANCHES:
            target_hash = _get_commit_hash(
                TARGET_GIT_REPO, TARGET_GIT_ORG, repo, tgt, AUTH_HEADERS
            )
            print(f"---> HEAD ({tgt}): {target_hash}")
            if source_hash != target_hash:
                print(f"---> YAY!!! We need to sync branch {tgt} here!")
                force_sync = True
        if force_sync:
            print(
                f"---> A sync is needed here against https://{TARGET_GIT_REPO}/{TARGET_GIT_ORG}/{repo} !!!"
            )
            try:
                _sync_branches_for_repo(repo)
                stats["synced"].append(repo)
            except Exception as exc:
                print(f"---> ERROR: {exc}")
            print(
                f"---> Pushed branch '{SOURCE_BRANCH}' from {SOURCE_GIT_REPO} to branches '{TARGET_BRANCHES}' at {TARGET_GIT_REPO}"
            )
            print("---> Successfully synced!")
        else:
            print("---> Nothing to sync here.")
        print()

    print("----------------------------------------------------------------")
    print(f" Packages that needed a synced: ", end="")
    if not stats["synced"]:
        print("(none)")
    else:
        for pkg in stats["synced"]:
            print()
            print(f" * {pkg}")
    print(f" Total packages already in sync: {stats['processed']}")
    print("----------------------------------------------------------------")
