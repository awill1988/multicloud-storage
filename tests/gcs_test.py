from datetime import datetime
from multicloud_storage.object import last_modified, name
import random
import string
import unittest
from hashlib import md5
from io import BytesIO
from json import dumps, loads
from os import SEEK_END
from typing import Tuple

from multicloud_storage import GCS, Storage, StorageException
from multicloud_storage.http import HttpMethod


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


def calc_checksum(data: BytesIO) -> str:
    md5_hash = md5(data.read().strip())
    return md5_hash.hexdigest()


class GCSTest(unittest.TestCase):
    """
    GCSTest.
    The client code should be able to work with any pre-configured abstraction-
    implementation combination.
    """

    gcs = GCS()
    storage: Storage = Storage(gcs)
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
        try:
            self.storage.make_bucket(self.bucket_name)
        except:  # pylint: disable=bare-except
            pass

    def tearDown(self) -> None:
        try:
            self.storage.remove_bucket(self.temp_bucket_name)
        except:  # pylint: disable=bare-except
            pass
        try:
            self.storage.delete_object(self.bucket_name, self.object_name)
        except:  # pylint: disable=bare-except
            pass

    def test_configurable_project(self):
        self.assertEqual(self.gcs._project(), "localstack")
        different_client = Storage(GCS("other_project"))
        self.assertEqual(different_client._client._project(), "other_project")
        self.assertEqual(self.gcs._project(), "localstack")

    def test_is_abstract(self):
        self.assertEqual(Storage, type(self.storage))
        self.assertNotEqual(Storage, type(self.gcs))

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
        self.assertRaises(
            StorageException,
            self.storage.get_presigned_url,
            self.bucket_name,
            self.object_name,
            method=HttpMethod.GET,
        )
        data, size = str_buffer(self.object_data)
        self.storage.put_object(self.bucket_name, self.object_name, data, size)
        hostname = random_str()
        url = self.storage.get_presigned_url(
            self.bucket_name,
            self.object_name,
            method=HttpMethod.GET,
            use_hostname=hostname,
        )
        self.assertIn(hostname, url)
        self.assertIn(self.object_name, url)

    def test_get_object(self):
        """
        Asserts an object can be retrieved from the storage implementation.
        """
        data, size = str_buffer(self.object_data)
        self.storage.put_object(self.bucket_name, self.object_name, data, size)
        data = self.storage.get_object(self.bucket_name, self.object_name)
        self.assertEqual(self.object_data, loads(data.read().decode("utf-8")))

    def test_copy_object(self):
        """
        Asserts an object can be copied from one place to another.
        """
        data, size = str_buffer(self.object_data)
        self.storage.put_object(self.bucket_name, self.object_name, data, size)
        new_object_name = random_str()
        self.storage.copy_object(
            self.bucket_name,
            self.object_name,
            self.bucket_name,
            new_object_name,
        )
        self.assertTrue(
            self.storage.object_exists(self.bucket_name, new_object_name)
        )
        new_data = self.storage.get_object(self.bucket_name, new_object_name)
        data.seek(0)
        self.assertEqual(new_data.read(), data.read())
        self.storage.delete_object(self.bucket_name, new_object_name)

    def test_rename_object(self):
        """
        Asserts an object can be renamed.
        """
        data, size = str_buffer(self.object_data)
        self.storage.put_object(self.bucket_name, self.object_name, data, size)
        new_object_name = random_str()
        self.storage.rename_object(
            self.bucket_name, self.object_name, new_object_name
        )
        self.assertFalse(
            self.storage.object_exists(self.bucket_name, self.object_name)
        )
        self.assertTrue(
            self.storage.object_exists(self.bucket_name, new_object_name)
        )

    def test_md5_hash(self):
        """
        Asserts it is possible to retrieve an md5 hash.
        """
        data, size = str_buffer(self.object_data)
        self.storage.put_object(self.bucket_name, self.object_name, data, size)
        checksum = self.storage.md5_checksum(
            self.bucket_name, self.object_name
        )
        self.assertGreater(len(checksum), 0)
        data.seek(0)
        self.assertEqual(calc_checksum(data), checksum)

    def test_list_objects(self):
        """
        Asserts it is possible to list objects.
        """
        data, size = str_buffer(self.object_data)
        self.storage.put_object(self.bucket_name, self.object_name, data, size)
        objects = self.storage.list_objects(self.bucket_name)
        retrieved_object = next(objects)
        self.assertEqual(len(str(self.object_data)), retrieved_object.size)
        self.assertNotEqual(None, last_modified(retrieved_object))
        self.assertEqual(self.object_name, name(retrieved_object))

    def test_concat_objects(self):
        """
        Asserts it is possible to concat objects.
        """
        second_object_name = random_str()
        data, size = str_buffer(self.object_data)
        self.storage.put_object(self.bucket_name, self.object_name, data, size)
        data.seek(0)
        self.storage.put_object(
            self.bucket_name, second_object_name, data, size
        )
        self.storage.concat_objects(
            self.bucket_name,
            self.object_name,
            [self.object_name, second_object_name],
        )
        self.storage.delete_object(self.bucket_name, second_object_name)

        self.storage.get_object(self.bucket_name, self.object_name)
        data = self.storage.get_object(self.bucket_name, self.object_name)
        self.assertEqual(
            data.read().decode("utf-8"),
            dumps(self.object_data) + dumps(self.object_data),
        )
