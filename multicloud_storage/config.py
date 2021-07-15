from os import getenv, getcwd, path
from typing import Dict
from dotenv import load_dotenv

env_dirname = path.realpath(getcwd())
load_dotenv(path.join(env_dirname, ".env"))


def config() -> Dict:
    return {
        "STORAGE_EMULATOR_HOST": getenv("STORAGE_EMULATOR_HOST", default=None),
        "GOOGLE_CLOUD_PROJECT": getenv("GOOGLE_CLOUD_PROJECT", default=None),
        "GOOGLE_APPLICATION_CREDENTIALS": getenv(
            "GOOGLE_APPLICATION_CREDENTIALS", default=None
        ),
        "AWS_ACCESS_KEY_ID": getenv("AWS_ACCESS_KEY_ID", default=None),
        "AWS_SECRET_ACCESS_KEY": getenv("AWS_SECRET_ACCESS_KEY", default=None),
        "AWS_SESSION_TOKEN": getenv("AWS_SESSION_TOKEN", default=None),
        "AWS_REGION": getenv("AWS_REGION", default=None),
        "S3_ENDPOINT": getenv("S3_ENDPOINT", default=None),
        "STORAGE_EXTERNAL_HOSTNAME": getenv(
            "STORAGE_EXTERNAL_HOSTNAME", default=None
        ),
    }
