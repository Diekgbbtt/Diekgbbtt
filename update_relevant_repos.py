import os
import requests
import logging
from datetime import datetime, timezone

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


def fetch_repo_details(repo):
    """Fetch repository details including stars, forks, and last commit date."""
    try:
        logger.debug(f"Fetching repo details for {repo}...")
        url = f"https://api.github.com/repos/{repo}"
        repo_data = requests.get(url, headers=headers).json()
        
        stars = repo_data.get("stargazers_count", 0)
        forks = repo_data.get("forks_count", 0)
        
        # Get last commit date
        commits_url = f"https://api.github.com/repos/{repo}/commits?per_page=1"
        commits = requests.get(commits_url, headers=headers).json()
        
        last_commit_date = None
        if commits and len(commits) > 0:
            last_commit_date = commits[0]["commit"]["committer"]["date"]
        
        return stars, forks, last_commit_date
    except Exception as e:
        logger.error(f"Failed to fetch repo details for {repo}: {e}")
        return 0, 0, None


def calculate_time_gap(last_commit_date):
    """Calculate time gap from last commit in human-readable format."""
    if not last_commit_date:
        return "unknown"
    
    try:
        commit_date = datetime.fromisoformat(last_commit_date.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - commit_date
        
        if delta.days >= 31:
            months = delta.days // 31
            return f"/more {months} month{'s' if months > 1 else ''} ago"
        elif delta.days >= 7:
            weeks = delta.days // 7
            return f"/more {weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
    except Exception as e:
        logger.error(f"Failed to calculate time gap: {e}")
        return "unknown"


def craft_result_string(top5):
    """Format the top 5 repositories data into markdown string."""
    lines = []
    for repo, data in top5:
        # Extract just the project name from full_name (username/project -> project)
        project_name = repo.split('/')[-1]
        repo_url = f"https://github.com/{repo}"
        
        lines.append(f"- **[{project_name}]({repo_url})** :")
        lines.append(f"  - contributions")
        lines.append(f"     <span style='color:green'>+ {data['additions']} loc</span>")
        lines.append(f"     <span style='color:red'>- {data['deletions']} loc</span>")
        lines.append(f"  - {', '.join(data['languages']) if data['languages'] else 'N/A'}")
        lines.append(f"  - {data['time_gap']}")
        
        # Only add forks if > 0
        if data['forks'] > 0:
            lines.append(f"  - {data['forks']} forks")
        
        # Only add stars if > 0
        if data['stars'] > 0:
            lines.append(f"  - {data['stars']} stars")
    
    return "\n".join(lines)


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
            stars, forks, last_commit_date = fetch_repo_details(repo)
            repo_stats[repo] = {
                "additions": total_add,
                "deletions": total_del,
                "languages": fetch_languages(repo),
                "stars": stars,
                "forks": forks,
                "last_commit_date": last_commit_date,
                "time_gap": calculate_time_gap(last_commit_date)
            }

    # 3. Sort & top 5
    top5 = sorted(repo_stats.items(), key=lambda x: (x[1]["additions"] + x[1]["deletions"]), reverse=True)[:5]

    # 4. Format output
    result = craft_result_string(top5)
    update_readme(result, "loc")


if __name__ == "__main__":
    main()
