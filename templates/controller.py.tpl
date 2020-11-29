import base64
import kopf
import pykube
import yaml

from bravado_core import model
import os_sdk_light as osl

from open4k import utils
from open4k import kube

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

    if body.get("status", {}).get("applied") == True:
        LOG.info(f"{name} exists")
        return

    clouds_obj = kube.find(pykube.Secret, "open4k", namespace=namespace)
    clouds = yaml.safe_load(
        base64.b64decode(clouds_obj.obj["data"]["clouds.yaml"]))
    client = osl.get_client(
        cloud=body["spec"]["cloud"],
        service="{{ api.service }}",
        schema=osl.schema("{{ api.service }}.yaml"),
        cloud_config=clouds,
    )
    obj = kube.find({{ kind }}, name, namespace=namespace)
    try:
        created = client.{{ api.object }}.{{ api.create}}(
            {{ kind | lower }}=body["spec"]["body"]
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

    clouds_obj = kube.find(pykube.Secret, "open4k", namespace=namespace)
    clouds = yaml.safe_load(
        base64.b64decode(clouds_obj.obj["data"]["clouds.yaml"]))
    client = osl.get_client(
        cloud=body["spec"]["cloud"],
        service="{{ api.service }}",
        schema=osl.schema("{{ api.service }}.yaml"),
        cloud_config=clouds,
    )
    client.{{ api.object }}.{{ api.delete }}({{ kind | lower }}_id=obj_id)
