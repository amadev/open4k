import kopf
import pykube

from open4k import utils
from open4k import kube
from open4k import client
from open4k import settings
from open4k import hooks

LOG = utils.get_logger(__name__)
kopf_on_args = ["open4k.amadev.ru", "v1alpha1", "instances"]


class Instance(pykube.objects.NamespacedAPIObject, kube.HelmBundleMixin):
    version = "open4k.amadev.ru/v1alpha1"
    endpoint = "instances"
    kind = "Instance"
    api = {
        "service": "compute",
        "object": "server",
        "objects": "servers",
        "get_": "get_server",
        "list": "list_servers",
        "create": "create_server",
        "delete": "delete_server",
    }

    @staticmethod
    def get_os_obj(c, obj_id, id_name=None):
        if not id_name:
            id_name = "server_id"
        os_obj = getattr(getattr(c, "servers"), "get_server")(
            **{id_name: obj_id}
        )
        if {
            "service": "compute",
            "object": "server",
            "objects": "servers",
            "get_": "get_server",
            "list": "list_servers",
            "create": "create_server",
            "delete": "delete_server",
        }.get("object_envelope", True):
            os_obj = os_obj[list(os_obj)[0]]
        return os_obj

    def create_os_obj(c, body):
        os_obj = c.servers.create_server(server=body)
        if {
            "service": "compute",
            "object": "server",
            "objects": "servers",
            "get_": "get_server",
            "list": "list_servers",
            "create": "create_server",
            "delete": "delete_server",
        }.get("object_envelope", True):
            os_obj = os_obj[list(os_obj)[0]]
        return os_obj

    def delete_os_obj(c, obj_id):
        getattr(getattr(c, "servers"), "delete_server")(server_id=obj_id)


@kopf.on.create(*kopf_on_args)
@kopf.on.update(*kopf_on_args)
@kopf.on.resume(*kopf_on_args)
async def instance_change_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got Instance change event {name}")
    if body["spec"].get("managed") == False:
        LOG.info(f"{name} is not managed")
        return

    c = client.get_client(
        settings.OPEN4K_NAMESPACE, body["spec"]["cloud"], "compute"
    )
    obj = kube.find(Instance, name, namespace=namespace)

    klass = Instance

    if body.get("status", {}).get("applied") == True:
        LOG.info(f"{name} exists, updating ...")
        obj_id = body["status"]["object"].get("id")
        id_name = None
        if not obj_id:
            id_name = "uuid"
            obj_id = body["status"]["object"].get("uuid")
        os_obj = klass.get_os_obj(c, obj_id, id_name)
        obj.patch(
            {"status": {"object": os_obj}},
            subresource="status",
        )
        return

    try:
        os_obj = klass.create_os_obj(c, body["spec"]["body"])
    except Exception as e:
        obj.patch(
            {"status": {"applied": False, "error": str(e)}},
            subresource="status",
        )
        raise
    obj.patch(
        {"status": {"applied": True, "error": "", "object": os_obj}},
        subresource="status",
    )
    await hooks.call("instance", "post_create", c, klass, obj, os_obj)


@kopf.on.delete(*kopf_on_args)
async def instance_delete_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got Instance delete event {name}")
    if body["spec"].get("managed") == False:
        LOG.info(f"{name} is not managed")
        return

    if not body.get("status", {}).get("applied"):
        LOG.info(f"{name} was not applied successfully")
        return

    klass = Instance

    os_obj_id = body["status"].get("object", {}).get("id")
    if not os_obj_id:
        LOG.info(f"Cannot get id for {name}")
        return

    c = client.get_client(
        settings.OPEN4K_NAMESPACE, body["spec"]["cloud"], "compute"
    )
    klass.delete_os_obj(c, os_obj_id)
