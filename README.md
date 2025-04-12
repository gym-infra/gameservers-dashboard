# Game Servers Dashboard

A web application for easy management of game server deployments running in Kubernetes.

## Overview

The Game Servers Dashboard provides an easy way to monitor and manage game server deployments running in a Kubernetes cluster. It offers the following features:

- Overview of all game deployments with status indicators
- Detailed views for each game instance and its components
- Ability to restart deployments with one click
- Support for multiple game types, instances, and components

The application uses Kubernetes deployment annotations to identify and categorize game servers:
- `game-server/game`: The game type (e.g., "factorio", "minecraft")
- `game-server/instance`: The specific instance (e.g., "vanilla", "modded")
- `game-server/component`: The component type (e.g., "gameserver", "webserver")

## Setup and Installation

### Prerequisites

- Python 3.9+
- FastAPI
- Kubernetes cluster with API access
- kubectl configured with appropriate permissions

### Development Environment

1. Clone the repository
2. Create a virtual environment and install dependencies:
```bash
cd servers-dashboard
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Running Locally

The application can run in two modes:
1. **Live mode**: Connects to a real Kubernetes cluster
2. **Mock mode**: Uses mock data for testing without a Kubernetes cluster

#### Live Mode

```bash
python -m app.main
```

The application will attempt to connect to the Kubernetes cluster using:
1. Bearer token from the request header (if provided)
2. In-cluster configuration (if running inside Kubernetes)
3. Local kubeconfig file (~/.kube/config)

#### Mock Mode

For development without a Kubernetes cluster:

```bash
python tests/run_with_mock.py
```

This runs the application with simulated game server deployments.

## Testing

We provide a comprehensive test suite and a convenient test runner script to make testing easier:

### Using the Test Runner

The `run_tests.py` script provides an easy way to run all tests or specific test types:

```bash
# Run all tests
./tests/run_tests.py --all

# Run only unit tests
./tests/run_tests.py --unit

# Run tests with live Kubernetes cluster 
./tests/run_tests.py --live

# Run mock server test
./tests/run_tests.py --mock

# Run tests with coverage report
./tests/run_tests.py --coverage

# Run tests with verbose output
./tests/run_tests.py --verbose
```

### Unit Tests

To run the unit tests directly:

```bash
pytest
```

### Manual Testing with Mock Data

The mock data script provides sample game server deployments for testing:

```bash
python tests/run_with_mock.py
```

### Testing with Real Kubernetes Data

To test with real data, apply the test service account and deployments:

```bash
kubectl apply -f tests/test-serviceaccount.yaml
kubectl apply -f tests/test-deployments.yaml
```

Then run the connection test:

```bash
python tests/check_k8s_connection.py
```

## Helm Deployment

The application can be deployed to Kubernetes using the included Helm chart.

```bash
helm install servers-dashboard ./helm \
  --namespace servers-dashboard --create-namespace \
  --set kubernetesConfig.apiServer=https://kubernetes.default.svc
```

### Authentication with OIDC Proxy

The dashboard is designed to work with an OIDC proxy that provides bearer tokens in the `Authorization` header. The application extracts these tokens and uses them to authenticate with the Kubernetes API.

Example ingress configuration with OIDC:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: servers-dashboard
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/auth-url: "https://auth.example.com/oauth2/auth"
    nginx.ingress.kubernetes.io/auth-signin: "https://auth.example.com/oauth2/start?rd=$escaped_request_uri"
    nginx.ingress.kubernetes.io/auth-response-headers: "Authorization"
spec:
  rules:
  - host: dashboard.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: servers-dashboard
            port:
              number: 8000
```

## CI/CD Pipeline

The project includes a GitHub Actions workflow that:

1. Runs tests and linting
2. Builds and pushes a Docker image to GitHub Container Registry
3. Deploys to Kubernetes using Helm

## License

This project is licensed under the MIT License - see the LICENSE file for details.
