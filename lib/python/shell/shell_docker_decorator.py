import os


class ShellDockerDecorator:
    def __init__(self, docker_image: str = "ghcr.io/msys2/msys2-docker-experimental", user: str = os.getlogin()):
        self.__docker_image = docker_image
        self.__user = user

    def __call__(self, func):
        def __decorator_func(*args, **kwargs) -> str:
            cmd_line = func(*args, **kwargs)
            return f'docker run -it "{self.__docker_image}" {cmd_line}'

        return __decorator_func
