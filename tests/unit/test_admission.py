# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import json

import falcon
from falcon import testing
import pytest

from openstack_controller.admission import controller


# https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/#request
ADMISSION_REQ_JSON = """
{
    "apiVersion": "admission.k8s.io/v1",
    "kind": "AdmissionReview",
    "request": {
        "uid": "00000000-0000-0000-0000-000000000000",
        "kind": {
            "group": "lcm.mirantis.com",
            "version": "v1alpha1",
            "kind": "OpenStackDeployment"
        },
        "resource": {
            "group": "lcm.mirantis.com",
            "version": "v1alpha1",
            "resource": "openstackdeployments"
        },
        "name": "osh-dev",
        "namespace": "openstack",
        "operation": "CREATE",
        "object": {
            "apiVersion": "lcm.mirantis.com/v1alpha1",
            "kind": "OpenStackDeployment",
            "spec": {
                "openstack_version": "ussuri",
                "preset": "compute",
                "size": "tiny",
                "features": {
                    "neutron": {
                        "floating_network": {
                            "physnet": "physnet1"
                        }
                    }
                }
            }
        },
        "oldObject": null,
        "dryRun": false
    }
}
"""

ADMISSION_REQ = json.loads(ADMISSION_REQ_JSON)


@pytest.fixture
def client():
    return testing.TestClient(controller.create_api())


def test_root(client):
    response = client.simulate_get("/")
    assert response.status == falcon.HTTP_OK


def test_minimal_validation_response(client):
    req = copy.deepcopy(ADMISSION_REQ)
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True


def test_validate_invalid_request_body(client):
    req = "Boo!"
    response = client.simulate_post("/validate", body=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "Exception parsing the body of request: Expecting value"
        in response.json["response"]["status"]["message"]
    )


def test_validate_not_satisfying_schema(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req.pop("apiVersion")
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "'apiVersion' is a required property"
        in response.json["response"]["status"]["message"]
    )


def test_openstack_create_master_fail(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["openstack_version"] = "master"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "Using master of OpenStack is not permitted"
        in response.json["response"]["status"]["message"]
    )


def test_openstack_upgrade_ok(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["operation"] = "UPDATE"
    req["request"]["oldObject"] = copy.deepcopy(req["request"]["object"])
    req["request"]["oldObject"]["spec"]["openstack_version"] = "train"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True


def test_openstack_upgrade_to_master_fail(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["operation"] = "UPDATE"
    req["request"]["oldObject"] = copy.deepcopy(req["request"]["object"])
    req["request"]["object"]["spec"]["openstack_version"] = "master"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "Using master of OpenStack is not permitted"
        in response.json["response"]["status"]["message"]
    )


def test_validator_single_fail(client):
    """Test that validation stops on first error"""
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["operation"] = "UPDATE"
    req["request"]["oldObject"] = copy.deepcopy(req["request"]["object"])
    # set up for both master failure and neutron physnet required failure
    # openstack check must be called first and only its failure returned
    req["request"]["object"]["spec"]["openstack_version"] = "master"
    req["request"]["object"]["spec"]["features"]["neutron"] = {}

    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "Using master of OpenStack is not permitted"
        in response.json["response"]["status"]["message"]
    )


def test_openstack_skiplevel_upgrade_fail(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["operation"] = "UPDATE"
    req["request"]["oldObject"] = copy.deepcopy(req["request"]["object"])
    req["request"]["oldObject"]["spec"]["openstack_version"] = "stein"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "Skip-level OpenStack version upgrade is not permitted"
        in response.json["response"]["status"]["message"]
    )


def test_openstack_downgrade_fail(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["operation"] = "UPDATE"
    req["request"]["oldObject"] = copy.deepcopy(req["request"]["object"])
    req["request"]["object"]["spec"]["openstack_version"] = "train"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "downgrade is not permitted"
        in response.json["response"]["status"]["message"]
    )


def test_upgrade_with_extra_changes_fail(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["operation"] = "UPDATE"
    req["request"]["oldObject"] = copy.deepcopy(req["request"]["object"])
    req["request"]["oldObject"]["spec"]["openstack_version"] = "train"
    req["request"]["object"]["spec"]["size"] = "small"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "changing other values in the spec is not permitted"
        in response.json["response"]["status"]["message"]
    )


def test_physnet_required_no_tf(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["features"]["neutron"] = {}
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "physnet needs to be specified"
        in response.json["response"]["status"]["message"]
    )


