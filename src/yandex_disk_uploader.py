import os
import tempfile
import requests
import tarfile
import hashlib


def calculate_md5(file_path, extract_path, chunk_size=8192):
    try:
        with tarfile.open(file_path, "r") as tar:
            tar.extractall(path=extract_path)

        md5 = hashlib.md5()
        for root, _, files in os.walk(extract_path):
            for file in sorted(files):
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as f:
                    while chunk := f.read(chunk_size):
                        md5.update(chunk)
    except Exception as e:
        print(f"Failed to calculate MD5 for {file_path}: {e}")
        return None
    return md5.hexdigest()


def get_yandex_disk_hash_contents(directory_path, token):
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {
        "Authorization": f"OAuth {token}",
        "Accept": "application/json",
    }
    params = {
        "path": directory_path,
        "fields": "_embedded.items.name,_embedded.items.path",
        "limit": 10000
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        items = response.json().get("_embedded", {}).get("items", [])
        hash_contents = {}
        for item in items:
            if item["name"].endswith(".hash"):
                hash_url = f"https://cloud-api.yandex.net/v1/disk/resources/download?path={item['path']}"
                hash_response = requests.get(hash_url, headers=headers)
                if hash_response.status_code == 200:
                    download_url = hash_response.json()["href"]
                    content_response = requests.get(download_url)
                    if content_response.status_code == 200:
                        hash_contents[item["name"]] = content_response.text.strip()
        return hash_contents
    else:
        print(f"Failed to get file info for {directory_path} on Yandex.Disk: {response.text}")
        return {}


def create_yandex_disk_directory(directory_path, token):
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {
        "Authorization": f"OAuth {token}",
        "Accept": "application/json",
    }
    params = {
        "path": directory_path,
    }

    requests.put(url, headers=headers, params=params)


def upload_to_yandex_disk(directory, token, yandex_disk_directory):
    create_yandex_disk_directory(yandex_disk_directory, token)

    url_upload = "https://cloud-api.yandex.net/v1/disk/resources/upload"

    headers = {
        "Authorization": f"OAuth {token}",
        "Accept": "application/json",
    }

    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    existing_hashes = get_yandex_disk_hash_contents(yandex_disk_directory, token)

    with tempfile.TemporaryDirectory() as tmpdirname:
        for file_name in files:
            file_path = os.path.join(directory, file_name)
            local_md5 = calculate_md5(file_path, tmpdirname)

            if not local_md5:
                continue

            hash_file_name = f"{file_name}.hash"

            if local_md5 in existing_hashes.values():
                print(f"File {file_name} already exists on Yandex.Disk. Skipping upload.")
                continue

            params = {
                "path": f"{yandex_disk_directory}/{file_name}",
                "overwrite": "true",
            }

            response = requests.get(url_upload, headers=headers, params=params)

            if response.status_code == 200:
                upload_url = response.json()["href"]
                print(f"Starting upload of {file_name} to Yandex.Disk")

                with open(file_path, "rb") as file:
                    upload_response = requests.put(
                        upload_url,
                        headers={"Content-Type": "application/octet-stream"},
                        data=iter(lambda: file.read(4096), b''),
                        stream=True
                    )

                    if upload_response.status_code == 201:
                        print(f"Uploaded {file_name} to Yandex.Disk")
                    else:
                        print(f"Failed to upload {file_name} to Yandex.Disk: {upload_response.text}")
            else:
                print(f"Failed to get upload URL for {file_name}: {response.text}")

            params_hash = {
                "path": f"{yandex_disk_directory}/{hash_file_name}",
                "overwrite": "true",
            }

            response_hash = requests.get(url_upload, headers=headers, params=params_hash)

            if response_hash.status_code == 200:
                upload_url_hash = response_hash.json()["href"]
                print(f"Starting upload of {hash_file_name} to Yandex.Disk")

                upload_response_hash = requests.put(
                    upload_url_hash,
                    headers={"Content-Type": "application/octet-stream"},
                    data=local_md5.encode(),
                    stream=True
                )

                if upload_response_hash.status_code == 201:
                    print(f"Uploaded {hash_file_name} to Yandex.Disk")
                else:
                    print(f"Failed to upload {hash_file_name} to Yandex.Disk: {upload_response_hash.text}")
            else:
                print(f"Failed to get upload URL for {hash_file_name}: {response_hash.text}")
