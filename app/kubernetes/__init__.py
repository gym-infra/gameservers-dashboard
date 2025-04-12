"""
Kubernetes client module for interacting with the K8s API.
"""
from .client import KubernetesClient, get_k8s_client

__all__ = ["KubernetesClient", "get_k8s_client"]
