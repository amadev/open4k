from . import flavor

from . import image

from . import network

from . import securitygroup

from . import instance

from . import floatingip

from . import port


RESOURCES = {}


RESOURCES["flavor"] = flavor.Flavor

RESOURCES["image"] = image.Image

RESOURCES["network"] = network.Network

RESOURCES["securitygroup"] = securitygroup.SecurityGroup

RESOURCES["instance"] = instance.Instance

RESOURCES["floatingip"] = floatingip.FloatingIP

RESOURCES["port"] = port.Port
