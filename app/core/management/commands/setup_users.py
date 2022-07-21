from django.contrib.auth.models import User
from django.core.management import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        User.objects.create_user('ephillips', email='user1@kpkapp.biz', first_name='Eric', last_name='Phillips')
        User.objects.create_user('wbeachman', email='user2@kpkapp.biz', first_name='Willie', last_name='Beachman')
        User.objects.create_user('sabdus', email='user3@kpkapp.biz', first_name='Saeed', last_name='Abdus-Salaam')
        User.objects.create_user('mphillips', email='user4@kpkapp.biz', first_name='Marquett', last_name='Phillips')
        User.objects.create_user('gwingfield', email='user6@kpkapp.biz', first_name='Grady', last_name='Wingfield')
        User.objects.create_user('jcalhounjr', email='user7@kpkapp.biz', first_name='Joe', last_name='Calhoun_Jr')
        User.objects.create_user('jblankenship', email='user8@kpkapp.biz', first_name='Joey', last_name='Blankenship')
        # User.objects.create_user('', email='user9@kpkapp.biz', first_name='', last_name='')
        # User.objects.create_user('', email='user10@kpkapp.biz', first_name='', last_name='')
        # User.objects.create_user('', email='user11@kpkapp.biz', first_name='', last_name='')
        # User.objects.create_user('', email='user12@kpkapp.biz', first_name='', last_name='')
        # User.objects.create_user('', email='user13@kpkapp.biz', first_name='', last_name='')
        # User.objects.create_user('', email='user14@kpkapp.biz', first_name='', last_name='')
        # User.objects.create_user('', email='user15@kpkapp.biz', first_name='', last_name='')
        # User.objects.create_user('', email='user16@kpkapp.biz', first_name='', last_name='')
        # User.objects.create_user('', email='user17@kpkapp.biz', first_name='', last_name='')
        # User.objects.create_user('', email='user18@kpkapp.biz', first_name='', last_name='')
        # User.objects.create_user('', email='user19@kpkapp.biz', first_name='', last_name='')
        # User.objects.create_user('', email='user20@kpkapp.biz', first_name='', last_name='')

