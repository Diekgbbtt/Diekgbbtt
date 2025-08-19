import os
import requests
import logging

# --- Setup ---
USER = os.environ["GH_USER"]
TOKEN = os.environ["GH_TOKEN"]
headers = {"Authorization": f"Bearer {TOKEN}"}

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def fetch_repositories(user):
    """Fetch all repositories owned by the user."""
    try:
        logger.debug("Fetching repositories...")
        url = f"https://api.github.com/users/{user}/repos?per_page=100"
        repos = requests.get(url, headers=headers).json()
        return [repo["full_name"] for repo in repos if "full_name" in repo]
    except Exception as e:
        logger.error(f"Failed to fetch repositories: {e}")
        return []


def fetch_commits(repo, user):
    """Fetch commits authored by the user in a repo."""
    try:
        logger.debug(f"Fetching commits for {repo}...")
        url = f"https://api.github.com/repos/{repo}/commits?author={user}&per_page=100"
        commits = requests.get(url, headers=headers).json()
        return [c["sha"] for c in commits if "sha" in c]
    except Exception as e:
        logger.error(f"Failed to fetch commits for {repo}: {e}")
        return []


def fetch_commit_stats(repo, sha):
    """Fetch additions and deletions for a commit."""
    try:
        url = f"https://api.github.com/repos/{repo}/commits/{sha}"
        stats = requests.get(url, headers=headers).json().get("stats", {})
        return stats.get("additions", 0), stats.get("deletions", 0)
    except Exception as e:
        logger.error(f"Failed to fetch stats for {repo}@{sha}: {e}")
        return 0, 0


def fetch_languages(repo):
    """Fetch programming languages used in the repo."""
    try:
        url = f"https://api.github.com/repos/{repo}/languages"
        langs = requests.get(url, headers=headers).json()
        return list(langs.keys())
    except Exception as e:
        logger.error(f"Failed to fetch languages for {repo}: {e}")
        return []


def update_readme(content, marker="loc"):
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            readme = f.read()

        start_tag = f"<!-- {marker} starts -->"
        end_tag = f"<!-- {marker} ends -->"

        new_section = f"{start_tag}\n{content}\n{end_tag}"

        if start_tag in readme and end_tag in readme:
            updated = readme.split(start_tag)[0] + new_section + readme.split(end_tag)[1]
        else:
            # markers not found, just append at the end
            updated = readme + "\n\n" + new_section

        with open("README.md", "w", encoding="utf-8") as f:
            f.write(updated)

        logger.debug("README.md updated successfully.")

    except Exception as e:
        logger.error(f"Failed to update README.md: {e}")


if __name__ == "__main__":
    content = main()   # returns string
    update_readme(content, marker="loc")



def main():
    repo_stats = {}

    # 1. Repos
    repos = fetch_repositories(USER)

    # 2. Commits and LOC
    for repo in repos:
        total_add, total_del = 0, 0
        commits = fetch_commits(repo, USER)

        for sha in commits:
            add, dele = fetch_commit_stats(repo, sha)
            total_add += add
            total_del += dele

        if total_add + total_del > 0:
            repo_stats[repo] = {
                "additions": total_add,
                "deletions": total_del,
                "languages": fetch_languages(repo),
                "tags": ["contribution"]  # placeholder, can enrich later
            }

    # 3. Sort & top 5
    top5 = sorted(repo_stats.items(), key=lambda x: (x[1]["additions"] + x[1]["deletions"]), reverse=True)[:5]

    # 4. Format output
    lines = ["# Most Relevant Projects\n"]
    for repo, data in top5:
        lines.append(f"- **{repo}** : contribution :")
        lines.append(f"    - {data['additions']} additions | {data['deletions']} deletions")
        lines.append(f"    - {', '.join(data['languages']) if data['languages'] else 'N/A'}")
        lines.append(f"    - {', '.join(data['tags'])}")

    result = "\n".join(lines)
    update_readme(results, "loc")


if __name__ == "__main__":
    main()
