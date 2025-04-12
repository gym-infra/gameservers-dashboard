"""
Kubernetes client implementation for interacting with the K8s API.
"""
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel

from kubernetes import client, config
from kubernetes.client.api_client import ApiClient
from kubernetes.client.exceptions import ApiException

# Configure root logger to ensure our logs are displayed
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Annotation keys used to identify game server deployments
GAME_ANNOTATION = "game-server/game"
INSTANCE_ANNOTATION = "game-server/instance"
COMPONENT_ANNOTATION = "game-server/component"


class DeploymentStatus(BaseModel):
    """Model for deployment status information."""

    name: str
    namespace: str
    game: str
    instance: str
    component: str
    replicas: int
    available_replicas: Optional[int] = None
    unavailable_replicas: Optional[int] = None
    status: str  # "active" or "failed"
    conditions: List[Dict[str, Any]] = []


class GameInstance(BaseModel):
    """Model for game instance information."""

    name: str
    components: List[DeploymentStatus]


class Game(BaseModel):
    """Model for game information."""

    name: str
    instance_count: int
    component_count: int
    failing_deployments: int


class KubernetesClient:
    """Client for interacting with the Kubernetes API."""

    def __init__(self, api_client: Optional[ApiClient] = None):
        """Initialize the Kubernetes client.

        Args:
            api_client: Optional pre-configured Kubernetes API client
        """
        self.api_client = api_client
        self._apps_v1_api = None
        self._core_v1_api = None
        self._custom_objects_api = None

    @property
    def apps_v1_api(self):
        """Get the Apps V1 API client."""
        if self._apps_v1_api is None:
            self._apps_v1_api = client.AppsV1Api(api_client=self.api_client)
        return self._apps_v1_api

    @property
    def core_v1_api(self):
        """Get the Core V1 API client."""
        if self._core_v1_api is None:
            self._core_v1_api = client.CoreV1Api(api_client=self.api_client)
        return self._core_v1_api

    @property
    def custom_objects_api(self):
        """Get the Custom Objects API client."""
        if self._custom_objects_api is None:
            self._custom_objects_api = client.CustomObjectsApi(api_client=self.api_client)
        return self._custom_objects_api

    async def get_deployments(self, namespace: Optional[str] = None) -> List[DeploymentStatus]:
        """Get all game server deployments from the Kubernetes API.

        Args:
            namespace: Optional namespace to filter deployments

        Returns:
            List of deployment status objects
        """
        try:
            # Check if we have a namespace specified in the environment (for testing)
            env_namespace = os.environ.get("NAMESPACE")
            if namespace:
                response = self.apps_v1_api.list_namespaced_deployment(namespace=namespace)
            elif env_namespace:
                response = self.apps_v1_api.list_namespaced_deployment(namespace=env_namespace)
            else:
                response = self.apps_v1_api.list_deployment_for_all_namespaces()

            deployments = []
            for item in response.items:
                # Check if the deployment has our game annotations
                annotations = item.metadata.annotations or {}
                game = annotations.get(GAME_ANNOTATION)
                
                if not game:
                    continue  # Skip deployments without our game annotation
                    
                instance = annotations.get(INSTANCE_ANNOTATION, "unknown")
                component = annotations.get(COMPONENT_ANNOTATION, "unknown")
                
                # Get deployment status
                available_replicas = item.status.available_replicas or 0
                unavailable_replicas = item.status.unavailable_replicas or 0
                
                # Determine if the deployment is active or failed
                if (
                    item.spec.replicas == 0 
                    or (item.status.available_replicas is not None 
                        and item.status.available_replicas > 0)
                ):
                    status = "active"
                else:
                    status = "failed"
                
                # Extract conditions
                conditions = []
                if item.status.conditions:
                    for condition in item.status.conditions:
                        conditions.append({
                            "type": condition.type,
                            "status": condition.status,
                            "message": condition.message,
                            "last_transition_time": condition.last_transition_time.isoformat()
                            if condition.last_transition_time else None,
                        })
                
                deployments.append(
                    DeploymentStatus(
                        name=item.metadata.name,
                        namespace=item.metadata.namespace,
                        game=game,
                        instance=instance,
                        component=component,
                        replicas=item.spec.replicas,
                        available_replicas=available_replicas,
                        unavailable_replicas=unavailable_replicas,
                        status=status,
                        conditions=conditions,
                    )
                )
            
            return deployments
        except ApiException as e:
            logger.error(f"Error retrieving deployments: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving deployments: {str(e)}",
            )

    async def get_games(self) -> List[Game]:
        """Get a list of all games with their instance counts.

        Returns:
            List of game objects
        """
        deployments = await self.get_deployments()
        
        # Group deployments by game
        games = {}
        for deployment in deployments:
            game_name = deployment.game
            
            if game_name not in games:
                games[game_name] = {
                    "name": game_name,
                    "instances": set(),
                    "components": set(),
                    "failing_deployments": 0,
                }
            
            games[game_name]["instances"].add(deployment.instance)
            games[game_name]["components"].add(f"{deployment.instance}/{deployment.component}")
            
            if deployment.status == "failed":
                games[game_name]["failing_deployments"] += 1
        
        # Convert to Game model
        result = []
        for game_name, data in games.items():
            result.append(
                Game(
                    name=data["name"],
                    instance_count=len(data["instances"]),
                    component_count=len(data["components"]),
                    failing_deployments=data["failing_deployments"],
                )
            )
        
        return sorted(result, key=lambda g: g.name)

    async def get_game_instances(self, game_name: str) -> List[GameInstance]:
        """Get all instances for a specific game.

        Args:
            game_name: Name of the game

        Returns:
            List of game instance objects
        """
        deployments = await self.get_deployments()
        
        # Filter deployments by game name
        game_deployments = [d for d in deployments if d.game == game_name]
        
        # Group deployments by instance
        instances = {}
        for deployment in game_deployments:
            instance_name = deployment.instance
            
            if instance_name not in instances:
                instances[instance_name] = {
                    "name": instance_name,
                    "components": [],
                }
            
            instances[instance_name]["components"].append(deployment)
        
        # Convert to GameInstance model
        result = []
        for instance_name, data in instances.items():
            result.append(
                GameInstance(
                    name=data["name"],
                    components=sorted(data["components"], key=lambda d: d.component),
                )
            )
        
        return sorted(result, key=lambda i: i.name)

    async def scale_deployment(self, namespace: str, name: str, replicas: int) -> Dict[str, Any]:
        """Scale a specific deployment to the specified number of replicas.

        Args:
            namespace: Namespace of the deployment
            name: Name of the deployment
            replicas: Number of replicas to scale to

        Returns:
            Status information about the scale operation
        """
        try:
            # Get the current deployment
            deployment = self.apps_v1_api.read_namespaced_deployment(
                name=name,
                namespace=namespace,
            )
            
            # Update replicas
            deployment.spec.replicas = replicas
            
            # Apply the update
            self.apps_v1_api.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body={"spec": {"replicas": replicas}},
            )
            
            action = "started" if replicas > 0 else "stopped"
            return {
                "status": "success", 
                "message": f"Deployment {namespace}/{name} {action} successfully"
            }
        except ApiException as e:
            logger.error(f"Error scaling deployment: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error scaling deployment: {str(e)}",
            )

    async def restart_deployment(self, namespace: str, name: str) -> Dict[str, Any]:
        """Restart a specific deployment.

        Args:
            namespace: Namespace of the deployment
            name: Name of the deployment

        Returns:
            Status information about the restart operation
        """
        try:
            # Execute kubectl rollout restart command via API
            api_version = "apps/v1"
            kind = "Deployment"
            
            # Patch with restart annotation
            patch_body = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "kubectl.kubernetes.io/restartedAt": 
                                    client.ApiClient().sanitize_for_serialization(__import__('datetime').datetime.now().isoformat())
                            }
                        }
                    }
                }
            }
            
            self.apps_v1_api.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=patch_body,
            )
            
            return {
                "status": "success", 
                "message": f"Deployment {namespace}/{name} restarted successfully"
            }
        except ApiException as e:
            logger.error(f"Error restarting deployment: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error restarting deployment: {str(e)}",
            )


