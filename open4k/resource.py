import json
import time

from open4k import client
from open4k import kube
from open4k import settings
from open4k.controllers import RESOURCES


def import_resources(cloud, resource, list_filter=None, dry_run=False):
    klass = RESOURCES[resource]
    cl = client.get_client(
        settings.OPEN4K_NAMESPACE, cloud, klass.api["service"]
    )
    api_object = getattr(cl, klass.api["objects"])
    func = getattr(api_object, klass.api["list"])
    os_objs = func(**(list_filter or {}))[klass.api["objects"]]
    for os_obj in os_objs:
        if dry_run:
            print(json.dumps(os_obj))
            continue
        part = os_obj.get("name")
        if not part:
            part = os_obj["id"]
        name = kube.escape(f"{cloud}-{part}")
        data = {
            "apiVersion": klass.version,
            "kind": klass.kind,
            "metadata": {
                "name": name,
                "namespace": settings.OPEN4K_NAMESPACE,
            },
            "spec": {"managed": False, "cloud": cloud},
        }
        obj = klass(kube.api, data)
        start = time.time()
        if not obj.exists():
            obj.create()
            status = {"status": {"applied": True, "object": os_obj}}
            obj.patch(status, subresource="status")
            op = "created"
        else:
            status = {"status": {"object": os_obj}}
            obj.patch(status, subresource="status")
            op = "updated"
        print(f"{klass.kind} {name}: {op}", time.time() - start)
