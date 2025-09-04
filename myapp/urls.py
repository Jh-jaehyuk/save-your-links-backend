from django.urls import path
from rest_framework.routers import DefaultRouter

from myapp.views import LinkCollectionView, LinkView, UserView, kakao_login, \
    get_kakao_redirect_uri, kakao_logout, get_kakao_logout_redirect_uri

router = DefaultRouter()
router.register(r'link-collections', LinkCollectionView, basename='link-collections')
router.register(r'links', LinkView, basename='links')
router.register(r'users', UserView, basename='users')

urlpatterns = [
    path('auth/kakao-redirect-uri/', get_kakao_redirect_uri, name='kakao-redirect-uri'),
    path('auth/kakao-login/', kakao_login, name='kakao-login'),
    path('auth/kakao-logout-redirect-uri/', get_kakao_logout_redirect_uri, name='kakao-logout-redirect-uri'),
    path('auth/kakao-logout/', kakao_logout, name='kakao-logout'),
]
urlpatterns += router.urls
