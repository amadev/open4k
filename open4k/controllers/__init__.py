
from . import flavor

from . import securitygroup

from . import floatingip


RESOURCES = {}


RESOURCES['flavor'] = flavor.Flavor

RESOURCES['securitygroup'] = securitygroup.SecurityGroup

RESOURCES['floatingip'] = floatingip.FloatingIP
