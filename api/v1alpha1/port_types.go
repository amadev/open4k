/*


Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// EDIT THIS FILE!  THIS IS SCAFFOLDING FOR YOU TO OWN!
// NOTE: json tags are required.  Any new fields you add must have json tags for the fields to be serialized.

// PortSpec defines the desired state of Port
type PortSpec struct {
	// INSERT ADDITIONAL SPEC FIELDS - desired state of cluster
	// Important: Run "make" to regenerate code after modifying this file

	// Foo is an example field of Port. Edit Port_types.go to remove/update
	Foo string `json:"foo,omitempty"`
}

// PortStatus defines the observed state of Port
type PortStatus struct {
	// INSERT ADDITIONAL STATUS FIELD - define observed state of cluster
	// Important: Run "make" to regenerate code after modifying this file
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status

// Port is the Schema for the ports API
type Port struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   PortSpec   `json:"spec,omitempty"`
	Status PortStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

// PortList contains a list of Port
type PortList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []Port `json:"items"`
}

func init() {
	SchemeBuilder.Register(&Port{}, &PortList{})
}

// +kubebuilder:rbac:groups=open4k.amadev.ru,resources=ports,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=open4k.amadev.ru,resources=ports/status,verbs=get;update;patch
