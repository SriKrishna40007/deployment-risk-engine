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
    }

    environment {
        IMAGE_NAME = "dre-demo:${BUILD_NUMBER}"
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

        stage('Prepare Deployment') {
            steps {
                sh 'mkdir -p .generated'
                sh "sed 's|__IMAGE_NAME__|${IMAGE_NAME}|g' k8s/deployment.yaml > .generated/deployment.yaml"
            }
        }

        stage('Docker Security Scan') {
            steps {
                sh "uv run dre docker '${params.DOCKER_CONTEXT}/Dockerfile'"
            }
        }

        stage('Kubernetes Security Scan') {
            steps {
                sh 'uv run dre k8s .generated/deployment.yaml'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh "docker build -t '${IMAGE_NAME}' '${params.DOCKER_CONTEXT}'"
            }
        }

        stage('Deploy') {
            steps {
                sh 'kubectl apply -f .generated/deployment.yaml'
                sh 'kubectl apply -f k8s/service.yaml'
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
            sh 'rm -rf .generated'
            echo 'Deployment Risk Engine pipeline finished.'
        }
    }
}
