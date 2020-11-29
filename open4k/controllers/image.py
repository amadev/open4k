import base64
import kopf
import pykube
import yaml

from bravado_core import model
import os_sdk_light as osl

from open4k import utils
from open4k import kube

LOG = utils.get_logger(__name__)
kopf_on_args = ["open4k.amadev.ru", "v1alpha1", "images"]


class Image(pykube.objects.NamespacedAPIObject, kube.HelmBundleMixin):
    version = "open4k.amadev.ru/v1alpha1"
    endpoint = "images"
    kind = "Image"
    api = {'service': 'image', 'object': 'images', 'get': 'get', 'list': 'list', 'create': 'create', 'delete': 'delete'}


@kopf.on.create(*kopf_on_args)
@kopf.on.update(*kopf_on_args)
@kopf.on.resume(*kopf_on_args)
async def image_change_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got Image change event {name}")
    if body["spec"].get("managed") == False:
        LOG.info(f"{name} is not managed")
        return

    if body.get("status", {}).get("applied") == True:
        LOG.info(f"{name} exists")
        return

    clouds_obj = kube.find(pykube.Secret, "open4k", namespace=namespace)
    clouds = yaml.safe_load(
        base64.b64decode(clouds_obj.obj["data"]["clouds.yaml"]))
    client = osl.get_client(
        cloud=body["spec"]["cloud"],
        service="image",
        schema=osl.schema("image.yaml"),
        cloud_config=clouds,
    )
    obj = kube.find(Image, name, namespace=namespace)
    try:
        created = client.images.create(
            image=body["spec"]["body"]
        )
        if isinstance(created, model.Model):
            created = created.marshal()
        created = created[list(created)[0]]

    except Exception as e:
        obj.patch(
            {"status": {"applied": False, "error": str(e)}},
            subresource="status",
        )
        raise
    obj.patch(
        {"status": {"applied": True, "error": "", "object": created}},
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

    clouds_obj = kube.find(pykube.Secret, "open4k", namespace=namespace)
    clouds = yaml.safe_load(
        base64.b64decode(clouds_obj.obj["data"]["clouds.yaml"]))
    client = osl.get_client(
        cloud=body["spec"]["cloud"],
        service="image",
        schema=osl.schema("image.yaml"),
        cloud_config=clouds,
    )
    client.images.delete(image_id=obj_id)