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
from difflib import unified_diff
from traceback import format_exc
from subprocess import run, CalledProcessError
from lxml import etree
from osctiny import Osc
from osctiny.extensions.packages import Package
from osctiny.extensions.projects import Project

def copy_packages(client, src, dst, subproject=None):
    pkg_handler = Package(client)
    if subproject is not None:
        src = src + ":" + subproject
        dst = dst + ":" + subproject

    packages_list = pkg_handler.get_list(project=src)
    for package in packages_list.iter():
        package_name = package.attrib.get("name")
        # Only copypac the packages that are not linked to other package.
        # Packages with no link should be the ones that we mainain.
        if package_name is not None and not has_link(client, src, package_name):
            try:
                result = get_diff(src, dst, package_name)
                print(f"Diff for {package_name}: {result}")
                if result != "":
                    print(f"Copying {package_name} from {src} to {dst}")
                    run(["osc", "copypac", src, package_name, dst], check=True)
            except CalledProcessError:
                print(f"Could not copypac {package_name}")
                print(format_exc())
                sys.exit(1)

def get_diff(src, dst, pkgname) -> str:
    result = run(["osc", "rdiff", src, pkgname, dst], check=True, capture_output=True)
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
    pkg_files = pkg_handler.get_files(project,package)
    linkinfo = etree.fromstring(etree.tostring(pkg_files).decode('utf-8')).find("linkinfo")
    return linkinfo is not None

if __name__ == "__main__":
    osc = Osc(url="https://api.opensuse.org/")

    BASE_SRC = sys.argv[1]
    BASE_DST = sys.argv[2]

    copy_packages(osc, BASE_SRC, BASE_DST)

    subprojects_src = get_subprojects(osc, BASE_SRC)
    subprojects_dst = get_subprojects(osc, BASE_DST)

    for subproject_src in subprojects_src:
        sp_name = subproject_src[len(BASE_SRC) + 1:]
        subproject_src = BASE_SRC + ":" + sp_name
        subproject_dst = BASE_DST + ":" + sp_name

        if subproject_dst in subprojects_dst:
            copy_packages(osc, BASE_SRC, BASE_DST, sp_name)

            cfg_src = get_project_config(osc, subproject_src)
            cfg_dst = get_project_config(osc, subproject_dst)
            print(f"Configuration diff for {subproject_src} and {subproject_dst}")
            for line in unified_diff(cfg_src.splitlines(), cfg_dst.splitlines()):
                print(line)

            set_project_config(osc, BASE_DST + ":" + sp_name, cfg_src)
        else:
            print(f"The project {subproject_dst} does not exist.")
            