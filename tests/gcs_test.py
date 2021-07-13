import random
import string
from typing import Tuple
import unittest
from io import BytesIO
from json import dumps
from os import SEEK_END
from multicloud_storage import StorageException, GCS, Storage


def random_str() -> str:
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(10))


def str_buffer(json_object: object) -> Tuple[BytesIO, int]:
    data = BytesIO()
    data.write(dumps(json_object).encode())
    data.seek(0, SEEK_END)
    num_bytes = data.tell()
    data.seek(0)
    return data, num_bytes


class GCSTest(unittest.TestCase):
    """
    GCSTest.
    The client code should be able to work with any pre-configured abstraction-
    implementation combination.
    """

    @classmethod
    def tearDownClass(cls):
        if cls.storage.bucket_exists(cls.bucket_name):
            cls.storage.remove_bucket(cls.bucket_name)

    @classmethod
    def setUpClass(cls):
        cls.gcs = GCS()
        cls.storage = Storage(cls.gcs)
        cls.bucket_name = random_str()
        cls.object_name = random_str()
        cls.object_data = {"test": "test"}

    def test_is_abstract(self):
        self.assertEqual(Storage, type(self.storage))
        self.assertNotEqual(Storage, type(self.gcs))

    def test_bucket_exists(self):
        bucket = random_str()
        self.assertFalse(self.storage.bucket_exists(bucket))
        self.storage.make_bucket(bucket)
        self.assertTrue(self.storage.bucket_exists(bucket))
        self.storage.remove_bucket(bucket)

    def test_make_bucket(self):
        if self.storage.bucket_exists(self.bucket_name):
            self.storage.remove_bucket(self.bucket_name)

        self.storage.make_bucket(self.bucket_name)

    def test_make_bucket_raises_exception_when_exists(self):
        if not self.storage.bucket_exists(self.bucket_name):
            self.storage.make_bucket(self.bucket_name)

        self.assertRaises(
            StorageException, self.storage.make_bucket, self.bucket_name
        )

    def test_remove_bucket(self):
        if not self.storage.bucket_exists(self.bucket_name):
            self.storage.make_bucket(self.bucket_name)

        self.storage.remove_bucket(self.bucket_name)

    def test_object_exists(self):
        if not self.storage.bucket_exists(self.bucket_name):
            self.storage.make_bucket(self.bucket_name)
        self.assertFalse(
            self.storage.object_exists(self.bucket_name, self.object_name)
        )

    def test_put_object_presigned_url(self):
        if not self.storage.bucket_exists(self.bucket_name):
            self.storage.make_bucket(self.bucket_name)
        self.storage.get_presigned_url(
            self.bucket_name, self.object_name, method="PUT"
        )

    def test_get_presigned_url(self):
        if not self.storage.bucket_exists(self.bucket_name):
            self.storage.make_bucket(self.bucket_name)
        self.storage.get_presigned_url(
            self.bucket_name, self.object_name, method="GET"
        )
