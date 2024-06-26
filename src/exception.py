class DockerDaemonNotRunningError(Exception):
    pass


class GitRepositoryError(Exception):
    pass


class InvalidGitRepository(GitRepositoryError):
    pass


class BranchCheckoutError(GitRepositoryError):
    pass
