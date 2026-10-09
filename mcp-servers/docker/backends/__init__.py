import os
import shutil


def get_backend():
    docker_mode = os.getenv("DOCKER_MODE", "").lower()
    if docker_mode == "demo":
        from .simulated import SimulatedDockerBackend

        return SimulatedDockerBackend()
    if docker_mode == "live" and shutil.which("docker"):
        from .live import LiveDockerBackend

        return LiveDockerBackend()

    mode = os.getenv("CLOUDOPS_MODE", "demo").lower()
    if mode == "live" and shutil.which("docker"):
        from .live import LiveDockerBackend

        return LiveDockerBackend()
    from .simulated import SimulatedDockerBackend

    return SimulatedDockerBackend()
