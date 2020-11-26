import base64
import kopf
import pykube
import yaml

import os_sdk_light as osl

from open4k import kube
# from open4k.services import base
# from open4k import settings
from open4k import utils


LOG = utils.get_logger(__name__)


@kopf.on.create(*kube.Instance.kopf_on_args)
@kopf.on.update(*kube.Instance.kopf_on_args)
@kopf.on.resume(*kube.Instance.kopf_on_args)
async def instance_change_handler(body, name, namespace, **kwargs):
    LOG.info(f"Got instance change evenc {name}")
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
    server = body['spec']['body']
    instance = kube.find(kube.Instance, name, namespace=namespace)
    try:
        created = compute_client.servers.create_server(server=server)['server']
    except Exception as e:
        instance.patch({"status": {"success": False, "error": str(e)}}, subresource="status")
        raise
    instance.patch({"status": {"success": True, "error": "", "object": created}}, subresource="status")


@kopf.on.delete(*kube.Instance.kopf_on_args)
async def node_maintenance_request_delete_handler(body, retry, **kwargs):
    pass
