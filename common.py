import sys
import requests
import json
import datetime
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import settings


# get repository list from github
def get_github_repos(org, prefix=None, verbose=False):
    all_repos_list = []
    page_number = 1
    request_headers = {
        "User-Agent": "GitHubCloneAll/1.0",
        "Authorization": "token " + settings.github_token,
    }
    while True:
        if verbose:
            sys.stdout.write('.')
            sys.stdout.flush()
        repos_page = requests.get("https://api.github.com/orgs/{}/repos?page={}".format(org, page_number), headers = request_headers) 
        page_number = page_number + 1
        if repos_page.status_code != 200:
            raise Exception("Failed to load repos from GitHub: " + repos_page.content)
            # exit(1)
        repos_page_json = repos_page.json()
        if len(repos_page_json) == 0:
            # print(" Done.")
            break
        all_repos_list = all_repos_list + repos_page.json()
    if verbose:
        sys.stdout.write('\n')
    if prefix is not None:
        filtered_repo_list = [x for x in all_repos_list if x['name'].startswith(prefix)]
        return filtered_repo_list
    else:
        return all_repos_list
    # for repo in all_repos_list:
    #     print(repo['name'])
    # print( "%d of %d repos start with %s" % (len(filteredRepoList), len(allReposList), githubPrefix))


# get a set of github repository names with a given prefix
def get_github_repo_names(org, prefix=None):
    repos = get_github_repos(org, prefix)
    return set([x['full_name'] for x in repos])
    


# get projects list from AppVeyor
def get_appveyor_project_repo_names():
    headers = {
        "User-Agent": "AppVeyorAddRepo/1.0",
        "Authorization": "Bearer " + settings.appveyor_token,
    }
    res = requests.get('https://ci.appveyor.com/api/account/{}/projects'.format(settings.appveyor_account), headers = headers) 
    if res.status_code != 200:
        raise Exception("AppVeyor API reported and error when fetching project list! Message is '{}' ({}).".format(res.reason, res.status_code))
        # exit(1)
    response_json = json.loads(res.text)
    project_repository_names = {}
    for project in response_json:
        # project_repository_names.add(project['repositoryName'])
        project_repository_names[project['repositoryName']] = project['slug']
    return project_repository_names


# add a new appveyor project
# - repo: repository name of the new appveyor project
def add_appveyor_project(repo):
    headers = {
        "User-Agent": "AppVeyorAddRepo/1.0",
        "Authorization": "Bearer " + settings.appveyor_token,
    }
    add_project_request = {
        "repositoryProvider": "gitHub",
        "repositoryName": repo,
    }
    res = requests.post('https://ci.appveyor.com/api/account/{}/projects'.format(settings.appveyor_account), data=add_project_request, headers=headers)
    if res.status_code != 200:
        raise Exception("AppVeyor API reported an error while trying to add a new project '{}'! Message is '{}' ({}).".format(repo, res.reason, res.status_code))
        # raise Exception("Appveyor API error!")
    return res.content


# trigger a new build of repo's specified branch
def trigger_appveyor_build(slug, branch="master"):
    headers = {
        "User-Agent": "AppVeyorBuildRepo/1.0",
        "Authorization": "Bearer " + settings.appveyor_token,
    }
    build_project_request = {
        "accountName": settings.appveyor_account,
        # "repositoryProvider": "gitHub",
        "projectSlug": slug,
        "branch": branch,
    }
    res = requests.post('https://ci.appveyor.com/api/account/{}/builds'.format(settings.appveyor_account), data=build_project_request, headers=headers)
    if res.status_code != 200:
        raise Exception("AppVeyor API reported an error while trying to build branch '{}' of project '{}'! Message is '{}' ({}).".format(branch, slug, res.reason, res.status_code))
        # exit(1)
    return res.content


# add repositories to appveyor if they are not already added
def add_appveyor_projects_safely(repo_list, trigger_build=False):
    existing_projects_repos = get_appveyor_project_repo_names()
    new_projects = {}
    for repo in repo_list:
        if repo not in existing_projects_repos:
            res = add_appveyor_project(repo)
            slug = json.loads(res)['slug']
            new_projects[repo] = slug
            if trigger_build:
                trigger_appveyor_build(slug)
    return new_projects


# get a token for Travis API v 2.1 using an existing GitHub token
def get_travis_token(private=True):
    api_url = "https://api.travis-ci.{}/auth/github"
    travis_token_request = {
        "github_token": settings.github_token
    }
    res = requests.post(
        api_url.format("com" if private else "org"),
        data=travis_token_request
    )
    if res.status_code != 200:
        raise Exception("Travis API reported an error while trying to get a {} API token using GitHub token authentication! Message is '{}' ({}).".format("private" if private else "public", res.reason, res.status_code))
    return json.loads(res.content).get("access_token")


#
def get_github_check_runs(repo):
    check_runs_headers = {
        "User-Agent": "GitHubCheckRuns/1.0",
        "Authorization": "token " + settings.github_token,
        "Accept": "application/vnd.github.antiope-preview+json",
    }
    res = requests.get(
        "https://api.github.com/repos/{}/commits/master/check-runs".format(repo), 
        headers=check_runs_headers
    )
    if res.status_code != 200:
        raise Exception("GitHub API reported an error while trying to get check run info for repository '{}'! Message is '{}' ({}).".format(repo, res.reason, res.status_code))
    return json.loads(res.content).get("check_runs")


