
pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timestamps()
    }

    environment {
        IMAGE_NAME = 'manoj9627/flask-mysql-app'
        APP_CONTAINER = 'flask-app'
        DB_CONTAINER = 'flask-mysql'
        APP_PORT = '5000'
        DB_NAME = 'flaskdb'
        DB_USER = 'appuser'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu

                    docker build \
                        -t ${IMAGE_NAME}:${BUILD_NUMBER} \
                        -t ${IMAGE_NAME}:latest .
                '''
            }
        }

        stage('Start MySQL for Testing') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'mysql-test',
                        usernameVariable: 'MYSQL_USER',
                        passwordVariable: 'MYSQL_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -eu

                        docker network create flask-net || true

                        docker rm -f ${DB_CONTAINER} ${APP_CONTAINER} || true

                        docker run -d \
                            --name ${DB_CONTAINER} \
                            --network flask-net \
                            --network-alias mysql \
                            -e MYSQL_ROOT_PASSWORD="$MYSQL_PASSWORD" \
                            -e MYSQL_DATABASE=${DB_NAME} \
                            -e MYSQL_USER=${DB_USER} \
                            -e MYSQL_PASSWORD="$MYSQL_PASSWORD" \
                            mysql:8.4

                        for i in $(seq 1 40); do
                            if docker exec ${DB_CONTAINER} \
                                mysqladmin ping -h 127.0.0.1 \
                                -uroot -p"$MYSQL_PASSWORD" \
                                --silent; then
                                echo "MySQL is ready."
                                exit 0
                            fi
                            sleep 3
                        done

                        docker logs ${DB_CONTAINER}
                        exit 1
                    '''
                }
            }
        }

        stage('Test Flask Application') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'mysql-test',
                        usernameVariable: 'MYSQL_USER',
                        passwordVariable: 'MYSQL_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -eu

                        docker run -d \
                            --name ${APP_CONTAINER} \
                            --network flask-net \
                            -p 127.0.0.1:5001:5000 \
                            -e DB_HOST=mysql \
                            -e DB_USER=${DB_USER} \
                            -e DB_PASSWORD="$MYSQL_PASSWORD" \
                            -e DB_NAME=${DB_NAME} \
                            ${IMAGE_NAME}:${BUILD_NUMBER}

                        for i in $(seq 1 30); do
                            if curl --fail --silent \
                                http://127.0.0.1:5001/health; then
                                echo
                                echo "Flask health check passed."
                                exit 0
                            fi
                            sleep 2
                        done

                        docker logs ${APP_CONTAINER}
                        exit 1
                    '''
                }
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub',
                        usernameVariable: 'DOCKERHUB_USER',
                        passwordVariable: 'DOCKERHUB_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -eu

                        echo "$DOCKERHUB_PASSWORD" | \
                            docker login \
                            -u "$DOCKERHUB_USER" \
                            --password-stdin

                        docker push ${IMAGE_NAME}:${BUILD_NUMBER}
                        docker push ${IMAGE_NAME}:latest

                        docker logout
                    '''
                }
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'mysql-prod',
                        usernameVariable: 'MYSQL_USER',
                        passwordVariable: 'MYSQL_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -eu

                        # Create a persistent MySQL volume.
                        docker volume create flask-mysql-data
                        docker network create flask-prod-net || true

                        # Create production MySQL only if it does not exist.
                        if ! docker container inspect flask-mysql-prod \
                            >/dev/null 2>&1; then
                            docker run -d \
                                --name flask-mysql-prod \
                                --restart unless-stopped \
                                --network flask-prod-net \
                                --network-alias mysql \
                                -e MYSQL_ROOT_PASSWORD="$MYSQL_PASSWORD" \
                                -e MYSQL_DATABASE=${DB_NAME} \
                                -e MYSQL_USER=${DB_USER} \
                                -e MYSQL_PASSWORD="$MYSQL_PASSWORD" \
                                -v flask-mysql-data:/var/lib/mysql \
                                mysql:8.4
                        fi

                        # Wait for production MySQL.
                        for i in $(seq 1 40); do
                            if docker exec flask-mysql-prod \
                                mysqladmin ping -h 127.0.0.1 \
                                -uroot -p"$MYSQL_PASSWORD" \
                                --silent; then
                                break
                            fi
                            if [ "$i" -eq 40 ]; then
                                docker logs flask-mysql-prod
                                exit 1
                            fi
                            sleep 3
                        done

                        # Replace the application container.
                        docker rm -f ${APP_CONTAINER} || true

                        docker run -d \
                            --name ${APP_CONTAINER} \
                            --restart unless-stopped \
                            --network flask-prod-net \
                            -p ${APP_PORT}:5000 \
                            -e DB_HOST=mysql \
                            -e DB_USER=${DB_USER} \
                            -e DB_PASSWORD="$MYSQL_PASSWORD" \
                            -e DB_NAME=${DB_NAME} \
                            ${IMAGE_NAME}:${BUILD_NUMBER}

                        # Verify deployment.
                        for i in $(seq 1 30); do
                            if curl --fail --silent \
                                http://127.0.0.1:${APP_PORT}/health; then
                                echo
                                echo "Deployment successful."
                                exit 0
                            fi
                            sleep 2
                        done

                        docker logs ${APP_CONTAINER}
                        exit 1
                    '''
                }
            }
        }
    }

    post {
        always {
            sh '''
                docker rm -f ${APP_CONTAINER} ${DB_CONTAINER} \
                    >/dev/null 2>&1 || true
                docker network rm flask-net \
                    >/dev/null 2>&1 || true
            '''
            echo 'Pipeline finished.'
        }
    }
}
