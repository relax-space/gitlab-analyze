import os
import shutil
import git
from asyncio import Semaphore, create_task, gather, run as asyncio_run
from aiohttp import ClientSession, BasicAuth
from util import PERSONAL_ACCESS_TOKEN, LOCAL_PATH, GITLAB_BASE_URL, MAX_REQUESTS
from json import dump
from datetime import datetime


async def get_projects(url):
    headers = {"Private-Token": PERSONAL_ACCESS_TOKEN}

    async with ClientSession(auth=BasicAuth("user", PERSONAL_ACCESS_TOKEN)) as session:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            return data


async def clone_or_pull_project(i, project, start_date):
    project_name_one: str = project["path_with_namespace"]
    project_name = project_name_one.split("/")
    project_url = project["http_url_to_repo"]
    project_path = os.path.join(LOCAL_PATH, *project_name)
    updated_at = datetime.strptime(project["last_activity_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
    if updated_at >= datetime.strptime(start_date, "%Y-%m-%d"):
        if os.path.exists(project_path):
            try:
                repo = git.Repo(project_path)
                repo.remotes.origin.pull()

            except Exception as e:
                print(f"{i}.error {project_name}")
                return "-1"
            else:
                print(f"{i}.updated {project_name}")
        else:
            git.Repo.clone_from(project_url, project_path)
            print(f"{i}.cloned {project_name}")
        return project_name_one
    else:
        print(f"find it {project_name}")
        return "-2"


async def main(start_date):
    semaphore = Semaphore(MAX_REQUESTS)
    project_all_names = []
    page = 1
    has_next_page = True
    async with semaphore:
        while has_next_page:
            url = f"{GITLAB_BASE_URL}/projects?page={page}&per_page=10&order_by=last_activity_at&sort=desc"
            projects = await get_projects(url)
            project_names = [project["path_with_namespace"] for project in projects]
            project_all_names.append(project_names)
            print(f"项目总数(分页{page})： {len(projects)}个:{project_names}")
            tasks = []
            exp_set = set()
            if projects:
                for i, project in enumerate(projects):
                    exp_set.add(project["path_with_namespace"])
                    task = create_task(clone_or_pull_project(i, project, start_date))
                    tasks.append(task)

                result = await gather(*tasks)
                act_set = set(result)
                if exp_set != act_set:
                    err_set = exp_set - act_set
                    for i in err_set:
                        project_name = i.split("/")
                        project_url = project["http_url_to_repo"]
                        project_path = os.path.join(LOCAL_PATH, *project_name)
                        if os.path.isdir(project_path):
                            try:
                                shutil.rmtree(project_path)
                            except Exception as e:
                                print(f"{i}.error2 {project_name}")
                            else:
                                git.Repo.clone_from(project_url, project_path)
                                print(f"{i}.cloned {project_name}")

                if "-2" in act_set:
                    break
                pass
            else:
                has_next_page = False
            page += 1

    with open("projects.txt", mode="w", encoding="utf8") as f:
        dump(project_all_names, f)


if __name__ == "__main__":
    start_date = "2024-01-01"
    asyncio_run(main(start_date))
