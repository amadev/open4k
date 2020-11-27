import base64
import kopf
import pykube
import yaml

from open4k import kube
import os_sdk_light as osl


def get_client(namespace, cloud, service):
    clouds = get_clouds(namespace)
    #  body['spec'].get('api_version')
    print(cloud,
          service,
          osl.schema(f'{service}.yaml'),
          clouds)
    client =  osl.get_client(cloud=cloud,
                             service=service,
                             schema=osl.schema(f'{service}.yaml'),
                             cloud_config=clouds)
    return client


def get_clouds(namespace):
    clouds = kube.find(pykube.Secret, 'open4k', namespace=namespace)
    clouds = yaml.safe_load(base64.b64decode(clouds.obj['data']['clouds.yaml']))
    return clouds
