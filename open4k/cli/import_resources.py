import sys

from bravado_core import model

from open4k import client
from open4k import kube
from open4k import settings
from open4k.controllers import RESOURCES


def main(resources):
    for cloud in client.get_clouds(settings.OPEN4K_NAMESPACE)["clouds"]:
        for resource in resources:
            import_resources(cloud, resource)


def import_resources(cloud, resource):

    klass = RESOURCES[resource]
    cl = client.get_client(
        settings.OPEN4K_NAMESPACE, cloud, klass.api['service'])
    api_object = getattr(cl, klass.api['objects'])
    func = getattr(api_object, klass.api['list'])
    os_objs = func()[klass.api['objects']]
    for os_obj in os_objs:
        data = {
            "apiVersion": klass.version,
            "kind": klass.kind,
            "metadata": {
                "name": kube.escape(f'{cloud}-{os_obj["name"]}'),
                "namespace": settings.OPEN4K_NAMESPACE,
            },
            "spec": {"managed": False, "cloud": cloud},
        }
        if isinstance(os_obj, model.Model):
            os_obj = os_obj.marshal()
        status = {"status": {"success": True, "object": os_obj}}
        obj = klass(kube.api, data)
        if not obj.exists():
            obj.create()
            obj.patch(status, subresource="status")


if __name__ == "__main__":
    resources = RESOURCES.keys()
    if len(sys.argv) > 1:
        resources = sys.argv[1:]
    main(resources)
