pipeline {
    agent any

    environment {
        AWS_REGION = 'us-east-1'
        ECR_REGISTRY = '657157860151.dkr.ecr.us-east-1.amazonaws.com'
        IMAGE_NAME = 'mantra-backend'
    }

    options {
        timeout(time: 45, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Static analysis') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install 'bandit>=1.8,<2'
                    bandit -r backend/app -q
                    docker run --rm -v "$WORKSPACE/prometheus:/etc/prometheus:ro" -w /etc/prometheus --entrypoint promtool prom/prometheus:v2.54.1 test rules alert.rules.test.yml
                '''
            }
        }

        stage('Build image') {
            steps {
                sh '''
                    if [ "$GIT_BRANCH" = origin/main ] && aws ecr describe-images --repository-name "$IMAGE_NAME" --image-ids "imageTag=$GIT_COMMIT" --region "$AWS_REGION" >/dev/null 2>&1; then
                        aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"
                        docker pull "${ECR_REGISTRY}/${IMAGE_NAME}:${GIT_COMMIT}"
                    else
                        docker build -t "${ECR_REGISTRY}/${IMAGE_NAME}:${GIT_COMMIT}" ./backend
                    fi
                '''
            }
        }

        stage('Test exact runtime image') {
            steps {
                sh '''
                    docker run --rm -v "$WORKSPACE/tests:/tests:ro" \
                      -e IKI_ENVIRONMENT=test -e IKI_REQUIRE_API_KEY=false \
                      -e IKI_REPOSITORY_BACKEND=memory -e IKI_LOCAL_STORAGE_PATH=/tmp/test-storage \
                      "${ECR_REGISTRY}/${IMAGE_NAME}:${GIT_COMMIT}" \
                      python -m pytest /tests -v -p no:cacheprovider
                '''
            }
        }

        stage('Scan image') {
            steps {
                sh '''
                    trivy image --scanners vuln --severity HIGH,CRITICAL --format json --output trivy-report.json "${ECR_REGISTRY}/${IMAGE_NAME}:${GIT_COMMIT}"
                    trivy image --scanners vuln --ignore-unfixed --exit-code 1 --severity HIGH,CRITICAL "${ECR_REGISTRY}/${IMAGE_NAME}:${GIT_COMMIT}"
                '''
            }
            post { always { archiveArtifacts artifacts: 'trivy-report.json', allowEmptyArchive: false } }
        }

        stage('Push image') {
            when { expression { env.GIT_BRANCH == 'origin/main' || env.BRANCH_NAME == 'main' } }
            steps {
                sh '''
                    aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"
                    if ! aws ecr describe-images --repository-name "$IMAGE_NAME" --image-ids "imageTag=$GIT_COMMIT" --region "$AWS_REGION" >/dev/null 2>&1; then
                        docker push "${ECR_REGISTRY}/${IMAGE_NAME}:${GIT_COMMIT}"
                    fi
                '''
            }
        }

        stage('Deploy exact image') {
            when { expression { env.GIT_BRANCH == 'origin/main' || env.BRANCH_NAME == 'main' } }
            steps {
                withCredentials([sshUserPrivateKey(credentialsId: 'mantra-ec2-ssh', keyFileVariable: 'MANTRA_SSH_KEY')]) {
                    sh '''
                        ansible-playbook -i ansible/inventory/hosts.ini \
                          --private-key "$MANTRA_SSH_KEY" \
                          -e ansible_host=127.0.0.1 \
                          -e "mantra_backend_image=${ECR_REGISTRY}/${IMAGE_NAME}:${GIT_COMMIT}" \
                          ansible/playbooks/deploy.yml
                    '''
                }
            }
        }

    }

    post {
        always { sh 'docker logout "$ECR_REGISTRY" || true' }
    }
}
