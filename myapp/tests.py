from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient

from myapp.models import LinkCollection, Link


# Create your tests here.
class MyappTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        login_user1 = User.objects.create_user(
            username='user 1',
            password='password1!'
        )
        login_user2 = User.objects.create_user(
            username='user 2',
            password='password2!'
        )

        cls.main_page_url = '/api/link-collections/owned-or-all/'
        cls.collection_page_url = '/api/link-collections/'

        for i in range(1, 6):
            collection = LinkCollection.objects.create(
                title=f'Test Link Collection #{i}',
                owner=login_user1,
                description=f'This is a test link collection #{i}.',
                is_public=False,
            )
            link = Link.objects.create(
                title=f'Test Link #1',
                url='https://www.example.com',
                description='This is a test link #1.',
                collection=collection
            )

        for i in range(6, 11):
            collection = LinkCollection.objects.create(
                title=f'Test Collection #{i}',
                owner=login_user2,
                description=f'This is a test collection #{i}.',
                is_public=True,
            )
            link = Link.objects.create(
                title=f'Test Link #1',
                url='https://www.example.com',
                description='This is a test link #1.',
                collection=collection
            )

    def setUp(self):
        self.user1 = User.objects.get(username='user 1')
        self.user2 = User.objects.get(username='user 2')
        self.user3 = User.objects.create_user(
            username='user 3',
            password='password3!'
        )
        self.user4 = User.objects.create_user(
            username='user 4',
            password='password4!'
        )
        self.user5 = User.objects.create_user(
            username='user 5',
            password='password5!'
        )

    def test_main_page_unauthorized_user(self):
        response = self.client.get(self.main_page_url, format='json')

        # 요청이 보내지는지 확인
        self.assertEqual(response.status_code, 200)

        data = response.data['results']
        # 요청 결과가 뭐든 반환되긴 하는지
        self.assertIsNotNone(data)

        # 요청 결과가 5개인지 확인
        self.assertEqual(len(data), 5)

        for d in data:
            self.assertEqual(d['owner']['username'], 'user 2')
            self.assertEqual(d['is_public'], True)

    def test_main_page_authorized_user(self):
        self.client.force_authenticate(self.user1)

        # 쿼리 최적화 전 43개 쿼리 발생
        # 쿼리 최적화 이후 6개 쿼리 발생
        # 43 >> 6으로 약 7분의 1로 감소하였으며, N + 1 문제 없이 상수 값으로 고정됨
        with self.assertNumQueries(6):
            response = self.client.get(self.main_page_url, format='json')

        # 요청이 보내지는지 확인
        self.assertEqual(response.status_code, 200)

        data = response.data['results']
        # 요청 결과가 뭐든 반환되긴 하는지
        self.assertIsNotNone(data)
        # print(f'data 1: {data[0]}')

        # 요청 결과가 10개인지 확인
        self.assertEqual(len(data), 10)

        private_count = 0
        public_count = 0

        for d in data:
            if d['is_public']:
                public_count += 1
            else:
                private_count += 1

        self.assertEqual(public_count, 5)
        self.assertEqual(private_count, 5)

    def test_collection_page_unauthorized_user(self):
        response = self.client.get(self.collection_page_url, format='json')

        self.assertEqual(response.status_code, 403)

    def test_collection_page_authorized_user(self):
        self.client.force_authenticate(self.user1)
        response = self.client.get(self.collection_page_url, format='json')

        self.assertEqual(response.status_code, 200)

        data = response.data
        self.assertIsNotNone(data)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 5)

    def test_collection_like_unauthorized_user(self):
        private_collection = LinkCollection.objects.get(pk=1)
        public_collection = LinkCollection.objects.get(pk=6)
        private_collection_like_url = f'/api/link-collections/{private_collection.id}/toggle-like/'
        public_collection_like_url = f'/api/link-collections/{public_collection.id}/toggle-like/'

        private_response = self.client.post(private_collection_like_url)
        self.assertEqual(private_response.status_code, 403)

        public_response = self.client.post(public_collection_like_url)
        self.assertEqual(public_response.status_code, 403)

    def test_collection_like_authorized_user(self):
        self.client.force_authenticate(self.user1)
        private_collection = LinkCollection.objects.get(pk=1)
        public_collection = LinkCollection.objects.get(pk=6)
        private_collection_like_url = f'/api/link-collections/{private_collection.id}/toggle-like/'
        public_collection_like_url = f'/api/link-collections/{public_collection.id}/toggle-like/'
        # 본인은 본인 링크 모음에 좋아요 누를 수 없음
        private_response = self.client.post(private_collection_like_url)
        self.assertEqual(private_response.status_code, 403)

        # 좋아요 누르기
        public_response = self.client.post(public_collection_like_url)
        self.assertEqual(public_response.status_code, 200)
        self.assertEqual(public_response.data['message'], "Like created.")
        # 두 번 누르면 좋아요 취소
        public_response = self.client.post(public_collection_like_url)
        self.assertEqual(public_response.status_code, 200)
        self.assertEqual(public_response.data['message'], "Like deleted.")

        self.client.logout()

        # 비공개 링크 모음 좋아요 테스트
        self.client.force_authenticate(self.user2)
        # 비공개 링크 모음에는 좋아요 누를 수 없음
        private_response = self.client.post(private_collection_like_url)
        self.assertEqual(private_response.status_code, 403)

        # 본인은 본인 링크 모음에 좋아요 누를 수 없음
        public_response = self.client.post(public_collection_like_url)
        self.assertEqual(public_response.status_code, 403)

    def test_collection_like_count(self):
        collection1 = LinkCollection.objects.get(pk=6)
        collection2 = LinkCollection.objects.get(pk=7)
        collection3 = LinkCollection.objects.get(pk=8)
        collection4 = LinkCollection.objects.get(pk=9)
        collection5 = LinkCollection.objects.get(pk=10)

        collection1_like_url = f'/api/link-collections/{collection1.id}/toggle-like/'
        collection2_like_url = f'/api/link-collections/{collection2.id}/toggle-like/'
        collection3_like_url = f'/api/link-collections/{collection3.id}/toggle-like/'
        collection4_like_url = f'/api/link-collections/{collection4.id}/toggle-like/'
        collection5_like_url = f'/api/link-collections/{collection5.id}/toggle-like/'

        # 3 - 2 - 4 - 5 - 1 순서로 좋아요 개수가 줄어듦 (4개 - 3개 - 2개 - 1개 - 0개)
        for i in range(4, 0, -1):
            num = i

            while num > 0:
                if num == i:
                    self.client.force_authenticate(self.user1)
                elif num == i - 1:
                    self.client.force_authenticate(self.user3)
                elif num == i - 2:
                    self.client.force_authenticate(self.user4)
                else:
                    self.client.force_authenticate(self.user5)

                if i == 4:
                    self.client.post(collection3_like_url)
                elif i == 3:
                    self.client.post(collection2_like_url)
                elif i == 2:
                    self.client.post(collection4_like_url)
                else:
                    self.client.post(collection5_like_url)

                num -= 1
                self.client.logout()

        # 예상 반환 결과 - (#8, #7, #9, #10, #6)
        # total_likes - (4개, 3개, 2개, 1개, 0개)
        response = self.client.get(self.main_page_url, format='json')
        self.assertEqual(response.status_code, 200)

        data = response.data['results']
        self.assertIsNotNone(data)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 5)

        for i in range(5):
            self.assertEqual(data[i]['total_likes'], 4 - i)
