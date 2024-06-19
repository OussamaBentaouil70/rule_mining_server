from django.urls import path
from myapp.views import *

urlpatterns = [
    path('create_member/', create_member_by_owner, name='create_member_by_owner'),
    path('members/<int:user_id>/', update_member_by_owner, name='update_member_by_owner'),
    path('delete_member/<int:user_id>/', delete_member_by_owner, name='delete_member_by_owner'),
    path('get_members/', list_members_by_owner, name='list_members_by_owner'),
    path('member/<int:member_id>/', get_member_by_id, name='get_member_by_id'),
    path('rules_by_tag/', get_rules_by_tag, name='rules_by_tag'),
    path('delete_rules/', delete_rule, name='delete_rules'),
    path('register/', register_user, name='register'),
    path('login/', login_user, name='login'),
    path('profile/', get_profile, name='profile'),
    path('logout/', logout, name='logout'),
    path('update_profile/', update_profile, name='update_user_profile'),
    path('get_rules/', get_rules_from_mongodb_by_tag, name='get_rules_from_mongodb_by_tag'),
    path('edit_rule/<str:rule_id>/', edit_rule_by_id, name='edit_rule_in_mongodb_by_id'),
    path('add_rule/', add_rule, name='add_rule'),
    path('delete_rule/<str:rule_id>/', delete_rule, name='delete_rule'),
]
