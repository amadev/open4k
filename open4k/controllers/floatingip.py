import base64
import kopf
import pykube
import yaml

from bravado_core import model
import os_sdk_light as osl

from open4k import utils
from open4k import kube
from open4k import client
from open4k import settings

LOG = utils.get_logger(__name__)
kopf_on_args = ["open4k.amadev.ru", "v1alpha1", "floatingips"]


class FloatingIP(pykube.objects.NamespacedAPIObject, kube.HelmBundleMixin):
    version = "open4k.amadev.ru/v1alpha1"
    endpoint = "floatingips"
    kind = "FloatingIP"
    api = {'service': 'network', 'objects': 'floatingips', 'object': 'floatingip', 'get_': 'get_floatingips', 'list': 'list_floatingips', 'create': 'create_floatingip', 'delete': 'delete_floatingip'}


@kopf.on.create(*kopf_on_args)
@kopf.on.update(*kopf_on_args)
@kopf.on.resume(*kopf_on_args)
async def floatingip_change_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got FloatingIP change event {name}")
    if body["spec"].get("managed") == False:
        LOG.info(f"{name} is not managed")
        return

    c = client.get_client(
        settings.OPEN4K_NAMESPACE, body["spec"]["cloud"], "network")
    obj = kube.find(FloatingIP, name, namespace=namespace)

    if body.get("status", {}).get("applied") == True:
        LOG.info(f"{name} exists, updating ...")
        os_obj = getattr(getattr(c, "floatingips"), "get_floatingips")(
            **{'floatingip_id': body['status']['object']['id']})
        if isinstance(os_obj, model.Model):
            os_obj = os_obj.marshal()
        obj.patch(
            {"status": {"object": os_obj}},
            subresource="status",
        )
        return

    try:
        os_obj = c.floatingips.create_floatingip(
            floatingip=body["spec"]["body"]
        )
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
async def floatingip_delete_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got FloatingIP delete event {name}")
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
        settings.OPEN4K_NAMESPACE, body["spec"]["cloud"], "network")
    getattr(getattr(c, "floatingips"), "delete_floatingip")(floatingip_id=obj_id)