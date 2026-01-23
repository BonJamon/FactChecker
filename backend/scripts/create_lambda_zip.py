import shutil
import subprocess
from pathlib import Path
import zipfile
import os 

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
APP_DIR = BACKEND_DIR / "app"

BUILD_DIR = BACKEND_DIR / ".build"
PACKAGE_DIR = BUILD_DIR / "package"
DIST_DIR = BACKEND_DIR / "dist"

REQUIREMENTS = PROJECT_ROOT / "pyproject.toml"
ZIP_NAME = "lambda_package.zip"


def run(cmd, cwd=None):
    print(f"> {' '.join(map(str, cmd))}")
    subprocess.check_call(cmd, cwd=cwd)


def clean():
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    DIST_DIR.mkdir(exist_ok=True)


def install_dependencies():
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    #copy requiremens into backend
    shutil.copy(REQUIREMENTS, APP_DIR / "pyproject.toml")

    # Convert Windows paths to Docker-friendly Linux paths
    def docker_path(p: Path) -> str:
        # Convert C:\Users\... -> /c/Users/...
        return "/" + str(p.resolve()).replace(":", "").replace("\\", "/")

    app_mount = docker_path(APP_DIR)

    subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{app_mount}:/var/task",
            "--entrypoint",
            "",
            "public.ecr.aws/lambda/python:3.14",
            "/bin/sh", "-c",
            f"pip install --upgrade pip && pip install pip-tools && pip-compile pyproject.toml  && pip install -r /var/task/requirements.txt -t /var/task/.build/package"
        ],
        cwd=str(PROJECT_ROOT),
        check=True,
    )
    os.remove(APP_DIR / "pyproject.toml")



def copy_app():
    for item in APP_DIR.iterdir():
        dest = PACKAGE_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


def create_zip():
    zip_path = DIST_DIR / ZIP_NAME

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for file in PACKAGE_DIR.rglob("*"):
            z.write(file, file.relative_to(PACKAGE_DIR))

    print(f"Created {zip_path}")


def main():
    clean()
    #compile_requirements()
    install_dependencies()
    copy_app()
    create_zip()


if __name__ == "__main__":
    main()
