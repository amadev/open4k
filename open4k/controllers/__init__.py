
from . import flavor

from . import securitygroup

from . import floatingip

from . import image


RESOURCES = {}


RESOURCES['flavor'] = flavor.Flavor

RESOURCES['securitygroup'] = securitygroup.SecurityGroup

RESOURCES['floatingip'] = floatingip.FloatingIP

RESOURCES['image'] = image.Image
