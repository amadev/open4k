{% for doc in docs %}
from . import {{ doc.kind | lower }}
{% endfor %}

RESOURCES = {}

{% for doc in docs %}
RESOURCES['{{ doc.kind | lower }}'] = {{ doc.kind | lower }}.{{ doc.kind }}
{% endfor %}
