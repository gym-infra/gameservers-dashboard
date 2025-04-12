"""
API router for the Game Server Dashboard application.
"""
from typing import List

from fastapi import APIRouter, Depends, Path, Query, Request
from pydantic import BaseModel

from app.kubernetes import KubernetesClient, get_k8s_client
from app.kubernetes.client import DeploymentStatus, Game, GameInstance

router = APIRouter(tags=["deployments"])


class DeploymentActionResponse(BaseModel):
    """Response model for deployment action endpoints."""

    status: str
    message: str


@router.get(
    "/deployments",
    response_model=List[DeploymentStatus],
    summary="Get all game server deployments",
)
async def get_deployments(
    request: Request,
    namespace: str = Query(None, description="Filter deployments by namespace"),
    k8s_client: KubernetesClient = Depends(get_k8s_client),
):
    """Get all game server deployments.

    Returns a list of all deployments with game-server annotations.
    Optionally filter by namespace.
    """
    return await k8s_client.get_deployments(namespace=namespace)


@router.post(
    "/deployments/{namespace}/{name}/start",
    response_model=DeploymentActionResponse,
    summary="Start a deployment",
)
async def start_deployment(
    request: Request,
    namespace: str = Path(..., description="Namespace of the deployment"),
    name: str = Path(..., description="Name of the deployment"),
    k8s_client: KubernetesClient = Depends(get_k8s_client),
):
    """Start a specific deployment (set replicas to 1).

    Scales the deployment to 1 replica.
    """
    result = await k8s_client.scale_deployment(namespace=namespace, name=name, replicas=1)
    return DeploymentActionResponse(status=result["status"], message=result["message"])


@router.post(
    "/deployments/{namespace}/{name}/restart",
    response_model=DeploymentActionResponse,
    summary="Restart a deployment",
)
async def restart_deployment(
    request: Request,
    namespace: str = Path(..., description="Namespace of the deployment"),
    name: str = Path(..., description="Name of the deployment"),
    k8s_client: KubernetesClient = Depends(get_k8s_client),
):
    """Restart a specific deployment.

    Executes a rollout restart on the specified deployment.
    """
    result = await k8s_client.restart_deployment(namespace=namespace, name=name)
    return DeploymentActionResponse(status=result["status"], message=result["message"])


@router.post(
    "/deployments/{namespace}/{name}/stop",
    response_model=DeploymentActionResponse,
    summary="Stop a deployment",
)
async def stop_deployment(
    request: Request,
    namespace: str = Path(..., description="Namespace of the deployment"),
    name: str = Path(..., description="Name of the deployment"),
    k8s_client: KubernetesClient = Depends(get_k8s_client),
):
    """Stop a specific deployment (set replicas to 0).

    Scales the deployment to 0 replicas.
    """
    result = await k8s_client.scale_deployment(namespace=namespace, name=name, replicas=0)
    return DeploymentActionResponse(status=result["status"], message=result["message"])


@router.get(
    "/games",
    response_model=List[Game],
    summary="Get all games",
)
async def get_games(
    request: Request,
    k8s_client: KubernetesClient = Depends(get_k8s_client),
):
    """Get a list of all games.

    Returns a list of all games with their instance and component counts.
    """
    return await k8s_client.get_games()


@router.get(
    "/games/{game_name}/instances",
    response_model=List[GameInstance],
    summary="Get instances for a game",
)
async def get_game_instances(
    request: Request,
    game_name: str = Path(..., description="Name of the game"),
    k8s_client: KubernetesClient = Depends(get_k8s_client),
):
    """Get all instances for a specific game.

    Returns a list of all instances with their component deployments.
    """
    return await k8s_client.get_game_instances(game_name=game_name)
