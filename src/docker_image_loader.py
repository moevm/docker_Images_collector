import os
import subprocess
from .exception import DockerDaemonNotRunningError


def is_docker_running():
    try:
        subprocess.run(["docker", "ps"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False


def image_exists(image):
    try:
        subprocess.run(["docker", "inspect", image], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False


def save_docker_image(image, directory):
    if not image_exists(image):
        return

    if not os.path.exists(directory):
        os.makedirs(directory)

    file_name = os.path.join(directory, image.replace(":", "_") + ".tar")
    try:
        subprocess.run(["docker", "save", "-o", file_name, image], check=True)
    except subprocess.CalledProcessError as e:
        pass


def save_docker_images(images, directory):
    if not is_docker_running():
        raise DockerDaemonNotRunningError("Docker daemon is not running. Please start Docker and try again.")

    for image in images:
        save_docker_image(image, directory)
