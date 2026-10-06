pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
    }

    parameters {
        string(
            name: 'DOCKER_CONTEXT',
            defaultValue: 'examples/docker/secure',
            description: 'Docker build context containing the Dockerfile'
        )

        string(
            name: 'MANIFEST',
            defaultValue: 'k8s/deployment.yaml',
            description: 'Kubernetes manifest to scan and deploy'
        )

        string(
            name: 'IMAGE_NAME',
            defaultValue: 'dre-demo:latest',
            description: 'Docker image name and tag'
        )
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'uv sync --dev'
            }
        }

        stage('Test') {
            steps {
                sh 'uv run pytest'
            }
        }

        stage('Docker Security Scan') {
            steps {
                sh "uv run dre docker '${params.DOCKER_CONTEXT}/Dockerfile'"
            }
        }

        stage('Kubernetes Security Scan') {
            steps {
                sh "uv run dre k8s '${params.MANIFEST}'"
            }
        }

        stage('Build Docker Image') {
            steps {
                sh "docker build -t '${params.IMAGE_NAME}' '${params.DOCKER_CONTEXT}'"
            }
        }

        stage('Deploy') {
            steps {
                sh "kubectl apply -f '${params.MANIFEST}'"
                sh 'kubectl apply -f k8s/service.yaml'
                sh "kubectl set image deployment/dre-demo app='${params.IMAGE_NAME}'"
                sh 'kubectl rollout status deployment/dre-demo --timeout=120s'
            }
        }
    }

    post {
        success {
            echo 'All security gates passed. Deployment completed successfully.'
        }

        failure {
            echo 'Pipeline blocked or failed before deployment.'
        }

        always {
            echo 'Deployment Risk Engine pipeline finished.'
        }
    }
}
