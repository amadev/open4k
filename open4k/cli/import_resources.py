import sys
import json

from open4k import client
from open4k import settings
from open4k.controllers import RESOURCES
from open4k import resource as rlib


def parse_args(args):
    i = 0
    n = len(args)
    resources = []
    filters = {}
    while i < n:
        arg = args[i]
        if arg.startswith("--filter-"):
            if i == (n - 1):
                print(f"No option value for {arg}")
                raise ValueError("Option is not specified")
            try:
                data = json.loads(args[i + 1])
                for k, v in data.items():
                    pass
            except Exception as e:
                print(f"Cannot parse filter {arg}: {e}")
                raise
            filters[arg.replace("--filter-", "")] = data
            i += 2
            continue
        resources.append(arg)
        i += 1
    return (resources, filters)


def main():
    resources = RESOURCES.keys()
    filters = {}
    if len(sys.argv) > 1:
        try:
            resources, filters = parse_args(sys.argv[1:])
        except Exception as e:
            print(f"unable to parse arguments {e}")
            return 1
    if "-h" in resources:
        print(
            "example usage: import_resources "
            'image --filter-image \'{"name": "in:cirros-0.4.0"}\' '
            'instance --filter-instance \'{"description": "test-instances"}\''
        )
        return 0

    dry_run = False
    if "--dry-run" in resources:
        resources.remove("--dry-run")
        dry_run = True

    unknown = set(resources) - set(RESOURCES.keys())
    if unknown:
        print(f"Unknown resources {unknown}")
        return 1
    for cloud in client.get_clouds(settings.OPEN4K_NAMESPACE)["clouds"]:
        for resource in resources:
            rlib.import_resources(
                cloud, resource, filters.get(resource), dry_run
            )


if __name__ == "__main__":
    main()
