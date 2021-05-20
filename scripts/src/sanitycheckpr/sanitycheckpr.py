import re
import os
import sys
import argparse

import requests
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


ALLOW_CI_CHANGES = "allow/ci-changes"

def ensure_only_chart_is_modified(api_url, repository, branch):
    # api_url https://api.github.com/repos/<organization-name>/<repository-name>/pulls/1
    headers = {'Accept': 'application/vnd.github.v3+json'}
    r = requests.get(api_url, headers=headers)
    for label in r.json()["labels"]:
        if label["name"] == ALLOW_CI_CHANGES:
            return
    files_api_url = f'{api_url}/files'
    headers = {'Accept': 'application/vnd.github.v3+json'}
    r = requests.get(files_api_url, headers=headers)
    pattern = re.compile(r"charts/(\w+)/([\w-]+)/([\w-]+)/(.+)/.*")
    reportpattern = re.compile(r"charts/(\w+)/([\w-]+)/([\w-]+)/([\w\.]+)/report.yaml")
    count = 0
    for f in r.json():
        match = pattern.match(f["filename"])
        if not match:
            print("PR should only modify chart related files")
            sys.exit(1)
        elif match:
            category, organization, chart, version = match.groups()
            print("Downloading index.yaml")
            r = requests.get(f'https://raw.githubusercontent.com/{repository}/{branch}/index.yaml')
            if r.status_code == 200:
                data = yaml.load(r.text, Loader=Loader)
            else:
                data = {"apiVersion": "v1",
                    "entries": {}}

            crtentries = []
            entry_name = f"{organization}-{chart}"
            d = data["entries"].get(entry_name, [])
            for v in d:
                if v["version"] == version:
                    print("[ERROR] Helm chart release already exists:", version)
                    sys.exit(1)
        elif reportpattern.match(f["filename"]):
            print("[INFO] Report found")
            print("::set-output name=report-exists::true")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--index-branch", dest="branch", type=str, required=True,
                                        help="index branch")
    parser.add_argument("-r", "--repository", dest="repository", type=str, required=True,
                                        help="Git Repository")
    parser.add_argument("-u", "--api-url", dest="api_url", type=str, required=True,
                                        help="API URL for the pull request")
    args = parser.parse_args()
    branch = args.branch.split("/")[-1]
    ensure_only_chart_is_modified(args.api_url, args.repository, branch)


if __name__ == "__main__":
    main()
