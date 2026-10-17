"""Upload the app to a Hugging Face Space and sync its runtime secrets.

Reads everything from environment variables set by .github/workflows/deploy.yml.
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

# Keys the running app needs (passed on to the Space as Space secrets)
APP_SECRETS = [
    "SEARCH_ENDPOINT",
    "SEARCH_ADMIN_KEY",
    "SEARCH_INDEX_NAME",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_KEY",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
    "OPENAI_API_KEY",
    "AZURE_STORAGE_CONNECTION_STRING",
    "BLOB_CONTAINER_NAME",
]

# HF Spaces read their settings from front matter at the top of README.md;
# the GitHub README has none, so the Space gets its own.
SPACE_README = """---
title: DocChat {env}
emoji: 📄
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
---

Deployed automatically from GitHub Actions ({env}).
"""


def main():
    space_id = os.environ["HF_SPACE_ID"]
    app_env = os.environ["APP_ENV"]
    api = HfApi(token=os.environ["HF_TOKEN"])

    # Creates the Space on the first deploy; does nothing if it exists
    api.create_repo(space_id, repo_type="space", space_sdk="docker", exist_ok=True)

    for name in APP_SECRETS:
        if os.environ.get(name):
            api.add_space_secret(space_id, name, os.environ[name])
    api.add_space_variable(space_id, "APP_ENV", app_env)

    # Copy only git-tracked files, so nothing ignored or local is uploaded
    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    with tempfile.TemporaryDirectory() as tmp:
        for f in tracked:
            if f.startswith(".github/"):
                continue
            dest = Path(tmp, f)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
        Path(tmp, "README.md").write_text(SPACE_README.format(env=app_env), encoding="utf-8")

        api.upload_folder(
            folder_path=tmp,
            repo_id=space_id,
            repo_type="space",
            commit_message=f"Deploy {os.environ.get('GITHUB_SHA', 'local')[:7]} ({app_env})",
        )

    print(f"Deployed to https://huggingface.co/spaces/{space_id}")


if __name__ == "__main__":
    main()