def get_k8s_client_config(authorization_header: Optional[str] = None) -> ApiClient:
    """Get a configured Kubernetes API client.

    Args:
        authorization_header: Optional Bearer token from the request Authorization header

    Returns:
        Configured API client
    """
    try:
        # First try to use the authorization header if provided (from OIDC proxy)
        if authorization_header and authorization_header.startswith("Bearer "):
            token = authorization_header.split(" ", 1)[1]
            api_server = os.environ.get("K8S_API_SERVER", "https://kubernetes.default.svc")
            
            configuration = client.Configuration()
            configuration.host = api_server
            configuration.api_key = {"authorization": f"Bearer {token}"}
            configuration.api_key_prefix = {"authorization": "Bearer"}
            configuration.verify_ssl = False  # For development only, should be True in production
            
            logger.info("Using bearer token from request for Kubernetes API authentication")
            print(f"USING BEARER TOKEN FROM REQUEST: {api_server}")
            return ApiClient(configuration)
            
        # Next try to use in-cluster configuration
        try:
            config.load_incluster_config()
            logger.info("Using in-cluster Kubernetes configuration")
            print("USING IN-CLUSTER CONFIG")
            return ApiClient()
        except config.ConfigException:
            pass

        # Fall back to kubeconfig
        if os.path.exists(os.path.expanduser("~/.kube/config")):
            config.load_kube_config()
            logger.info("Using kubeconfig for Kubernetes configuration")
            print("USING KUBECONFIG")
            return ApiClient()
        
        logger.error("No valid Kubernetes configuration found")
        print("NO VALID K8S CONFIG")
        raise HTTPException(
            status_code=500,
            detail="No valid Kubernetes configuration found",
        )
    except Exception as e:
        logger.error(f"Error configuring Kubernetes client: {e}")
        print(f"ERROR CONFIGURING K8S CLIENT: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error configuring Kubernetes client: {str(e)}",
        )


async def get_k8s_client(request: Request = None) -> KubernetesClient:
    """Get a configured KubernetesClient instance.

    Args:
        request: FastAPI request to extract authorization header

    Returns:
        KubernetesClient instance
    """
    # Log all headers to help troubleshoot OAuth proxy issues
    print("=== DEBUGGING: REQUEST HEADERS START ===")
    if request:
        for header_name, header_value in request.headers.items():
            # Don't log the actual token value for security reasons
            if header_name.lower() == "authorization":
                print(f"  {header_name}: Bearer [TOKEN REDACTED]")
            else:
                print(f"  {header_name}: {header_value}")
    else:
        print("  No request object provided!")
    print("=== DEBUGGING: REQUEST HEADERS END ===")

    # First try standard Authorization header
    authorization_header = None
    if request:
        # Try standard Authorization header
        authorization_header = request.headers.get("Authorization")
        if not authorization_header:
            # Try common alternative headers that might be used by proxies
            authorization_header = request.headers.get("X-Forwarded-Authorization")
        if not authorization_header:
            # Check for Kubernetes specific auth header
            authorization_header = request.headers.get("X-Auth-Token")
    
    if authorization_header:
        print(f"Found authorization header type: {authorization_header[:10]}...")
    else:
        print("No authorization header found in the request")
    
    api_client = get_k8s_client_config(authorization_header)
    return KubernetesClient(api_client=api_client)
