import kopf
import pykube

from open4k import utils
from open4k import kube
from open4k import client
from open4k import settings
from open4k import hooks

LOG = utils.get_logger(__name__)
kopf_on_args = ["open4k.amadev.ru", "v1alpha1", "flavors"]


class Flavor(pykube.objects.NamespacedAPIObject, kube.HelmBundleMixin):
    version = "open4k.amadev.ru/v1alpha1"
    endpoint = "flavors"
    kind = "Flavor"
    api = {
        "service": "compute",
        "objects": "flavors",
        "object": "flavor",
        "get_": "get_flavor",
        "list": "list_flavors",
        "create": "create_flavor",
        "delete": "delete_flavor",
    }

    @staticmethod
    def get_os_obj(c, obj_id):
        os_obj = getattr(getattr(c, "flavors"), "get_flavor")(
            **{"flavor_id": obj_id}
        )
        if {
            "service": "compute",
            "objects": "flavors",
            "object": "flavor",
            "get_": "get_flavor",
            "list": "list_flavors",
            "create": "create_flavor",
            "delete": "delete_flavor",
        }.get("object_envelope", True):
            os_obj = os_obj[list(os_obj)[0]]
        return os_obj

    def create_os_obj(c, body):
        os_obj = c.flavors.create_flavor(flavor=body)
        if {
            "service": "compute",
            "objects": "flavors",
            "object": "flavor",
            "get_": "get_flavor",
            "list": "list_flavors",
            "create": "create_flavor",
            "delete": "delete_flavor",
        }.get("object_envelope", True):
            os_obj = os_obj[list(os_obj)[0]]
        return os_obj

    def delete_os_obj(c, obj_id):
        getattr(getattr(c, "flavors"), "delete_flavor")(flavor_id=obj_id)


@kopf.on.create(*kopf_on_args)
@kopf.on.update(*kopf_on_args)
@kopf.on.resume(*kopf_on_args)
async def flavor_change_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got Flavor change event {name}")
    if body["spec"].get("managed") == False:
        LOG.info(f"{name} is not managed")
        return

    c = client.get_client(
        settings.OPEN4K_NAMESPACE, body["spec"]["cloud"], "compute"
    )
    obj = kube.find(Flavor, name, namespace=namespace)

    klass = Flavor

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
    await hooks.call("flavor", "post_create", c, klass, obj, os_obj)


@kopf.on.delete(*kopf_on_args)
async def flavor_delete_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got Flavor delete event {name}")
    if body["spec"].get("managed") == False:
        LOG.info(f"{name} is not managed")
        return

    if not body.get("status", {}).get("applied"):
        LOG.info(f"{name} was not applied successfully")
        return

    klass = Flavor

    os_obj_id = body["status"].get("object", {}).get("id")
    if not os_obj_id:
        LOG.info(f"Cannot get id for {name}")
        return

    c = client.get_client(
        settings.OPEN4K_NAMESPACE, body["spec"]["cloud"], "compute"
    )
    klass.delete_os_obj(c, os_obj_id)
