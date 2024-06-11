from django.contrib import admin
from .models import Owner, Member, Rule

@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'full_name', 'role', 'fonction')
    search_fields = ('username', 'email', 'full_name')

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'full_name', 'role', 'fonction', 'owner')
    search_fields = ('username', 'email', 'full_name')

@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'tag')
    search_fields = ('name', 'tag')
