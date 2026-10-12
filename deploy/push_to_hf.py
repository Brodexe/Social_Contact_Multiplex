"""
Publish the interactive app to a Hugging Face static Space.

Builds deploy/site/ (see deploy/build_static.py) and uploads it, removing files
on the Space that are no longer part of the build. Static Spaces are free; the
simulation runs in each visitor's browser, so nothing needs a server.

One-time setup:  hf auth login   (token with write access from
https://huggingface.co/settings/tokens)

Run from the repo root:  python deploy/push_to_hf.py [--space USER/NAME]
"""

import argparse
import os
import sys

from huggingface_hub import HfApi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_static import build  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--space", help="USER/NAME (default: <your HF username>/multiplex-sirs)")
    args = parser.parse_args()

    api = HfApi()
    space = args.space or f"{api.whoami()['name']}/multiplex-sirs"
    api.create_repo(space, repo_type="space", space_sdk="static", exist_ok=True)
    api.upload_folder(repo_id=space, repo_type="space", folder_path=build(),
                      delete_patterns=["*"],  # .gitattributes is always kept
                      commit_message="Deploy interactive app")

    user, name = space.split("/")
    print(f"Space: https://huggingface.co/spaces/{space}")
    print(f"App:   https://{f'{user}-{name}'.lower()}.static.hf.space")


if __name__ == "__main__":
    main()
