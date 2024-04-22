import os
import git
from asyncio import Semaphore, create_task, gather, run as asyncio_run
from aiohttp import ClientSession, BasicAuth
from util import PERSONAL_ACCESS_TOKEN, LOCAL_PATH, GITLAB_BASE_URL


async def get_all_projects():
    headers = {"Private-Token": PERSONAL_ACCESS_TOKEN}
    async with ClientSession(auth=BasicAuth("user", PERSONAL_ACCESS_TOKEN)) as session:
        async with session.get(
            f"{GITLAB_BASE_URL}/projects", headers=headers
        ) as response:
            return await response.json()


async def clone_or_pull_project(i, project):
    project_name = project["name"]
    project_url = project["http_url_to_repo"]
    project_path = os.path.join(LOCAL_PATH, project_name)

    if os.path.exists(project_path):
        repo = git.Repo(project_path)
        repo.remotes.origin.pull()
        print(f"{i}.Project {project_name} updated.")
    else:
        git.Repo.clone_from(project_url, project_path)
        print(f"{i}.Project {project_name} cloned.")


async def main():
    projects = await get_all_projects()
    tasks = []

    print(f"项目总数： {len(projects)}个")
    # projects = [projects[0]]

    semaphore = Semaphore(5)

    async with semaphore:
        for i, project in enumerate(projects):
            task = create_task(clone_or_pull_project(i, project))
            tasks.append(task)

        await gather(*tasks)


if __name__ == "__main__":
    asyncio_run(main())
