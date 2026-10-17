
"""Download Ontop CLI 5.5.0 and the PostgreSQL JDBC driver.

Run from the project root:

    python session_05/ontop/setup_ontop.py

Requires Java (JDK 21) and an internet connection.
"""

import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen


HERE = Path(__file__).resolve().parent

CLI_URL = (
    "https://github.com/ontop/ontop/releases/download/"
    "ontop-5.5.0/ontop-cli-5.5.0.zip"
)

JDBC_URL = (
    "https://github.com/pgjdbc/pgjdbc/releases/download/"
    "REL42.7.13/postgresql-42.7.13.jar"
)

CLI_DIR = HERE / "ontop-cli"

EXECUTABLE = CLI_DIR / (
    "ontop.bat"
    if platform.system() == "Windows"
    else "ontop"
)


def download(url, destination):
    print(f"Downloading {url.rsplit('/', 1)[-1]}...")

    with urlopen(url, timeout=120) as response:
        with open(destination, "wb") as output:
            shutil.copyfileobj(response, output)


def main():

    if shutil.which("java") is None:
        sys.exit(
            "Java not found. Install JDK 21 and restart VS Code."
        )

    result = subprocess.run(
        ["java", "-version"],
        capture_output=True,
        text=True
    )

    print(result.stderr.splitlines()[0])

    if not EXECUTABLE.exists():

        archive = HERE / "ontop-cli.zip"

        download(CLI_URL, archive)

        with zipfile.ZipFile(archive) as zip_file:
            zip_file.extractall(CLI_DIR)

        archive.unlink()

        if platform.system() != "Windows":
            EXECUTABLE.chmod(0o755)

    jdbc_file = (
        CLI_DIR
        / "jdbc"
        / "postgresql-42.7.13.jar"
    )

    if not jdbc_file.exists():

        jdbc_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        download(JDBC_URL, jdbc_file)

    print("\nOntop setup completed.")
    print(f"Executable: {EXECUTABLE}")
    print(f"JDBC driver: {jdbc_file}")


if __name__ == "__main__":
    main()
