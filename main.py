import os
import argparse
from src.docker_image_extractor import get_all_images_with_tags, get_remote_repo_images_with_tags
from src.docker_image_loader import save_docker_images
from src.yandex_disk_uploader import upload_to_yandex_disk


def main():
    parser = argparse.ArgumentParser(description="Docker Image Manager")
    parser.add_argument('--function', choices=['local', 'remote'], required=True, help="Specify which function to call")
    parser.add_argument('--base_path', type=str, help="Base path for local repositories")
    parser.add_argument('--save_directory', type=str, required=True, help="Directory to save Docker images")
    parser.add_argument('--yandex_disk_directory', type=str, required=True, help="Directory on Yandex Disk")
    parser.add_argument('--yandex_disk_token', type=str, required=True, help="Yandex Disk OAuth token")
    parser.add_argument('--repo_urls', type=str, help="Comma-separated list of remote repository URLs")

    args = parser.parse_args()

    if args.function == 'local':
        if not args.base_path:
            raise ValueError("base_path is required for local function")
        images = get_all_images_with_tags(args.base_path)
    elif args.function == 'remote':
        if not args.repo_urls:
            raise ValueError("repo_urls is required for remote function")
        repo_urls = args.repo_urls.split(',')
        images = get_remote_repo_images_with_tags(repo_urls)

    save_docker_images(images, args.save_directory)
    upload_to_yandex_disk(args.yandex_disk_directory, args.yandex_disk_token, args.yandex_disk_directory)


if __name__ == "__main__":
    main()
