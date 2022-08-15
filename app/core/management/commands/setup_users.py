from django.contrib.auth.models import User
from django.core.management import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        User.objects.create_user('ericp', email='user1@kpkapp.biz', password='ericp123', first_name='Eric', last_name='Phillips')
        # User.objects.create_user('', email='user2@kpkapp.biz', password='', first_name='', last_name='')
        User.objects.create_user('saeeda', email='user3@kpkapp.biz', password='saeeda123', first_name='Saeed', last_name='Abdus-Salaam')
        User.objects.create_user('marqp', email='user4@kpkapp.biz', password='marqp123', first_name='Marquett', last_name='Phillips')
        # User.objects.create_user('', email='user5@kpkapp.biz', password='', first_name='', last_name='')
        User.objects.create_user('gradyw', email='user6@kpkapp.biz', password='gradyw123', first_name='Grady', last_name='Wingfield')
        User.objects.create_user('joecjr', email='user7@kpkapp.biz', password='joecjr123', first_name='Joe', last_name='Calhoun_Jr')
        User.objects.create_user('joey', email='user8@kpkapp.biz', password='joeyb123', first_name='Joey', last_name='Blankenship')
        # User.objects.create_user('', email='user9@kpkapp.biz', password='', first_name='', last_name='')
        # User.objects.create_user('', email='user10@kpkapp.biz', password='', first_name='', last_name='')
        # User.objects.create_user('', email='user11@kpkapp.biz', password='', first_name='', last_name='')
        # User.objects.create_user('', email='user12@kpkapp.biz', password='', first_name='', last_name='')
        # User.objects.create_user('', email='user13@kpkapp.biz', password='', first_name='', last_name='')
        # User.objects.create_user('', email='user14@kpkapp.biz', password='', first_name='', last_name='')
        # User.objects.create_user('', email='user15@kpkapp.biz', password='', first_name='', last_name='')
        # User.objects.create_user('', email='user16@kpkapp.biz', password='', first_name='', last_name='')
        # User.objects.create_user('', email='user17@kpkapp.biz', password='', first_name='', last_name='')
        # User.objects.create_user('', email='user18@kpkapp.biz', password='', first_name='', last_name='')
        # User.objects.create_user('', email='user19@kpkapp.biz', password='', first_name='', last_name='')
        # User.objects.create_user('', email='user20@kpkapp.biz', password='', first_name='', last_name='')

