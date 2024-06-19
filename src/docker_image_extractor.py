import os
import yaml
from git import Repo, GitCommandError, InvalidGitRepositoryError


class GitRepositoryError(Exception):
    pass


class InvalidGitRepository(GitRepositoryError):
    pass


class BranchCheckoutError(GitRepositoryError):
    pass


def scan_repositories(base_path):
    repos = []
    for root, dirs, files in os.walk(base_path):
        if '.git' in dirs:
            repos.append(root)
    return repos


def get_all_branches(repo_path):
    try:
        repo = Repo(repo_path)
        branches = [ref.name.split('/')[-1] for ref in repo.refs if 'HEAD' not in ref.name]

        if 'origin' in repo.remotes:
            branches += [ref.name.split('/')[-1] for ref in repo.remote('origin').refs if 'HEAD' not in ref.name]

        return list(set(branches))
    except InvalidGitRepositoryError as e:
        raise InvalidGitRepository(f"Invalid git repository: {e}")
    except ValueError as e:
        raise GitRepositoryError(f"Error: {e}")


def has_unmerged_paths(repo):
    unmerged_files = repo.index.unmerged_blobs()
    return bool(unmerged_files)


def list_changed_files(repo):
    changed_files = [item.a_path for item in repo.index.diff(None)]
    return changed_files


def checkout_branch(repo, branch_name):
    git = repo.git

    try:
        if not repo.head.is_valid():
            raise BranchCheckoutError("HEAD is not in a valid state. Can't switch branches.")

        if repo.head.is_detached:
            raise BranchCheckoutError("HEAD is detached. Can't switch branches.")

        current_branch = repo.active_branch.name

        if repo.index.unmerged_blobs():
            raise BranchCheckoutError(
                "There are unmerged paths in the working directory. Staying on the current branch.")

        if repo.is_dirty(untracked_files=True):
            git.stash('save', 'Auto-stash before checkout')
            git.checkout(branch_name)

            try:
                git.stash('pop')
            except GitCommandError as e:
                raise BranchCheckoutError(
                    f"An error occurred while popping stash. A merge conflict occurred. Please resolve the conflicts manually and commit the changes.")
        else:
            git.checkout(branch_name)

        return True
    except GitCommandError as e:
        try:
            git.checkout(current_branch)
        except GitCommandError as checkout_error:
            raise BranchCheckoutError(
                f"An error occurred. Returning to the current branch '{current_branch}'. Failed to return to the current branch '{current_branch}': {checkout_error}\nPlease resolve any conflicts manually and commit the changes.")

        raise BranchCheckoutError(f"An error occurred. Returning to the current branch '{current_branch}'.")
    except InvalidGitRepositoryError as e:
        raise InvalidGitRepository(f"Invalid git repository")
    except ValueError as e:
        raise GitRepositoryError(f"Error accessing repository")


def parse_dockerfile(dockerfile_path):
    images = []
    with open(dockerfile_path, 'r') as file:
        for line in file:
            if line.startswith('FROM'):
                images.append(line.split()[1])
    return images


def parse_docker_compose(compose_path):
    images = []
    with open(compose_path, 'r') as file:
        compose_content = yaml.safe_load(file)
        services = compose_content.get('services', {})
        for service in services.values():
            image = service.get('image')
            if image:
                images.append(image)
    return images


def parse_github_actions(actions_path):
    images = []
    try:
        with open(actions_path, 'r') as file:
            actions_content = yaml.safe_load(file)
            if actions_content is None:
                return images
            jobs = actions_content.get('jobs', {})
            for job in jobs.values():
                steps = job.get('steps', [])
                for step in steps:
                    if 'image' in step:
                        images.append(step['image'])
    except yaml.YAMLError as e:
        raise GitRepositoryError(f"Error parsing YAML file {actions_path}")
    except Exception as e:
        raise GitRepositoryError(f"Unexpected error while processing file {actions_path}")

    return images


def process_docker_files(repo_path):
    docker_images = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file == 'Dockerfile':
                dockerfile_path = parse_dockerfile(os.path.join(root, file))
                if dockerfile_path:
                    docker_images += dockerfile_path
            elif file == 'docker-compose.yml':
                compose_path = parse_docker_compose(os.path.join(root, file))
                if compose_path:
                    docker_images += compose_path
            elif file.endswith('.yml') or file.endswith('.yaml'):
                actions_path = parse_github_actions(os.path.join(root, file))
                if actions_path:
                    docker_images += actions_path

    return docker_images


def get_all_images_with_tags(base_path):
    all_images = set()
    repositories = scan_repositories(base_path)
    for repo_path in repositories:
        try:
            repo = Repo(repo_path)
            branches = get_all_branches(repo_path)

            for branch in branches:
                checkout_result = checkout_branch(repo, branch)
                if checkout_result is not True:
                    break

                images = process_docker_files(repo_path)
                for image in images:
                    all_images.add(image)

        except BranchCheckoutError as e:
            images = process_docker_files(repo_path)
            for image in images:
                all_images.add(image)

        except (InvalidGitRepository, GitRepositoryError) as e:
            continue

    return [image for image in all_images if ':' in image and 'latest' not in image.split(':')[1]]