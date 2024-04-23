import os
import shutil
import git
from asyncio import Semaphore, create_task, gather, run as asyncio_run
from aiohttp import ClientSession, BasicAuth
from util import PERSONAL_ACCESS_TOKEN, LOCAL_PATH, GITLAB_BASE_URL, MAX_REQUESTS
from json import dump
from datetime import datetime

from requests import get as req_get


async def get_projects_by_member(member, update_date):
    headers = {"PRIVATE-TOKEN": PERSONAL_ACCESS_TOKEN}
    params = {"updated_after": update_date}
    url = f"{GITLAB_BASE_URL}/users/{member}/projects?page=1&per_page=100"
    async with ClientSession(auth=BasicAuth("user", PERSONAL_ACCESS_TOKEN)) as session:
        async with session.get(url, headers=headers, params=params) as response:
            data = await response.json()
            return data


def get_path_namespace(local_path, full_path):
    project_name = full_path.split("/")
    project_path = os.path.join(local_path, *project_name)
    return project_path


async def clone_or_pull_project(i, project_key, project):
    project_url = project["http_url_to_repo"]
    project_path = get_path_namespace(LOCAL_PATH, project_key)

    try:
        if os.path.exists(project_path):
            repo = git.Repo(project_path)
            repo.remotes.origin.pull()
            print(f"{i}.updated {project_key}")
        else:
            git.Repo.clone_from(project_url, project_path)
            print(f"{i}.cloned {project_key}")
    except Exception as e:
        print(f"{i}.error {project_key}")
        return "-1"

    return project_key


async def download_projects_by_members(members, start_date):
    semaphore = Semaphore(MAX_REQUESTS)
    page = 1
    has_next_page = True
    project_errs = []
    async with semaphore:
        for member in members:
            while has_next_page:
                projects = await get_projects_by_member(member, start_date)

                if projects:
                    tasks = []
                    exp_set = set()
                    for i, project in enumerate(projects):
                        project_key = project["path_with_namespace"]
                        exp_set.add(project_key)
                        task = create_task(
                            clone_or_pull_project(i, project_key, project)
                        )
                        tasks.append(task)
                    result = await gather(*tasks)
                    act_set = set(result)
                    project_errs.extend(list(exp_set - act_set))
                else:
                    has_next_page = False
                page += 1

    with open("project_errs.txt", mode="w", encoding="utf8") as f:
        dump(project_errs, f)
        print(f"需要手动确认的项目列表：{project_errs}")


if __name__ == "__main__":
    MEMBERS = [
        "xiupengrong",
        "yangyue",
        "mengbotian",
        "c981681700",
        "HKJ",
        "xln",
        "danghaitao",
    ]  # 人员列表
    start_date = "2024-01-01"
    asyncio_run(download_projects_by_members(MEMBERS, start_date))