#
def get_successfull_build_info(repo):
    check_runs = get_github_check_runs(repo)
    # travis_build = None
    # completion_time = None
    for check_run in check_runs:
        if (
            "Travis CI" in check_run.get("name") 
            and check_run.get("conclusion") == "success"
        ):
            # travis_build = check_run.get("external_id")
            # completion_time = check_run.get("completed_at")
            return check_run
    # if not travis_build:
    return {}
    # return 


#
def get_travis_log(repo):
    # check_runs_headers = {
    #     "User-Agent": "GitHubCheckRuns/1.0",
    #     "Authorization": "token " + settings.github_token,
    # }
    # res = requests.get(
    #     "https://api.github.com/repos/{}/commits/master/check-runs".format(repo),
    #     headers=check_runs_headers
    # )
    # if res.status_code != 200:
    #     raise Exception("GitHub API reported an error while trying to get check run info for repository '{}'! Message is '{}' ({}).".format(repo, res.reason, res.status_code))
    # check_runs = json.loads(res.content).get("check_runs", [])
    # check_runs = get_github_check_runs(repo)
    # travis_build = None
    # completion_time = None
    # for check_run in check_runs:
    #     if (
    #         "Travis CI" in check_run.get("name")
    #         and check_run.get("conclusion") == "success"
    #     ):
    #         travis_build = check_run.get("external_id")
    #         completion_time = check_run.get("completed_at")
    #         break
    travis_build = get_successfull_build_info(repo).get("external_id")
    if not travis_build:
        return None
    # 
    # travis_token = get_travis_token()
    # 
    travis_headers = {
        "Travis-API-Version": "3",
        "User-Agent": "API Explorer",
        "Authorization": "token " + settings.travis_token,
    }
    res = requests.get(
        "https://api.travis-ci.com/build/{}".format(travis_build), 
        headers=travis_headers
    )
    if res.status_code != 200:
        raise Exception("Travis API reported an error while trying to get build info for build {} (repository '{}')! Message is '{}' ({}).".format(travis_build, repo, res.reason, res.status_code))
    job_id = json.loads(res.content).get("jobs", [{}])[-1].get("id")
    if job_id is None:
        raise Exception("No valid job ID found for build {} (repository '{}').".format(travis_build, repo))
    res = requests.get(
        "https://api.travis-ci.com/job/{}/log".format(job_id), 
        headers=travis_headers
    )
    if res.status_code != 200:
        raise Exception("Travis API reported an error while trying to get build log for job {} (build {} for repository '{}')! Message is '{}' ({}).".format(job_id, travis_build, repo, res.reason, res.status_code))
    return json.loads(res.content).get("content")


#
def get_successfull_status_info(repo):
    status_headers = {
        "User-Agent": "GitHubCheckRuns/1.0",
        "Authorization": "token " + settings.github_token,
        "Accept": "application/vnd.github.antiope-preview+json",
    }
    res = requests.get(
        "https://api.github.com/repos/{}/commits/master/status".format(repo), 
        headers=status_headers
    )
    if res.status_code != 200:
        raise Exception("GitHub API reported an error while trying to get status info for repository '{}'! Message is '{}' ({}).".format(repo, res.reason, res.status_code))
    status = json.loads(res.content)
    if status["state"] != "success":
        return {}
    for st in status["statuses"]:
        if st["state"] == "success" and "AppVeyor" in st["description"]:
            return st
    return {}


#
def get_task1_id(log):
    i = log.find("Solution for task")
    if i < 0:
        return None
    i += len("Solution for task") + 1
    return int(log[i:i+2].strip())


#
def get_task2_id(log):
    i = log.find("Task")
    if i < 0:
        return None
    i += len("Task") + 1
    return int(log[i:i+2].strip())


#
def gsheet(solutions, debug=False):
    #
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(settings.gsheet_key_filename, scope)
    conn = gspread.authorize(creds)
    #
    for sol in solutions:
        group_name = sol[0].strip()
        stud_name = sol[1].lower().strip()
        repo = sol[2].strip()
        lab_id = int(repo.split('os-task')[1].split('-')[0])
        try:
            worksheet = conn.open(settings.gspreadsheet_name).worksheet(group_name)
        except:
            raise Exception("No group {}: {}".format(group_name, sol))
        names_list = [x.lower() for x in worksheet.col_values(2)[2:]]
        if stud_name in names_list:
            stud_row = names_list.index(stud_name) + 3
        else:
            raise Exception("No student {}: {}".format(stud_name, sol))
        if lab_id == 2:
            completion_date = get_successfull_build_info(repo).get("completed_at")
            is_empty = worksheet.cell(stud_row, 4+1).value.strip() == ''
        elif lab_id == 3:
            completion_date = get_successfull_status_info(repo).get("updated_at")
            is_empty = worksheet.cell(stud_row, 7+1).value.strip() == ''
        else:
            completion_date = None
            is_empty = False
        if debug:
            print("{}: {}, {}".format(sol, completion_date, is_empty))
        if completion_date and is_empty:
            worksheet.update_cell(stud_row, 4+(lab_id-2)*3, repo)
            worksheet.update_cell(stud_row, 4+(lab_id-2)*3+1, datetime.datetime.strptime(completion_date, '%Y-%m-%dT%H:%M:%SZ').date().isoformat())
    
