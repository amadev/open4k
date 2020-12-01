import kopf
import pykube

from bravado_core import model

from open4k import utils
from open4k import kube
from open4k import client
from open4k import settings

LOG = utils.get_logger(__name__)
kopf_on_args = ["open4k.amadev.ru", "v1alpha1", "images"]


class Image(pykube.objects.NamespacedAPIObject, kube.HelmBundleMixin):
    version = "open4k.amadev.ru/v1alpha1"
    endpoint = "images"
    kind = "Image"
    api = {
        "service": "image",
        "objects": "images",
        "object": "image",
        "get_": "get",
        "list": "list",
        "create": "create",
        "delete": "delete",
    }


@kopf.on.create(*kopf_on_args)
@kopf.on.update(*kopf_on_args)
@kopf.on.resume(*kopf_on_args)
async def image_change_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got Image change event {name}")
    if body["spec"].get("managed") == False:
        LOG.info(f"{name} is not managed")
        return

    c = client.get_client(
        settings.OPEN4K_NAMESPACE, body["spec"]["cloud"], "image"
    )
    obj = kube.find(Image, name, namespace=namespace)

    if body.get("status", {}).get("applied") == True:
        LOG.info(f"{name} exists, updating ...")
        os_obj = getattr(getattr(c, "images"), "get")(
            **{"image_id": body["status"]["object"]["id"]}
        )
        if isinstance(os_obj, model.Model):
            os_obj = os_obj.marshal()
        obj.patch(
            {"status": {"object": os_obj}},
            subresource="status",
        )
        return

    try:
        os_obj = c.images.create(image=body["spec"]["body"])
        if isinstance(os_obj, model.Model):
            os_obj = os_obj.marshal()
        os_obj = os_obj[list(os_obj)[0]]

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


@kopf.on.delete(*kopf_on_args)
async def image_delete_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got Image delete event {name}")
    if body["spec"].get("managed") == False:
        LOG.info(f"{name} is not managed")
        return

    if not body.get("status", {}).get("applied"):
        LOG.info(f"{name} was not applied successfully")
        return

    obj_id = body["status"].get("object", {}).get("id")
    if not obj_id:
        LOG.info(f"Cannot get id for {name}")
        return

    c = client.get_client(
        settings.OPEN4K_NAMESPACE, body["spec"]["cloud"], "image"
    )
    getattr(getattr(c, "images"), "delete")(image_id=obj_id)
