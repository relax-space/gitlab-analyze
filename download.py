import os
import git
from asyncio import Semaphore, create_task, gather, run as asyncio_run
from aiohttp import ClientSession, BasicAuth
from util import PERSONAL_ACCESS_TOKEN, LOCAL_PATH, GITLAB_BASE_URL, MAX_REQUESTS


async def get_projects(url):
    headers = {"Private-Token": PERSONAL_ACCESS_TOKEN}

    async with ClientSession(auth=BasicAuth("user", PERSONAL_ACCESS_TOKEN)) as session:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            return data


async def clone_or_pull_project(i, project):
    project_name = project["path"]
    project_url = project["http_url_to_repo"]
    project_path = os.path.join(LOCAL_PATH, project_name)

    if os.path.exists(project_path):
        repo = git.Repo(project_path)
        repo.remotes.origin.pull()
        print(f"{i}.{project_name} updated.")
    else:
        git.Repo.clone_from(project_url, project_path)
        print(f"{i}.{project_name} cloned.")


async def main():
    semaphore = Semaphore(MAX_REQUESTS)
    page = 1
    has_next_page = True
    while has_next_page:
        url = f"{GITLAB_BASE_URL}/projects?page={page}&per_page=100"
        projects = await get_projects(url)
        project_names = [project["path"] for project in projects]
        print(f"项目总数(分页{page})： {len(projects)}个:{project_names}")

        if projects:
            async with semaphore:
                await gather(
                    *(
                        clone_or_pull_project(i, project)
                        for i, project in enumerate(projects)
                    )
                )
            pass
        else:
            has_next_page = False
        page += 1


if __name__ == "__main__":
    asyncio_run(main())
