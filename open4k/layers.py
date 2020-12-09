import base64
import copy
import json
import functools
import hashlib

import deepmerge
import deepmerge.exception
from deepmerge.strategy import dict as merge_dict
from deepmerge.strategy import list as merge_list
import deepmerge.strategy.type_conflict
import jinja2
import kopf
import yaml

from openstack_controller import constants
from openstack_controller import settings
from openstack_controller.filters.tempest import generate_tempest_config
from openstack_controller import utils

LOG = utils.get_logger(__name__)


ENV = jinja2.Environment(
    loader=jinja2.PackageLoader(__name__.split(".")[0]),
    extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
)
LOG.info(f"found templates {ENV.list_templates()}")

ENV.filters["generate_tempest_config"] = generate_tempest_config
ENV.filters["b64encode"] = base64.b64encode
ENV.filters["decode"] = lambda x: x.decode()
ENV.filters["encode"] = lambda x: x.encode()


class TypeConflictFail(
    deepmerge.strategy.type_conflict.TypeConflictStrategies
):
    @staticmethod
    def strategy_fail(config, path, base, nxt):
        if (type(base), type(nxt)) == (float, int):
            return nxt
        raise deepmerge.exception.InvalidMerge(
            f"Trying to merge different types of objects, {type(base)} and "
            f"{type(nxt)} at path {':'.join(path)}"
        )


class CustomListStrategies(merge_list.ListStrategies):
    """
    Contains the strategies provided for lists.
    """

    @staticmethod
    def strategy_merge(config, path, base, nxt):
        """ merge base with nxt, adds new elements from nxt. """
        merged = copy.deepcopy(base)
        for el in nxt:
            if el not in merged:
                merged.append(el)
        return merged


class CustomMerger(deepmerge.Merger):
    PROVIDED_TYPE_STRATEGIES = {
        list: CustomListStrategies,
        dict: merge_dict.DictStrategies,
    }

    def __init__(
        self, type_strategies, fallback_strategies, type_conflict_strategies
    ):
        super(CustomMerger, self).__init__(
            type_strategies, fallback_strategies, []
        )
        self._type_conflict_strategy_with_fail = TypeConflictFail(
            type_conflict_strategies
        )

    def type_conflict_strategy(self, *args):
        return self._type_conflict_strategy_with_fail(self, *args)


merger = CustomMerger(
    # pass in a list of tuple, with the strategies you are looking to apply
    # to each type.
    # NOTE(pas-ha) We are handling results of yaml.safe_load and k8s api
    # exclusively, thus only standard json-compatible collection data types
    # will be present, so not botherting with collections.abc for now.
    [(list, ["merge"]), (dict, ["merge"])],
    # next, choose the fallback strategies, applied to all other types:
    ["override"],
    # finally, choose the strategies in the case where the types conflict:
    ["fail"],
)


