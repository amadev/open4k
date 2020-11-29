// +kubebuilder:rbac:groups={{ group }}.{{ domain }},resources={{ plural }},verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups={{ group }}.{{ domain }},resources={{ plural }}/status,verbs=get;update;patch
