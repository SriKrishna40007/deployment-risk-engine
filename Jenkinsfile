pipeline {
    agent any

    parameters {
        string(
            name: 'DOCKER_CONTEXT',
            defaultValue: 'examples/docker/secure',
            description: 'Docker build context containing the Dockerfile'
        )

        string(
            name: 'MANIFEST',
            defaultValue: 'examples/secure/deployment.yaml',
            description: 'Kubernetes manifest to scan'
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
                echo 'Security gates passed. Kubernetes deployment can proceed.'
            }
        }
    }

    post {
        success {
            echo 'All security gates passed. Pipeline completed successfully.'
        }

        failure {
            echo 'Pipeline blocked or failed before deployment.'
        }

        always {
            echo 'Deployment Risk Engine pipeline finished.'
        }
    }
}
