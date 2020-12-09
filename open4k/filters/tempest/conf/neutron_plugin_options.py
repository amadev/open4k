from openstack_controller.filters.tempest import base_section


class NeutronPluginOptions(base_section.BaseSection):

    name = "neutron_plugin_options"
    options = [
        "advanced_image_ref",
        "advanced_image_flavor_ref",
        "advanced_image_ssh_user",
        "available_type_drivers",
        "agent_availability_zone",
        "default_image_is_advanced",
        "dns_domain",
        "l3_agent_mode",
        "max_mtu",
        "max_networks_per_project",
        "multicast_group_range",
        "provider_net_base_segm_id",
        "provider_vlans",
        "q_agent",
        "specify_floating_ip_address_available",
        "ssh_proxy_jump_host",
        "ssh_proxy_jump_keyfile",
        "ssh_proxy_jump_password",
        "ssh_proxy_jump_port",
        "ssh_proxy_jump_username",
        "test_mtu_networks",
    ]

    @property
    def advanced_image_ref(self):
        pass

    @property
    def advanced_image_flavor_ref(self):
        pass

    @property
    def advanced_image_ssh_user(self):
        pass

    @property
    def available_type_drivers(self):
        pass

    @property
    def agent_availability_zone(self):
        pass

    @property
    def default_image_is_advanced(self):
        pass

    @property
    def dns_domain(self):
        dns_domain = self.get_values_item(
            "neutron", "conf.neutron.DEFAULT.dns_domain"
        )
        if dns_domain:
            if dns_domain.endswith("."):
                return dns_domain[:-1]
            else:
                return dns_domain

    @property
    def l3_agent_mode(self):
        pass

    @property
    def max_mtu(self):
        pass

    @property
    def max_networks_per_project(self):
        pass

    @property
    def multicast_group_range(self):
        pass

    @property
    def provider_net_base_segm_id(self):
        pass

    @property
    def provider_vlans(self):
        pass

    @property
    def q_agent(self):
        pass

    @property
    def specify_floating_ip_address_available(self):
        pass

    @property
    def ssh_proxy_jump_host(self):
        pass

    @property
    def ssh_proxy_jump_keyfile(self):
        pass

    @property
    def ssh_proxy_jump_password(self):
        pass

    @property
    def ssh_proxy_jump_port(self):
        pass

    @property
    def ssh_proxy_jump_username(self):
        pass

    @property
    def test_mtu_networks(self):
        pass