def kopf_exception(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (kopf.TemporaryError, kopf.PermanentError):
            raise
        except deepmerge.exception.InvalidMerge as e:
            raise kopf.PermanentError(f"DeepMerge Error: {e}") from e
        except yaml.YAMLError as e:
            raise kopf.PermanentError(f"YAML error: {e}") from e
        except jinja2.TemplateNotFound as e:
            raise kopf.PermanentError(
                f"Template {e.name} (loaded from file {e.filename}) "
                f"was not found: {e}"
            ) from e
        except jinja2.TemplateSyntaxError as e:
            raise kopf.PermanentError(
                f"Template {e.name} (loaded from {e.filename}) "
                f"has syntax error at lineno {e.lineno}: {e.message}"
            ) from e
        except jinja2.UndefinedError as e:
            raise kopf.TemporaryError(
                f"Template for tried to operate on undefined: " f"{e.message}"
            ) from e
        except Exception as e:
            raise kopf.TemporaryError(f"{e}") from e

    return wrapper


def spec_hash(spec):
    """Generate stable hash of body.spec structure

    as these are objects received from k8s API it is presumed
    that this object is already JSON-serializable w/o any need
    for additional conversions
    """
    hasher = hashlib.sha256()
    hasher.update(json.dumps(spec, sort_keys=True).encode())
    return hasher.hexdigest()


def services(spec, logger, **kwargs):
    base = merge_spec(spec, logger)

    to_apply = set(base["features"].get("services", []))
    LOG.debug(f"Working with openstack services: {to_apply}")

    to_delete = {}
    # NOTE(pas-ha) each diff is (op, (path, parts, ...), old, new)
    # kopf ignores changes to status except its own internal fields
    # and metadata except labels and annotations
    # (kind and apiVersion and namespace are de-facto immutable)
    for op, path, old, new in kwargs.get("diff", []):
        LOG.debug(f"{op} {'.'.join(path)} from {old} to {new}")
        if path == ("spec", "features", "services"):
            # NOTE(pas-ha) something changed in services,
            # need to check if any were deleted
            to_delete = set(old or []) - set(new or [])
    return to_apply, to_delete


@kopf_exception
def render_service_template(
    service, body, meta, spec, logger, **template_args
):
    tpl = ENV.get_template(f"services/{service}.yaml")
    LOG.debug(f"Using template {tpl.filename}")

    # get supported openstack versions
    openstack_versions = [v for v in constants.OpenStackVersion.__members__]

    text = tpl.render(
        body=body,
        meta=meta,
        spec=spec,
        openstack_versions=openstack_versions,
        **template_args,
    )
    data = yaml.safe_load(text)
    return data


def merge_osdpl_into_helmbundle(service, spec, service_helmbundle):
    # let's make sure no deeply located dict are linked during the merge
    # we don't modify input params and return a completely new dict
    spec = copy.deepcopy(spec)
    service_helmbundle = copy.deepcopy(service_helmbundle)

    # We have 4 level of hierarchy, in increasing priority order:
    # 1. helm values.yaml - which is default
    # 2. openstack_controller/templates/services/<helmbundle>.yaml
    # 3. OpenstackDeployment or preset charts section
    # 4. OpenstackDeployment or preset common/group section

    # The values are merged in this specific order.
    for release in service_helmbundle["spec"]["releases"]:
        chart_name = release["chart"].split("/")[-1]
        merger.merge(
            release,
            spec.get("common", {}).get("charts", {}).get("releases", {}),
        )
        for group, charts in constants.CHART_GROUP_MAPPING.items():
            if chart_name in charts:
                common_releases = (
                    spec.get("common", {}).get(group, {}).get("releases", {})
                )
                if chart_name in common_releases:
                    merger.merge(release, common_releases[chart_name])
                else:
                    merger.merge(release, common_releases)

                merger.merge(
                    release["values"],
                    spec.get("common", {}).get(group, {}).get("values", {}),
                )

        merger.merge(
            release["values"],
            spec.get("services", {})
            .get(service, {})
            .get(chart_name, {})
            .get("values", {}),
        )

        # Merge nodes settings
        chart_normalized_override = {}
        for label_tag, override in spec.get("nodes", {}).items():
            daemonset_override = (
                override.get("services", {})
                .get(service, {})
                .get(chart_name, {})
            )
            if daemonset_override:
                for daemonset_name, override in daemonset_override.items():
                    if daemonset_name not in chart_normalized_override:
                        chart_normalized_override[daemonset_name] = {}
                    merger.merge(
                        chart_normalized_override[daemonset_name],
                        {"labels": {label_tag: override}},
                    )

        if chart_normalized_override:
            LOG.debug(
                f"Applying node specific override for {service}:{chart_name}"
            )
            merger.merge(
                release["values"], {"overrides": chart_normalized_override}
            )

    return service_helmbundle


def merge_service_layer(service, spec, kind, data):
    merger.merge(
        data["spec"],
        spec.get("services", {}).get(service, {}).get(kind, {}),
    )

    return data


@kopf_exception
def merge_all_layers(service, body, meta, spec, logger, **template_args):
    """Merge releases and values from osdpl crd into service HelmBundle"""

    orig_spec = copy.deepcopy(body["spec"])
    spec = copy.deepcopy(dict(spec))
    images = render_artifacts(spec)
    service_helmbundle = render_service_template(
        service, body, meta, spec, logger, images=images, **template_args
    )

    # FIXME(pas-ha) either move to dict merging stage before,
    # or move to the templates themselves
    service_helmbundle["spec"]["repositories"] = spec["common"]["charts"][
        "repositories"
    ]
    # first merge osdpl with preset and sizes
    service_helmbundle = merge_osdpl_into_helmbundle(
        service, spec, service_helmbundle
    )
    # and than an "original" osdpl on top of that
    service_helmbundle = merge_osdpl_into_helmbundle(
        service, orig_spec, service_helmbundle
    )
    return service_helmbundle


@kopf_exception
def merge_spec(spec, logger):
    """Merge user-defined OsDpl spec with base for preset and OS version"""
    spec = copy.deepcopy(dict(spec))
    preset = spec["preset"]
    size = spec["size"]
    os_release = spec["openstack_version"]
    LOG.debug(f"Using preset {preset}")
    LOG.debug(f"Using size {size}")

    base = yaml.safe_load(
        ENV.get_template(f"preset/{preset}.yaml").render(
            openstack_version=os_release,
            openstack_namespace=settings.OSCTL_OS_DEPLOYMENT_NAMESPACE,
            services=spec.get("features", {}).get("services", []),
            ironic_mt_enabled=spec.get("features", {})
            .get("ironic", {})
            .get("networks", {})
            .get("baremetal", {})
            .get("network_type")
            == "vlan",
        )
    )
    preset_binary_base_url = base["artifacts"]["binary_base_url"]
    binary_base_url = spec.get("artifacts", {}).get(
        "binary_base_url", preset_binary_base_url
    )
    artifacts = yaml.safe_load(
        ENV.get_template("artifacts.yaml").render(
            binary_base_url=binary_base_url
        )
    )
    sizing = yaml.safe_load(ENV.get_template(f"size/{size}.yaml").render())
    merger.merge(base, artifacts)
    merger.merge(base, sizing)

    # Merge IAM data defined via values, the user defined via spec
    # still have priority
    if settings.OSDPL_IAM_DATA["enabled"]:
        # TODO(vsaienko): pass odic certificate into keystone/horizon pods /etc/ssl/certs folder
        iam_features = {
            "features": {
                "keystone": {
                    "keycloak": {
                        "enabled": True,
                        "url": settings.OSDPL_IAM_DATA["url"],
                        "oidc": {
                            "OIDCSSLValidateServer": False,
                            "OIDCClientID": settings.OSDPL_IAM_DATA["client"],
                        },
                    }
                }
            }
        }
        merger.merge(base, iam_features)

    # Merge operator defaults with user context.
    return merger.merge(base, spec)


def render_cache_template(mspec, name, images):
    artifacts = render_artifacts(mspec)
    tpl = ENV.get_template("native/cache.yaml")
    text = tpl.render(images=images, name=name, pause_image=artifacts["pause"])
    return yaml.safe_load(text)


def render_cache_images():
    return yaml.safe_load(
        ENV.get_template("native/cache_images.yaml").render()
    )


def render_artifacts(spec):
    os_release = spec["openstack_version"]
    # values from preset were earlier merged to spec.
    images_base_url = spec["artifacts"]["images_base_url"]
    binary_base_url = spec["artifacts"]["binary_base_url"]
    return yaml.safe_load(
        ENV.get_template(f"{os_release}/artifacts.yaml").render(
            images_base_url=images_base_url, binary_base_url=binary_base_url
        )
    )
