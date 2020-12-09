from openstack_controller.filters.tempest import base_section


class Network(base_section.BaseSection):

    name = "network"
    options = [
        "build_interval",
        "build_timeout",
        "catalog_type",
        "default_network",
        "dns_servers",
        "endpoint_type",
        "floating_network_name",
        "port_vnic_type",
        "project_network_cidr",
        "project_network_mask_bits",
        "project_network_v6_cidr",
        "project_network_v6_mask_bits",
        "project_networks_reachable",
        "public_network_id",
        "public_router_id",
        "region",
        "shared_physical_network",
    ]

    @property
    def build_interval(self):
        pass

    @property
    def build_timeout(self):
        pass

    @property
    def catalog_type(self):
        pass

    @property
    def default_network(self):
        pass

    @property
    def dns_servers(self):
        pass

    @property
    def endpoint_type(self):
        pass

    @property
    def floating_network_name(self):
        pass

    @property
    def port_vnic_type(self):
        pass

    @property
    def project_network_cidr(self):
        pass

    @property
    def project_network_mask_bits(self):
        pass

    @property
    def project_network_v6_cidr(self):
        pass

    @property
    def project_network_v6_mask_bits(self):
        pass

    @property
    def project_networks_reachable(self):
        pass

    @property
    def public_network_id(self):
        pass

    @property
    def public_router_id(self):
        pass

    @property
    def region(self):
        pass

    @property
    def shared_physical_network(self):
        pass
