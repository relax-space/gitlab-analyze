import git
import openpyxl
from datetime import datetime
from multiprocessing import Pool, freeze_support
from os import listdir, path as os_path


# 遍历每个项目
def analyze_repository(args):
    repo_path, excluded_file_types, start_date, end_date, authors = args
    repo = git.Repo(repo_path)
    default_branch = repo.head.reference
    commits = list(repo.iter_commits(default_branch, since=start_date, until=end_date))

    author_lines = {}
    for commit in commits:
        if len(commit.parents) > 1:  # 忽略merge操作
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
        # 获取修改的文件列表
        files = commit.stats.files
        # 计算每次提交的新增行数，排除指定文件类型
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
            result.append([commit_date, repo_path, author, line_count])
    return result


def analyze_repositories(repositories, start_date, end_date, authors):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["日期", "项目", "作者", "新增行数"])

    # 定义需要排除的文件类型
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

    # 使用多进程进行并行处理
    pool = Pool(processes=8)  # 可以根据需要调整进程数
    args = [
        (repo, excluded_file_types, start_date, end_date, authors)
        for repo in repositories
    ]
    results = pool.map(
        analyze_repository,
        args,
    )

    for result in results:
        for row in result:
            ws.append(row)

    wb.save(f"{authors[0]}_new_code_line_statistics_by_day.xlsx")


if __name__ == "__main__":
    # 调用函数并传入项目路径、开始时间和结束时间
    # 调用函数并传入项目路径、开始时间和结束时间

    person = "xiupengrong"

    parent_dir = rf"D:\gitlab\{person}"
    repositories = []
    for i in listdir(parent_dir):
        repositories.append(os_path.join(parent_dir, i))
    start_date = "2024-01-01"
    end_date = "2025-05-01"
    authors = [person]
    freeze_support()
    analyze_repositories(repositories, start_date, end_date, authors)
