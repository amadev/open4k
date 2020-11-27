import sys
import collections

from bravado_core import model

from open4k import client
from open4k import kube
from open4k import settings


ARGS = {
             # service, resource, class, func
    'image': ['image', 'images', kube.Image, 'list'],
    'network': ['network', 'networks', kube.Network, 'list'],
    'flavor': ['compute', 'flavors', kube.Flavor, 'list_flavors'],
    'instance': ['compute', 'instances', kube.Instance, 'list'],
}


def main(resources):
    for cloud in client.get_clouds(settings.OPEN4K_NAMESPACE)['clouds']:
        for resource in resources:
            import_resources(cloud, resource)


def import_resources(cloud, resource):
    cl = client.get_client(settings.OPEN4K_NAMESPACE, cloud, ARGS[resource][0])
    res = ARGS[resource][1]
    klass = ARGS[resource][2]
    func = ARGS[resource][3]
    os_objs = getattr(getattr(cl, res), func)()[res]
    for os_obj in os_objs:
        data = {
            'apiVersion': klass.version,
            'kind': klass.kind,
            'metadata': {'name': kube.escape(f'{cloud}-{os_obj["name"]}'),
                         "namespace": settings.OPEN4K_NAMESPACE},
            'spec': {'managed': False, 'cloud': cloud},
        }
        if isinstance(os_obj, model.Model):
            os_obj = os_obj.marshal()
        status = {'status': {'success': True, 'object': os_obj}}
        obj = klass(kube.api, data)
        if not obj.exists():
            obj.create()
            obj.patch(status, subresource="status")


if __name__ == '__main__':
    resources =  ('image', 'network', 'flavor', 'instance')
    if len(sys.argv) > 1:
        resources = sys.argv[1:]
    main(resources)
