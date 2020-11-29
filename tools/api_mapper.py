import os
import jinja2
import yaml
import subprocess


ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
    extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
)


def create_go_crd(doc):
    fname = f'api/{doc["version"]}/{doc["kind"].lower()}_types.go'
    if not os.path.exists(fname):
        cmd = f'operator-sdk create api --group {doc["group"]} --version {doc["version"]} --kind {doc["kind"]} --resource=true --controller=false'
        cmd = cmd.split()
        subprocess.check_call(cmd)
        with open(fname, "a") as f:
            f.write(ENV.get_template("rbac.tpl").render(**doc))


def create_controller(doc):
    fname = f'open4k/controllers/{doc["kind"]}.py'.lower()
    with open(fname, "w") as f:
        f.write(ENV.get_template("controller.py.tpl").render(**doc))


def main():
    data = open('api_mapper.yaml').read()
    docs  = [yaml.safe_load(i) for i in data.split('---') if i]

    fname = 'open4k/controllers/__init__.py'
    with open(fname, "w") as f:
        f.write(ENV.get_template("controllers_init.py.tpl").render({'docs': docs}))

    for doc in docs:
        create_go_crd(doc)
        create_controller(doc)



if __name__ == '__main__':
    main()
