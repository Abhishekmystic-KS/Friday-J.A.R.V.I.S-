import base64
import os
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / "env" / ".env"


def _read_key(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    if ENV_PATH.exists():
        return (dotenv_values(ENV_PATH).get(name) or "").strip()
    return ""


GITHUB_TOKEN = _read_key("GITHUB_TOKEN")

HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

PROFILES = [
    "AkshathaaRk",
    "Abhishekmystic-KS",
]

OUTPUT_DIR = Path(__file__).parent.parent / "knowledge" / "github"


def fetch(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def get_readme(owner, repo):
    try:
        data = fetch(f"https://api.github.com/repos/{owner}/{repo}/readme")
        return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def ingest_profile(username):
    print(f"[github] Fetching {username}...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    profile = fetch(f"https://api.github.com/users/{username}")

    profile_text = f"""# GitHub Profile: {username}

Name: {profile.get('name', username)}
Bio: {profile.get('bio', 'N/A')}
Location: {profile.get('location', 'N/A')}
Company: {profile.get('company', 'N/A')}
Public repos: {profile.get('public_repos', 0)}
Followers: {profile.get('followers', 0)}
Profile URL: {profile.get('html_url')}
"""

    repos = fetch(f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated")
    repo_lines = []
    readme_docs = []

    for repo in repos:
        if repo.get("fork"):
            continue

        name = repo["name"]
        desc = repo.get("description") or "No description"
        lang = repo.get("language") or "Unknown"
        stars = repo.get("stargazers_count", 0)
        topics = ", ".join(repo.get("topics", [])) or "none"
        url = repo.get("html_url", "")

        repo_lines.append(f"- {name} ({lang}, *{stars}): {desc} | topics: {topics} | {url}")

        if stars > 0 or desc != "No description":
            readme = get_readme(username, name)
            if readme and len(readme) > 100:
                readme_docs.append(f"## {username}/{name}\n\n{readme[:3000]}")

        time.sleep(0.2)

    profile_text += "\n## Repositories\n\n" + "\n".join(repo_lines)

    profile_file = OUTPUT_DIR / f"{username}_profile.md"
    profile_file.write_text(profile_text, encoding="utf-8")
    print(f"[github] Saved profile -> {profile_file}")

    if readme_docs:
        readme_file = OUTPUT_DIR / f"{username}_readmes.md"
        readme_file.write_text("\n\n---\n\n".join(readme_docs), encoding="utf-8")
        print(f"[github] Saved READMEs -> {readme_file}")


def run():
    print("GitHub ingestor started")
    for user in PROFILES:
        try:
            ingest_profile(user)
        except Exception as exc:
            print(f"[github] Error for {user}: {exc}")
        time.sleep(1)

    print("DONE: GitHub data saved in RAG/knowledge/github/")


if __name__ == "__main__":
    run()