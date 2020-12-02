import kopf
import pykube

from open4k import utils
from open4k import kube
from open4k import client
from open4k import settings
from open4k import hooks

LOG = utils.get_logger(__name__)
kopf_on_args = ["open4k.amadev.ru", "v1alpha1", "ports"]


class Port(pykube.objects.NamespacedAPIObject, kube.HelmBundleMixin):
    version = "open4k.amadev.ru/v1alpha1"
    endpoint = "ports"
    kind = "Port"
    api = {
        "service": "network",
        "object": "port",
        "objects": "ports",
        "get_": "get_port",
        "list": "list_ports",
        "create": "create_port",
        "delete": "delete_port",
    }

    @staticmethod
    def get_os_obj(c, obj_id):
        os_obj = getattr(getattr(c, "ports"), "get_port")(
            **{"port_id": obj_id}
        )
        if {
            "service": "network",
            "object": "port",
            "objects": "ports",
            "get_": "get_port",
            "list": "list_ports",
            "create": "create_port",
            "delete": "delete_port",
        }.get("object_envelope", True):
            os_obj = os_obj[list(os_obj)[0]]
        return os_obj

    def create_os_obj(c, body):
        os_obj = c.ports.create_port(port=body)
        if {
            "service": "network",
            "object": "port",
            "objects": "ports",
            "get_": "get_port",
            "list": "list_ports",
            "create": "create_port",
            "delete": "delete_port",
        }.get("object_envelope", True):
            os_obj = os_obj[list(os_obj)[0]]
        return os_obj

    def delete_os_obj(c, obj_id):
        getattr(getattr(c, "ports"), "delete_port")(port_id=obj_id)


@kopf.on.create(*kopf_on_args)
@kopf.on.update(*kopf_on_args)
@kopf.on.resume(*kopf_on_args)
async def port_change_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got Port change event {name}")
    if body["spec"].get("managed") == False:
        LOG.info(f"{name} is not managed")
        return

    c = client.get_client(
        settings.OPEN4K_NAMESPACE, body["spec"]["cloud"], "network"
    )
    obj = kube.find(Port, name, namespace=namespace)

    klass = Port

    if body.get("status", {}).get("applied") == True:
        LOG.info(f"{name} exists, updating ...")
        os_obj = klass.get_os_obj(c, body["status"]["object"]["id"])
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
    await hooks.call("port", "post_create", c, klass, obj, os_obj)


@kopf.on.delete(*kopf_on_args)
async def port_delete_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got Port delete event {name}")
    if body["spec"].get("managed") == False:
        LOG.info(f"{name} is not managed")
        return

    if not body.get("status", {}).get("applied"):
        LOG.info(f"{name} was not applied successfully")
        return

    klass = Port

    os_obj_id = body["status"].get("object", {}).get("id")
    if not os_obj_id:
        LOG.info(f"Cannot get id for {name}")
        return

    c = client.get_client(
        settings.OPEN4K_NAMESPACE, body["spec"]["cloud"], "network"
    )
    klass.delete_os_obj(c, os_obj_id)
