import asyncio
import subprocess

from open4k import utils

LOG = utils.get_logger(__name__)


async def call(resource, hook_name, *args):
    func = utils.get_in(HOOKS, [resource, hook_name])
    if func:
        return await func(*args)


async def wait_instance_ready(c, klass, obj, os_obj):
    obj.reload()
    while True:
        os_obj = klass.get_os_obj(c, obj.obj["status"]["object"]["id"])
        if os_obj["status"] == "ACTIVE":
            obj.patch(
                {"status": {"object": os_obj}},
                subresource="status",
            )
            break
        asyncio.sleep(1)

    from open4k import resource as rlib

    rlib.import_resources(
        obj.obj["spec"]["cloud"], "port", {"device_id": os_obj["id"]}
    )
    return os_obj


async def upload_image(c, klass, obj, os_obj):
    url = obj.obj["spec"]["url"]
    image_id = obj.obj["status"]["object"]["id"]
    cmd = f"wget {url} -O /tmp/{image_id}"
    cmd = cmd.split()
    subprocess.check_call(cmd)

    url = c.endpoint.rstrip("/") + f"/images/{image_id}/file"
    cmd = (
        f"curl -i -X PUT -H X-Auth-Token:{c.token} "
        f"-H Content-Type:application/octet-stream "
        f"-d @/tmp/{image_id} "
        f"{url}"
    )
    cmd = cmd.split()
    print("!!!", cmd)
    subprocess.check_call(cmd)


HOOKS = {
    "instance": {"post_create": wait_instance_ready},
    "image": {"post_create": upload_image},
}
