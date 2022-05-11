import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Follow, Group, Post, User

from ..forms import PostForm

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='Auth_user')
        cls.user_follower = User.objects.create_user(username='Follower')
        cls.group = Group.objects.create(
            title='test_group_1',
            slug='test_slug_1',
            description='test_description_1',
        )
        cls.group_test = Group.objects.create(
            title='test_group_2',
            slug='test_slug_2',
            description='test_description_2'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='test_post',
            image=cls.uploaded
        )
        cls.templates_urls = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': cls.user.username}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': cls.post.id}):
                'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': cls.post.id}):
                'posts/post_create.html',
            reverse('posts:post_create'): 'posts/post_create.html',
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_follower = Client(self.user_follower)
        self.authorized_client_follower.force_login(self.user_follower)

    def post_check(self, post):
        self.assertEqual(post.id, self.post.id)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.post.group)
        self.assertEqual(post.image, self.post.image)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for url, template in self.templates_urls.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_home_page_correct_context(self):
        """Шаблон главной страницы сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.post_check(response.context['page_obj'][0])

    def test_group_list_page_correct_context(self):
        """Проверка списка постов отфильтрованных по группе."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.post_check(response.context['page_obj'][0])
        self.assertEqual(response.context["group"], self.group)

    def test_profile_page_correct_context(self):
        """Проверка списка постов отфильтрованных по пользователю."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        self.post_check(response.context['page_obj'][0])
        self.assertEqual(self.user, response.context["author"])

    def test_group_list_page_id_correct_context(self):
        """Проверка одного поста отфильтрованного по id."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(
            response.context.get('post').author.posts.count(),
            len(self.user.posts.select_related('author')))
        self.assertTrue(response.context['post'].image)
        self.assertEqual(response.context.get('post').author, self.user)

    def test_creat_page_correct_context(self):
        """Шаблон создания поста с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'group': forms.models.ChoiceField,
            'text': forms.fields.CharField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                self.assertIsInstance(
                    response.context['form'].fields[value], expected)

    def test_post_edit_show_correct_context(self):
        """Шаблон редактирования поста сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'group': forms.fields.ChoiceField,
            'text': forms.fields.CharField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                self.assertIsInstance(
                    response.context['form'].fields[value], expected)
        self.assertIsInstance(response.context.get('form'), PostForm)

    def test_new_post_create_appears_on_correct_pages(self):
        """При создании поста он должен появляется на главной странице,
        на странице выбранной группы и в профиле пользователя."""
        pages = [
            reverse('posts:index'),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.user.username})
        ]
        for urls in pages:
            with self.subTest(urls=urls):
                response = self.authorized_client.get(urls)
                self.assertIn(self.post, response.context['page_obj'])

    def test_post_in_the_right_group(self):
        """Проверяем что пост не попал в другую группу."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test_slug_2'}))
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_follow(self):
        """Проверка: авторизованный пользователь может подписаться
        на другого пользователя.
        """
        follow_count = Follow.objects.count()
        self.authorized_client_follower.get(
            reverse('posts:profile_follow', kwargs={'username': self.user})
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertTrue(
            Follow.objects.filter(
                user=self.user_follower,
                author=self.user
            ).exists()
        )

    def test_unfollow(self):
        """Проверка: авторизованный пользователь может отписаться
        на другого пользователя.
        """
        self.authorized_client_follower.get(
            reverse('posts:profile_follow', kwargs={'username': self.user})
        )
        follow_count = Follow.objects.count()
        self.authorized_client_follower.get(
            reverse('posts:profile_unfollow', kwargs={'username': self.user})
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)
        self.assertFalse(
            Follow.objects.filter(
                user=self.user_follower,
                author=self.user
            ).exists()
        )

    def test_follow_page_if_follower(self):
        """Проверка на наличие нового поста в ленте подписок,
        если пользователь подписан на автора.
        """
        self.authorized_client_follower.get(
            reverse('posts:profile_follow', kwargs={'username': self.user})
        )
        post = Post.objects.create(
            text="test_post",
            author=self.user
        )
        response = self.authorized_client_follower.get(reverse(
            'posts:follow_index')
        )
        object = response.context['page_obj'][0]
        post_text = object.text
        post_author = object.author
        self.assertEqual(post_text, post.text)
        self.assertEqual(post_author, self.user)

    def test_follow_page_if_not_follower(self):
        """Проверка на отсутствие нового поста в ленте подписок,
        если пользователь не подписан на автора.
        """
        Post.objects.create(
            text="test_post",
            author=self.user
        )
        response = self.authorized_client_follower.get(reverse(
            'posts:follow_index')
        )
        self.assertEqual(len(response.context['page_obj']), 0)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Auth_user')
        cls.group = Group.objects.create(
            title='test_group',
            slug='test_slug',
            description='test_description',
        )
        cls.posts = []
        for test_post in range(13):
            cls.posts.append(Post(
                author=cls.user,
                text=f'{test_post}',
                group=cls.group)
            )
        Post.objects.bulk_create(cls.posts)
        cls.templates = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}),
            reverse('posts:profile', kwargs={'username': cls.user.username})
        ]
        cls.templates2 = [
            reverse('posts:index') + '?page=2',
            reverse('posts:group_list', kwargs={'slug': cls.group.slug})
            + '?page=2',
            reverse('posts:profile', kwargs={'username': cls.user.username})
            + '?page=2'
        ]

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page_has_ten_posts(self):
        """Проверяет, что на первой странице 10 постов."""
        for page in self.templates:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']), settings.POSTS_PER_PAGE
                )

    def test_rests_of_the_posts_next_page(self):
        """Проверяет, что на второй странице 3 поста."""
        for page in self.templates2:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']),
                    settings.POSTS_PER_PAGE_2
                )


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest = Client()
        cls.user = User.objects.create_user(username='Test_cache')
        cls.post = Post.objects.create(
            text='Test_cache',
            author=cls.user)

    def test_index_page_is_cached(self):
        """Проверяем кэшируется ли главная страница."""
        first_response = CacheTests.guest.get(reverse('posts:index'))
        CacheTests.post.delete()
        second_response = CacheTests.guest.get(reverse('posts:index'))
        cache.clear()
        third_response = CacheTests.guest.get(reverse('posts:index'))
        self.assertEqual(first_response.content,
                         second_response.content)
        self.assertNotEqual(first_response.content,
                            third_response.content)
