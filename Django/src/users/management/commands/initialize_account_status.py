"""Provision existing database accounts before application services start."""
from uuid import uuid4

from django.core.management.base import BaseCommand

from users.models import UserModel
from utils.auth_status import status_key
from utils import refresh_tokens


class Command(BaseCommand):
    help = 'Enable existing accounts without overwriting any stored account status.'

    def handle(self, *args, **options):
        redis = refresh_tokens.get_redis()
        created = 0
        for user_id in UserModel.objects.values_list('pk', flat=True).iterator():
            created += bool(redis.set(status_key(user_id), 'enabled:' + str(uuid4()), nx=True))
        self.stdout.write(self.style.SUCCESS(f'Initialized {created} account status entries.'))
