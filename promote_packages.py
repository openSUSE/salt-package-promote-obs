#!/usr/bin/python3
"""
This script is used to copy packages from one OBS project to another
and does the same for its subprojects.

- Takes source and destination project names from arguments.
- Shows diff between source an destination packages before copying
for both project and subprojects.
- Shows diff between configurations of subprojects and copy the
configuration from source to destination subproject.
"""

import sys
from argparse import ArgumentParser
from difflib import unified_diff
from traceback import format_exc
from subprocess import run, CalledProcessError, PIPE
from lxml import etree
from osctiny import Osc
from osctiny.extensions.packages import Package
from osctiny.extensions.projects import Project


def copy_packages(client, src, dst, subproject=None, exclude_packages=None):
    pkg_handler = Package(client)
    if subproject is not None:
        src = src + ":" + subproject
        dst = dst + ":" + subproject

    if exclude_packages is None:
        exclude_packages = []

    packages_list = pkg_handler.get_list(project=src)
    for package in packages_list.iter():
        package_name = package.attrib.get("name")
        # Only copypac the packages that are not linked to other package.
        # Packages with no link should be the ones that we mainain.
        if (
            package_name is not None
            and package_name not in exclude_packages
            and not has_link(client, src, package_name)
        ):
            try:
                result = get_diff(src, dst, package_name)
                print(
                    "###################################################################",
                    flush=True,
                )
                print(f"Diff for '{package_name}' package from '{src}' to '{dst}':\n {result}", flush=True)
                print(
                    "###################################################################",
                    flush=True,
                )
                if result != "":
                    print(f"Copying '{package_name}' from '{src}' to '{dst}'\n", flush=True)
                    run(["osc", "copypac", src, package_name, dst], check=True)
            except CalledProcessError:
                print(f"Could not copypac '{package_name}'\n", flush=True)
                print(format_exc(), flush=True)
                sys.exit(1)


def get_diff(src, dst, pkgname) -> str:
    result = run(
        ["osc", "rdiff", dst, pkgname, src], check=True, stdout=PIPE, stderr=PIPE
    )
    return result.stdout.decode("utf-8")


def get_subprojects(client, project_name) -> list:
    prefix = project_name + ":"
    root = client.search.project("starts-with(@name,'" + prefix + "')")
    return [p.attrib["name"] for p in root.findall("project")]


def get_project_config(client, project_name) -> str:
    project_handler = Project(client)
    return project_handler.get_config(project_name)


def set_project_config(client, prj, config):
    project_handler = Project(client)
    project_handler.set_config(prj, config=config)


def has_link(client, project, package) -> bool:
    pkg_handler = Package(client)
    pkg_files = pkg_handler.get_files(project, package)
    linkinfo = etree.fromstring(etree.tostring(pkg_files).decode("utf-8")).find(
        "linkinfo"
    )
    return linkinfo is not None


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-s", "--source", dest="src", help="Source Project")
    parser.add_argument("-t", "--target", dest="dst", help="Target Project")
    parser.add_argument(
        "-A", "--apiurl", dest="url", default="https://api.opensuse.org",
        help="URL to Build Service API"
    )
    parser.add_argument(
        "--exclude", dest="exclude_packages", action="append", metavar="PACKAGE_TO_EXCLUDE"
    )
    parser.add_argument(
        "--exclude-subproject", dest="exclude_subproject", action="append", metavar="SUBPROJECT_TO_EXCLUDE"
    )

    commands = parser.add_subparsers(dest="action", title='Available actions')
    commands.add_parser('packages', help="Promote packages from Source to Target projects")
    commands.add_parser('subprojects', help="Promote packages inside subprojects")
    commands.add_parser('projectconfigs', help="Promote project configs for subprojects")
    commands.add_parser('all', help="Perform all the actions")

    args = parser.parse_args()

    osc = Osc(url=args.url)

    BASE_SRC = args.src
    BASE_DST = args.dst
    exclude = args.exclude_packages
    exclude_subprojects = args.exclude_subproject if args.exclude_subproject is not None else []

    if args.action in ["packages", "all"]:
        copy_packages(osc, BASE_SRC, BASE_DST, exclude_packages=exclude)

    if args.action in ["subprojects", "projectconfigs", "all"]:
        subprojects_src = get_subprojects(osc, BASE_SRC)
        subprojects_dst = get_subprojects(osc, BASE_DST)

        for subproject_src in subprojects_src:
            if subproject_src in exclude_subprojects:
                continue
            sp_name = subproject_src[len(BASE_SRC) + 1 :]
            subproject_src = BASE_SRC + ":" + sp_name
            subproject_dst = BASE_DST + ":" + sp_name
            if subproject_dst in subprojects_dst:
                if args.action in ["subprojects", "all"]:
                    copy_packages(osc, BASE_SRC, BASE_DST, sp_name, exclude)

                if args.action in ["projectconfigs", "all"]:
                    cfg_src = get_project_config(osc, subproject_src)
                    cfg_dst = get_project_config(osc, subproject_dst)
                    print(
                        "###################################################################",
                        flush=True,
                    )
                    print(
                        f"Configuration diff for '{subproject_src}' and '{subproject_dst}':\n",
                        flush=True,
                    )
                    for line in unified_diff(cfg_src.splitlines(), cfg_dst.splitlines()):
                        print(line, flush=True)
                    print(
                        "###################################################################",
                        flush=True,
                    )

                    set_project_config(osc, BASE_DST + ":" + sp_name, cfg_src)
            else:
                print(f"The project '{subproject_dst}' does not exist.\n", flush=True)
