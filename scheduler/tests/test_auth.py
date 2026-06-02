from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(APP_PASSWORD='secret123')
class AuthTests(TestCase):
    def test_protected_page_redirects_to_login_when_anonymous(self):
        resp = self.client.get(reverse('schedule'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('login'), resp['Location'])

    def test_login_page_is_accessible_without_auth(self):
        resp = self.client.get(reverse('login'))
        self.assertEqual(resp.status_code, 200)

    def test_login_with_wrong_password_shows_error(self):
        resp = self.client.post(reverse('login'), {'password': 'nope'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '비밀번호가 올바르지 않습니다')

    def test_login_with_correct_password_grants_access(self):
        resp = self.client.post(reverse('login'), {'password': 'secret123'})
        self.assertEqual(resp.status_code, 302)
        # 로그인 후 보호 페이지 접근 가능
        resp = self.client.get(reverse('schedule'))
        self.assertEqual(resp.status_code, 200)

    def test_logout_clears_session(self):
        self.client.post(reverse('login'), {'password': 'secret123'})
        self.client.get(reverse('logout'))
        resp = self.client.get(reverse('schedule'))
        self.assertEqual(resp.status_code, 302)
