from os import path as os_path
import git
from asyncio import Semaphore, create_task, gather, run as asyncio_run
from aiohttp import ClientSession, BasicAuth
from util import PERSONAL_ACCESS_TOKEN, LOCAL_PATH, GITLAB_BASE_URL, MAX_REQUESTS
from json import dump, load as json_load
from datetime import datetime


async def get_projects(url, session, semaphore):
    headers = {"Private-Token": PERSONAL_ACCESS_TOKEN}
    try:
        async with semaphore:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                return data
    except Exception as e:
        print(url, e)
        return None
        pass


def get_path_namespace(local_path, username, full_path):
    project_name = full_path.split("/")
    project_path = os_path.join(local_path, username, *project_name)
    return project_path


async def clone_or_pull_project(username, project, start_date):
    project_name: str = project["path_with_namespace"]
    project_url = project["http_url_to_repo"]
    project_path = get_path_namespace(LOCAL_PATH, username, project_name)
    updated_at = datetime.strptime(project["last_activity_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
    if updated_at >= datetime.strptime(start_date, "%Y-%m-%d"):
        if os_path.exists(project_path):
            try:
                repo = git.Repo(project_path)
                repo.remotes.origin.pull()
            except Exception as e:
                print(f"error {project_name}")
                return "-1"
            else:
                print(f"updated {project_name}")
        else:
            git.Repo.clone_from(project_url, project_path)
            print(f"cloned {project_name}")
        return project_name
    else:
        return "-1"


def get_project_names(file_name):
    with open(file_name, mode="r", encoding="utf8") as f:
        resp = json_load(f)
        return resp


async def main(start_date, file_name):
    semaphore = Semaphore(MAX_REQUESTS)
    project_all_names = []
    dic_project: dict = get_project_names(file_name)
    # http://10.0.50.12:8088/api/v4/projects?simple=true&search_namespaces=true&search=bsn-ddc/ddchashrate/ddc-hashrate-web
    async with ClientSession(auth=BasicAuth("user", PERSONAL_ACCESS_TOKEN)) as session:
        for k, v in dic_project.items():
            projects = v
            tasks = []
            for pj in projects:
                url = f"{GITLAB_BASE_URL}/projects?simple=true&search_namespaces=true&search={pj}"
                task = create_task(get_projects(url, session, semaphore))
                tasks.append(task)
            resp_projects = await gather(*tasks)
            tasks = []
            exp_set = set()
            if resp_projects:
                for i, project in enumerate(resp_projects):
                    exp_set.add(project["path_with_namespace"])
                    task = create_task(clone_or_pull_project(k, project, start_date))
                    tasks.append(task)

                result = await gather(*tasks)
                act_set = set(result)
                if exp_set != act_set:
                    print(f"{k} 以下项目需要手动下载：{exp_set-act_set}")
                pass

    with open("projects.txt", mode="w", encoding="utf8") as f:
        dump(project_all_names, f)


if __name__ == "__main__":
    start_date = "2024-01-01"
    file_name = "raw20240425.json"
    asyncio_run(main(start_date, file_name))