def test_physnet_optional_tf(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["features"]["neutron"] = {
        "backend": "tungstenfabric"
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True


def _node_specific_request(client, node_override, result):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["nodes"] = node_override
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    if result:
        assert response.json["response"]["allowed"]
    else:
        assert response.json["response"]["allowed"] is False


def test_nodes_node_label(client):
    _node_specific_request(client, {"wrong:label": {"features": {}}}, False)
    _node_specific_request(client, {"good::label": {"services": {}}}, True)


def test_nodes_top_keys(client):
    allowed_top_keys = ["services", "features"]
    for top_key in allowed_top_keys:
        _node_specific_request(client, {"good::label": {top_key: {}}}, True)
    _node_specific_request(client, {"good::label": {"fake": {}}}, False)


def test_nodes_allowed_keys(client):
    allowed_value_override = {"chart_daemonset": {"values": {"conf": {}}}}
    allowed_services = [
        {
            "load-balancer": {"octavia": allowed_value_override},
        },
        {
            "networking": {
                "neutron": allowed_value_override,
                "openvswitch": allowed_value_override,
            }
        },
        {"metering": {"ceilometer": allowed_value_override}},
        {"metric": {"gnocchi": allowed_value_override}},
        {"compute": {"nova": allowed_value_override}},
    ]
    for service in allowed_services:
        _node_specific_request(
            client,
            {"good::label": {"services": service}},
            True,
        )


def test_nodes_wrong_key(client):
    allowed_value_override = {"chart_daemonset": {"values": {"conf": {}}}}
    wrong_service = {
        "identity": {"keystone": allowed_value_override},
    }
    _node_specific_request(
        client,
        {"good::label": {"services": wrong_service}},
        False,
    )


def test_nodes_wrong_chart_value_key(client):
    wrong_value_override = {"chart_daemonset": {"wrong": {"conf": {}}}}
    allowed_service = {
        "compute": {"nova": wrong_value_override},
    }
    _node_specific_request(
        client,
        {"good::label": {"services": allowed_service}},
        False,
    )


def test_nodes_features_top_keys(client):
    allowed_top_keys = [("neutron", {})]
    for top_key, top_value in allowed_top_keys:
        _node_specific_request(
            client, {"good::label": {"features": {top_key: {}}}}, True
        )
    _node_specific_request(
        client, {"good::label": {"features": {"fake": {}}}}, False
    )


def test_nodes_features_neutron_keys(client):
    neutron_required = {"dpdk": {"enabled": True, "driver": "igb_uio"}}
    _node_specific_request(
        client,
        {"good::label": {"features": {"neutron": neutron_required}}},
        True,
    )

    # Bridges valid
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "dpdk": {
                            "enabled": True,
                            "driver": "igb_uio",
                            "bridges": [
                                {"name": "br1", "ip_address": "1.2.3.4/24"}
                            ],
                        }
                    }
                }
            }
        },
        True,
    )

    # Bridges valid additional fields
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "dpdk": {
                            "enabled": True,
                            "driver": "igb_uio",
                            "bridges": [
                                {
                                    "name": "br1",
                                    "ip_address": "1.2.3.4/24",
                                    "additional": "",
                                }
                            ],
                        }
                    }
                }
            }
        },
        True,
    )

    # Bridges missing IP
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "dpdk": {
                            "enabled": True,
                            "driver": "igb_uio",
                            "bridges": [{"name": "br1"}],
                        }
                    }
                }
            }
        },
        False,
    )

    # Bonds valid
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "dpdk": {
                            "enabled": True,
                            "driver": "igb_uio",
                            "bonds": [
                                {
                                    "name": "foo",
                                    "bridge": "br1",
                                    "nics": [
                                        {"name": "br1", "pci_id": "1.2.3:00.1"}
                                    ],
                                }
                            ],
                        }
                    }
                }
            }
        },
        True,
    )

    # Bonds valid additional fields
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "dpdk": {
                            "enabled": True,
                            "driver": "igb_uio",
                            "bonds": [
                                {
                                    "name": "foo",
                                    "bridge": "br1",
                                    "nics": [
                                        {
                                            "name": "br1",
                                            "pci_id": "1.2.3:00.1",
                                            "additional": "option",
                                        }
                                    ],
                                }
                            ],
                        },
                        "tunnel_interface": "br-phy",
                    }
                }
            }
        },
        True,
    )

    # Bonds Missing PCI_ID
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "dpdk": {
                            "enabled": True,
                            "driver": "igb_uio",
                            "bonds": [
                                {
                                    "name": "foo",
                                    "bridge": "br1",
                                    "nics": [{"name": "br1"}],
                                }
                            ],
                        }
                    }
                }
            }
        },
        False,
    )
