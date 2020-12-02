import sys

from open4k import client
from open4k import settings
from open4k.controllers import RESOURCES
from open4k import resource as rlib


def main():
    resources = RESOURCES.keys()
    if len(sys.argv) > 1:
        resources = sys.argv[1:]
    for cloud in client.get_clouds(settings.OPEN4K_NAMESPACE)["clouds"]:
        for resource in resources:
            rlib.import_resources(cloud, resource)


if __name__ == "__main__":
    main()
