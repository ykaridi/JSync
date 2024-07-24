"""
Small script to create Python type stubs for the Java packages used in JSync.
Contributed by noamzaks
"""

import importlib
import os
import shutil
import re
import argparse
from pathlib import Path


ROOT = Path(__file__).absolute().parent.parent
TYPINGS = ROOT / 'typings'

PACKAGES_FOR_STUBS = [
    "java",
    "jadx",
    "com.pnfsoftware.jeb",
    "org.slf4j",
    "org.python",
    "javax.swing",
]


def get_jadx_dependencies():
    build = (ROOT / 'jadx' / 'build.gradle.kts').read_text()
    
    for line in build.splitlines():
        match = re.search(r'(api|compileOnly|implementation|runtimeOnly|testImplementation)'
                          r'\("(?P<dep>(.+):(.+):(.+))"\)', line)
        if not match:
            continue
        
        yield match.group('dep')


def get_dependency_jars(dependency: str):
    assert dependency.count(":") == 2
    [package, name, version] = dependency.split(":")
    directory = Path(os.path.expanduser(f"~/.gradle/caches/modules-2/files-2.1/{package}/{name}"))
    
    return [p for p in directory.glob('**/*.jar') if not p.name.endswith('-sources.jar')]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate stubs for JSync")
    
    # Define two keyword arguments
    parser.add_argument('--jeb', type=Path, required=True, help='JEB Directory')
    parser.add_argument('--jadx', type=Path, required=True, help='JADX Directory')
    
    args = parser.parse_args()
    jeb_directory = args.jeb
    jadx_directory = args.jadx
        
    jars = []

    for directory in [jeb_directory, jadx_directory]:
        if directory.exists():
            jars.extend(directory.glob("**/*.jar"))

    jadx_dependencies = get_jadx_dependencies()
    for dependency in jadx_dependencies:
        jars += get_dependency_jars(dependency)

    for child in TYPINGS.iterdir():
        if child.is_dir():
            shutil.rmtree(child)

    # make sure there is no 'jadx' folder, otherwise the Python importer will use it instead of the Java package.
    import jpype
    import stubgenj

    jpype.startJVM("", convertStrings=True, classpath=[os.path.abspath(p) for p in jars])
    import jpype.imports

    stubgenj.generateJavaStubs(
        [importlib.import_module(package) for package in PACKAGES_FOR_STUBS],
        useStubsSuffix=False,
        jpypeJPackageStubs=False,
    )
