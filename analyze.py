from os import listdir, path as os_path, walk as os_walk
from git import Repo
from datetime import datetime
from openpyxl import Workbook
import asyncio
from aiofiles import open as aio_open


async def analyze_repo(repo_path, excluded_file_types, start_date, end_date, authors):
    repo = Repo(repo_path)
    commits = list(repo.iter_commits("--all", since=start_date, until=end_date))

    author_lines = {}
    for commit in commits:
        if len(commit.parents) > 1:
            continue
        if not commit.parents:
            continue
        commit_date = datetime.fromtimestamp(commit.authored_date).strftime("%Y-%m-%d")
        author = commit.author.name
        if author not in authors:
            continue
        if commit_date not in author_lines:
            author_lines[commit_date] = {}
        if author not in author_lines[commit_date]:
            author_lines[commit_date][author] = 0

        files = commit.stats.files
        added_lines = 0
        for file in files:
            if not any(file.endswith(file_type) for file_type in excluded_file_types):
                diff = repo.git.diff(commit.parents[0], commit, "--", file).splitlines()
                added_lines += sum(
                    1
                    for line in diff
                    if line.startswith("+") and not line.startswith("+++")
                )
        author_lines[commit_date][author] += added_lines

    result = []
    for commit_date, authors in author_lines.items():
        for author, line_count in authors.items():
            result.append(
                [commit_date, repo_path, author, line_count, repo.active_branch.name]
            )
    return result


async def analyze_repositories(repositories, start_date, end_date, authors):
    wb = Workbook()
    ws = wb.active
    ws.append(["日期", "项目", "作者", "新增行数", "分支"])

    excluded_file_types = [
        ".txt",
        ".md",
        ".sql",
        ".csv",
        ".json",
        ".db",
        ".sqlite",
        ".xls",
        ".xlsx",
    ]

    tasks = [
        analyze_repo(repo, excluded_file_types, start_date, end_date, authors)
        for repo in repositories
    ]
    results = await asyncio.gather(*tasks)

    async with aio_open("new_code_line_statistics_by_day.xlsx", mode="wb") as f:
        async for result in results:
            for row in result:
                await f.write("\t".join(map(str, row)) + "\n")

    wb.save(filename="new_code_line_statistics_by_day.xlsx")


def find_git_repositories(person, parent_dir=None):
    if parent_dir is None:
        parent_dir = rf"D:\source\gitlab\{person}"
    repositories = []
    for dirpath, dirnames, file_ames in os_walk(parent_dir):
        if ".git" in dirnames:
            repositories.append(os_path.abspath(dirpath))
            break
    return repositories


if __name__ == "__main__":

    person = "xiupengrong"
    repositories = find_git_repositories(person)
    start_date = "2024-01-01"
    end_date = "2024-05-01"
    authors = [person]

    asyncio.run(analyze_repositories(repositories, start_date, end_date, authors))
