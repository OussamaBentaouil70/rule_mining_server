from django.urls import path
from myapp.views import create_member_by_owner, delete_rule, get_profile, get_rules_by_tag, login_user, register_user, update_member_by_owner, delete_member_by_owner, list_members_by_owner, get_member_by_id

urlpatterns = [
    path('members/', create_member_by_owner, name='create_member_by_owner'),
    path('members/<int:user_id>/', update_member_by_owner, name='update_member_by_owner'),
    path('members/<int:user_id>/', delete_member_by_owner, name='delete_member_by_owner'),
    path('members/', list_members_by_owner, name='list_members_by_owner'),
    path('members/<int:member_id>/', get_member_by_id, name='get_member_by_id'),
    path('rules_by_tag/', get_rules_by_tag, name='rules_by_tag'),
    path('delete_rules/', delete_rule, name='delete_rules'),
    path('register/', register_user, name='register'),
    path('login/', login_user, name='login'),
    path('profile/', get_profile, name='profile'),
    path('logout/', login_user, name='logout'),
]
