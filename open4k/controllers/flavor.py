import base64
import kopf
import pykube
import yaml

import os_sdk_light as osl

from open4k import kube
from open4k import utils


LOG = utils.get_logger(__name__)


@kopf.on.create(*kube.Flavor.kopf_on_args)
@kopf.on.update(*kube.Flavor.kopf_on_args)
@kopf.on.resume(*kube.Flavor.kopf_on_args)
async def flavor_change_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got flavor change event {name}")
    if body.get('status', {}).get("success") == True:
        LOG.info(f"{name} exists")
        return

    clouds = kube.find(pykube.Secret, 'open4k', namespace=namespace)
    clouds = yaml.safe_load(base64.b64decode(clouds.obj['data']['clouds.yaml']))
    #  body['spec'].get('api_version')
    compute_client = osl.get_client(cloud=body['spec']['cloud'],
                                    service='compute',
                                    schema=osl.schema('compute.yaml'),
                                    cloud_config=clouds)
    flavor = kube.find(kube.Flavor, name, namespace=namespace)
    try:
        created = compute_client.flavors.create_flavor(
            flavor=body['spec']['body'])['flavor'].marshal()
    except Exception as e:
        flavor.patch({"status": {"success": False, "error": str(e)}}, subresource="status")
        raise
    flavor.patch({"status": {"success": True, "error": "", "object": created}}, subresource="status")


@kopf.on.delete(*kube.Flavor.kopf_on_args)
async def flavor_delete_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got flavor delete event {name}")
    if not body.get('status', {}).get("success"):
        LOG.info(f"{name} was not applied successfully")
        return
    flavor_id = body['status'].get('object', {}).get('id')
    if not flavor_id:
        LOG.info(f"Cannot get id for {name}")
        return
    clouds = kube.find(pykube.Secret, 'open4k', namespace=namespace)
    clouds = yaml.safe_load(base64.b64decode(clouds.obj['data']['clouds.yaml']))
    compute_client = osl.get_client(cloud=body['spec']['cloud'],
                                    service='compute',
                                    schema=osl.schema('compute.yaml'),
                                    cloud_config=clouds)
    try:
        compute_client.flavors.delete_flavor(flavor_id=flavor_id)
    except Exception as e:
        raise
