#!/usr/bin/python3
"""
This file contains helper functions to interact with
Git repositories and perform some operations
"""

import subprocess
from typing import Dict, List

import requests


def fetch_repos_json(git_server: str, org: str) -> str:
    """
    Use gitea API to fetch the list of repositories for a given organization.
    """
    output = []
    keep_fetching = True
    page = 1

    while keep_fetching:
        ret = requests.get(
            f"https://{git_server}/api/v1/users/{org}/repos?limit=100&page={page}"
        ).json()
        if not ret:
            keep_fetching = False
        else:
            page += 1
            output.extend(ret)

    return output


def get_commit_hash(
    git_server: str, org: str, repo_name: str, branch: str, headers: Dict = {}
) -> str:
    """
    Get latest commit hash for a given branch name
    """
    ret = None
    ret = requests.get(
        f"https://{git_server}/api/v1/repos/{org}/{repo_name}/branches/{branch}",
        headers=headers,
    ).json()["commit"]["id"]
    return ret


def run_git(command: str, cwd: str = None, check: bool = True):
    """
    Run a git command
    """
    _cmd = f"git {command}"
    result = subprocess.run(
        _cmd,
        shell=True,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd=cwd,
    )
    return result


def promote_project_config(
    git_server: str,
    org: str,
    source_branch: str,
    target_branch: str,
    auth_token: str,
    cwd: str,
):
    """
    Copy changes on _config file from SOURCE_BRANCH to TARGET_BRANCH
    """
    COMMIT_MESSAGE = f"Merge changes from {source_branch} branch"
    PROJCONFIG_FILE = "_config"
    REPONAME = "_ObsPrj"
    run_git(
        f"clone https://{auth_token}@{git_server}/{org}/{REPONAME} -b {source_branch} .",
        cwd=cwd,
    )
    run_git(f"checkout {target_branch}", cwd=cwd)
    run_git(f"checkout {source_branch} -- {PROJCONFIG_FILE}", cwd=cwd)
    changes_exist = run_git(
        f"diff --cached --quiet {PROJCONFIG_FILE}", check=False, cwd=cwd
    ).returncode
    if not changes_exist:
        return False
    print("---> Here is the diff:\n")
    print(run_git("diff --staged", cwd=cwd).stdout)
    run_git(f"commit -m {COMMIT_MESSAGE}", cwd=cwd)
    run_git(f"push origin {target_branch}", cwd=cwd)
    return True


def promote_package(
    git_server: str,
    org: str,
    repo_name: str,
    source_branch: str,
    target_branch: str,
    auth_token: str,
    cwd: str,
):
    """
    Promote SOURCE_BRANCH to TARGET_BRANCH
    """
    run_git("init --bare --object-format=sha256", cwd=cwd)
    run_git(
        f"remote add source https://{git_server}/{org}/{repo_name}",
        cwd=cwd,
    )
    run_git(
        f"remote add target https://{auth_token}@{git_server}/{org}/{repo_name}",
        cwd=cwd,
    )
    run_git(f"fetch source {source_branch}:{source_branch}", cwd=cwd)
    run_git(f"fetch target {target_branch}:{target_branch}", cwd=cwd)
    print(
        run_git(f"diff target/{target_branch}..source/{source_branch}", cwd=cwd).stdout
    )
    run_git(f"push target {source_branch}:{target_branch}", cwd=cwd)


def sync_branches_for_repo(
    source_git_server: str,
    source_org: str,
    repo_name: str,
    source_branch: str,
    target_git_server: str,
    target_org: str,
    target_branches: List[str],
    cwd: str,
):
    """
    Synchronize target_branches according to source_branch
    """
    run_git("init --bare --object-format=sha256", cwd=cwd)
    run_git(
        f"remote add source https://{source_git_server}/{source_org}/{repo_name}",
        cwd=cwd,
    )
    run_git(
        f"remote add target https://{auth_token}@{target_git_server}/{target_org}/{repo_name}",
        cwd=cwd,
    )
    run_git(f"fetch source {source_branch}:{source_branch}", cwd=cwd)
    for tgt in target_branches:
        run_git(f"push target {source_branch}:{tgt}", cwd=cwd)


def get_repo_list(git_server: str, org: str, exclude: List[str] = None) -> List[str]:
    """
    Returns the list of repository names to process without excluded repositories
    """
    if not exclude:
        exclude = []
    repos_json = fetch_repos_json(git_server, org)
    return [repo["name"] for repo in repos_json if repo["name"] not in exclude]
