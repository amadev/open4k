
from . import flavor

from . import securitygroup


RESOURCES = {}


RESOURCES['flavor'] = flavor.Flavor

RESOURCES['securitygroup'] = securitygroup.SecurityGroup
