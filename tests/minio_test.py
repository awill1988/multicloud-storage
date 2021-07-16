import random
import string
import unittest
from io import BytesIO
from json import dumps
from os import SEEK_END
from typing import Tuple

from multicloud_storage import StorageException, S3, Storage


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


class S3Test(unittest.TestCase):
    """
    StorageTest.
    The client code should be able to work with any pre-configured abstraction-
    implementation combination.
    """

    minio: S3 = S3()
    storage: Storage = Storage(minio)
    bucket_name: str = random_str()
    object_name: str = random_str()
    object_data = {"test": "test"}

    @classmethod
    def tearDownClass(cls):
        try:
            cls.storage.remove_bucket(cls.bucket_name)
        except:  # pylint: disable=bare-except
            pass

    @classmethod
    def setUpClass(cls) -> None:
        cls.storage.make_bucket(cls.bucket_name)

    def setUp(self) -> None:
        self.temp_bucket_name = random_str()

    def tearDown(self) -> None:
        try:
            self.storage.remove_bucket(self.temp_bucket_name)
        except:  # pylint: disable=bare-except
            pass
        try:
            self.storage.delete_object(self.bucket_name, self.object_name)
        except:  # pylint: disable=bare-except
            pass

    def test_is_abstract(self):
        self.assertEqual(Storage, type(self.storage))
        self.assertNotEqual(Storage, type(self.minio))

    def test_bucket_exists(self):
        """
        Asserts that buckets exist.
        """
        self.assertFalse(self.storage.bucket_exists(self.temp_bucket_name))
        self.storage.make_bucket(self.temp_bucket_name)
        self.assertTrue(self.storage.bucket_exists(self.temp_bucket_name))
        self.storage.remove_bucket(self.temp_bucket_name)

    def test_make_bucket(self):
        """
        Asserts buckets can be made.
        """
        self.storage.make_bucket(self.temp_bucket_name)
        self.assertRaises(
            StorageException, self.storage.make_bucket, self.temp_bucket_name
        )

    def test_remove_bucket(self):
        """
        Asserts buckets can be deleted.
        """
        if not self.storage.bucket_exists(self.bucket_name):
            self.storage.make_bucket(self.bucket_name)
        self.storage.remove_bucket(self.bucket_name)

    def test_delete_object(self):
        """
        Asserts objects can be deleted.
        """
        data, size = str_buffer(self.object_data)
        self.storage.put_object(self.bucket_name, self.object_name, data, size)
        self.assertTrue(
            self.storage.object_exists(self.bucket_name, self.object_name)
        )
        self.storage.delete_object(self.bucket_name, self.object_name)
        self.assertFalse(
            self.storage.object_exists(self.bucket_name, self.object_name)
        )

    def test_put_object(self):
        """
        Asserts objects can be written.
        """
        data, size = str_buffer(self.object_data)
        self.storage.put_object(self.bucket_name, self.object_name, data, size)
        self.assertTrue(
            self.storage.object_exists(self.bucket_name, self.object_name)
        )

    def test_object_exists(self):
        """
        Asserts object existence can be determined.
        """
        self.assertFalse(
            self.storage.object_exists(self.bucket_name, self.object_name)
        )
        data, size = str_buffer(self.object_data)
        self.storage.put_object(self.bucket_name, self.object_name, data, size)
        self.assertTrue(
            self.storage.object_exists(self.bucket_name, self.object_name)
        )

    def test_put_object_presigned_url(self):
        """
        Asserts presigned urls can be generated for put requests.
        """
        url = self.storage.get_presigned_url(
            self.bucket_name, self.object_name, method="PUT"
        )
        self.assertIn(self.object_name, url)

    def test_get_presigned_url(self):
        """
        Asserts presigned urls can be generated for get requests.
        """
        url = self.storage.get_presigned_url(
            self.bucket_name, self.object_name, method="GET"
        )
        self.assertIn(self.object_name, url)
        hostname = random_str()
        url = self.storage.get_presigned_url(
            self.bucket_name,
            self.object_name,
            method="GET",
            use_hostname=hostname,
        )
        self.assertIn(hostname, url)
