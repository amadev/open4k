import asyncio

from open4k import utils
from open4k import client
from open4k import settings

LOG = utils.get_logger(__name__)


async def call(resource, hook_name, *args):
    func = utils.get_in(HOOKS, [resource, hook_name])
    if func:
        return await func(*args)


async def wait_instance_ready(api_config, cloud, obj, os_obj):
    obj.reload()
    c = client.get_client(settings.OPEN4K_NAMESPACE, cloud, "compute")
    while True:
        os_obj = getattr(
            getattr(c, api_config["objects"]), api_config["get_"]
        )(**{f'{api_config["object"]}_id': obj.obj["status"]["object"]["id"]})
        os_obj = os_obj[list(os_obj)[0]]
        print("!os_obj", os_obj)
        if os_obj["status"] == "ACTIVE":
            obj.patch(
                {"status": {"object": os_obj}},
                subresource="status",
            )
            break
        asyncio.sleep(1)
    from open4k import resource as rlib

    rlib.import_resources(cloud, "port", {"device_id": os_obj["id"]})
    return os_obj


HOOKS = {"instance": {"post_create": wait_instance_ready}}
