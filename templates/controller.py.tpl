import kopf
import pykube

from bravado_core import model

from open4k import utils
from open4k import kube
from open4k import client
from open4k import settings

LOG = utils.get_logger(__name__)
kopf_on_args = ["{{ group }}.{{ domain }}", "{{ version }}", "{{ plural }}"]


class {{ kind }}(pykube.objects.NamespacedAPIObject, kube.HelmBundleMixin):
    version = "{{ group}}.{{ domain }}/{{ version }}"
    endpoint = "{{ plural }}"
    kind = "{{ kind }}"
    api = {{ api }}


@kopf.on.create(*kopf_on_args)
@kopf.on.update(*kopf_on_args)
@kopf.on.resume(*kopf_on_args)
async def {{ kind | lower }}_change_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got {{ kind }} change event {name}")
    if body["spec"].get("managed") == False:
        LOG.info(f"{name} is not managed")
        return

    c = client.get_client(
        settings.OPEN4K_NAMESPACE, body["spec"]["cloud"], "{{ api.service }}")
    obj = kube.find({{ kind }}, name, namespace=namespace)

    if body.get("status", {}).get("applied") == True:
        LOG.info(f"{name} exists, updating ...")
        os_obj = getattr(getattr(c, "{{ api.objects }}"), "{{ api.get_ }}")(
            **{'{{ api.object }}_id': body['status']['object']['id']})
        if isinstance(os_obj, model.Model):
            os_obj = os_obj.marshal()
        obj.patch(
            {"status": {"object": os_obj}},
            subresource="status",
        )
        return

    try:
        os_obj = c.{{ api.objects }}.{{ api.create}}(
            {{ api.object }}=body["spec"]["body"]
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
async def {{ kind | lower }}_delete_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got {{ kind }} delete event {name}")
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
        settings.OPEN4K_NAMESPACE, body["spec"]["cloud"], "{{ api.service }}")
    getattr(getattr(c, "{{ api.objects }}"), "{{ api.delete}}")({{ api.object }}_id=obj_id)
