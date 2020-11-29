
from . import flavor

from . import securitygroup

from . import floatingip

from . import image

from . import instance


RESOURCES = {}


RESOURCES['flavor'] = flavor.Flavor

RESOURCES['securitygroup'] = securitygroup.SecurityGroup

RESOURCES['floatingip'] = floatingip.FloatingIP

RESOURCES['image'] = image.Image

RESOURCES['instance'] = instance.Instance
