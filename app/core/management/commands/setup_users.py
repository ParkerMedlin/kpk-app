from django.contrib.auth.models import User
from django.core.management import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        users = [
            {'username' : 'ddavis', 'email' : 'ddavis@kinpakinc.com', 'password' : 'danny1234', 'first_name' : 'Danny', 'last_name' : 'Davis', 'group' : 'front_office'},
            {'username' : 'gbarganier', 'email' : 'gbarganier@kinpakinc.com', 'password' : 'ginny1234', 'first_name' : 'Ginny', 'last_name' : 'Barganier', 'group' : 'front_office'},
            {'username' : 'vwaclawek', 'email' : 'vwaclawek@kinpakinc.com', 'password' : 'vincent123', 'first_name' : 'Vincent', 'last_name' : 'Waclawek', 'group' : 'front_office'},
            {'username' : 'ahale', 'email' : 'ahale@kinpakinc.com', 'password' : 'anthony123', 'first_name' : 'Anthony', 'last_name' : 'Hale', 'group' : 'front_office'},
            {'username' : 'sabdus', 'email' : 'matos.saeed@gmail.com', 'password' : 'saeed123', 'first_name' : 'Saeed', 'last_name' : 'Abdus-Salaam', 'group' : 'blend_crew'},
            {'username' : 'rbanks', 'email' : 'rodneytbanks76@gmail.com', 'password' : 'rodney123', 'first_name' : 'Rodney', 'last_name' : 'Banks', 'group' : 'blend_crew'},
            {'username' : 'ephillips', 'email' : 'ephillips334@gmail.com', 'password' : 'eric1234', 'first_name' : 'Eric', 'last_name' : 'Phillips', 'group' : 'blend_crew'},
            {'username' : 'mphillips', 'email' : 'ttpphillips63@gmail.com', 'password' : 'marquett123', 'first_name' : 'Marquett', 'last_name' : 'Phillips', 'group' : 'blend_crew'},
            {'username' : 'jcalhounsr', 'email' : 'jcalhoun2976@gmail.com', 'password' : 'joesr1234', 'first_name' : 'Joe', 'last_name' : 'Calhoun-Sr', 'group' : 'blend_crew'},
            {'username' : 'jcalhounjr', 'email' : 'calhounjo@yahoo.com', 'password' : 'joejr1234', 'first_name' : 'Joe', 'last_name' : 'Calhoun-Jr', 'group' : 'blend_crew'},
            {'username' : 'khardy', 'email' : 'hardykeith554@gmail.com', 'password' : 'keith123', 'first_name' : 'Keith', 'last_name' : 'Hardy', 'group' : 'blend_crew'},
            {'username' : 'kkeyes', 'email' : 'keyeskevin91@yahoo.com', 'password' : 'kevin123', 'first_name' : 'Kevin', 'last_name' : 'Keyes', 'group' : 'blend_crew'},
            {'username' : 'amccloud', 'email' : 'polokid399@gmail.com', 'password' : 'aaron123', 'first_name' : 'Aaron', 'last_name' : 'McCloud', 'group' : 'blend_crew'},
            {'username' : 'jtyler', 'email' : 'tylerboi32@gmail.com', 'password' : 'jermaine123', 'first_name' : 'Jermaine', 'last_name' : 'Tyler', 'group' : 'blend_crew'},
            {'username' : 'swheeler', 'email' : 'swheeler@kinpakinc.com', 'password' : 'shawn123', 'first_name' : 'Shawn', 'last_name' : 'Wheeler', 'group' : 'blend_crew'},
            {'username' : 'jblankenship', 'email' : 'warehouse@kinpakinc.com', 'password' : 'joey1234', 'first_name' : 'Joey', 'last_name' : 'Blankenship', 'group' : 'forklift_operator'},
            {'username' : 'mchandler', 'email' : '', 'password' : 'morris123', 'first_name' : 'Morris', 'last_name' : 'Chandler', 'group' : 'forklift_operator'},
            {'username' : 'tstone', 'email' : '', 'password' : 'tom12345', 'first_name' : 'Tom', 'last_name' : 'Stone', 'group' : 'forklift_operator'},
            {'username' : 'atodd', 'email' : '', 'password' : 'anthony123', 'first_name' : 'Anthony', 'last_name' : 'Todd', 'group' : 'forklift_operator'},
            {'username' : 'mabrams', 'email' : '', 'password' : 'mike1234', 'first_name' : 'Mike', 'last_name' : 'Abrams', 'group' : 'forklift_operator'},
            {'username' : 'rwilliams', 'email' : '', 'password' : 'renardo123', 'first_name' : 'Renardo', 'last_name' : 'Williams', 'group' : 'forklift_operator'},
            {'username' : 'oglover', 'email' : '', 'password' : 'otis1234', 'first_name' : 'Otis', 'last_name' : 'Glover', 'group' : 'forklift_operator'},
            {'username' : 'vbrown', 'email' : '', 'password' : 'vicki123', 'first_name' : 'Vicki', 'last_name' : 'Brown', 'group' : 'forklift_operator'},
            {'username' : 'cholloway', 'email' : '', 'password' : 'crystal123', 'first_name' : 'Crystal', 'last_name' : 'Holloway', 'group' : 'forklift_operator'},
            {'username' : 'ljackson', 'email' : '', 'password' : 'leo12345', 'first_name' : 'Leo', 'last_name' : 'Jackson', 'group' : 'forklift_operator'},
            {'username' : 'chenderson', 'email' : '', 'password' : 'conita123', 'first_name' : 'Conita', 'last_name' : 'Henderson', 'group' : 'forklift_operator'},
            {'username' : 'etaylor', 'email' : '', 'password' : 'ernest123', 'first_name' : 'Earnest', 'last_name' : 'Taylor', 'group' : 'forklift_operator'},
            {'username' : 'rriddle', 'email' : '', 'password' : 'rodney123', 'first_name' : 'Rodney', 'last_name' : 'Riddle', 'group' : 'forklift_operator'},
            {'username' : 'mcaldwell', 'email' : '', 'password' : 'mack1234', 'first_name' : 'Mack', 'last_name' : 'Caldwell', 'group' : 'forklift_operator'},
            {'username' : 'ewoods', 'email' : '', 'password' : 'ernest123', 'first_name' : 'Ernest', 'last_name' : 'Woods', 'group' : 'forklift_operator'},
            {'username' : 'bbarganier', 'email' : '', 'password' : 'bobby123', 'first_name' : 'Bobby', 'last_name' : 'Barganier', 'group' : 'forklift_operator'},
            {'username' : 'mclark', 'email' : '', 'password' : 'maxie123', 'first_name' : 'Maxie', 'last_name' : 'Clark', 'group' : 'forklift_operator'},
            {'username' : 'karmont', 'email' : '', 'password' : 'kirby123', 'first_name' : 'Kirby', 'last_name' : 'Armont', 'group' : 'forklift_operator'},
            {'username' : 'zmcmannes', 'email' : '', 'password' : 'zach1234', 'first_name' : 'Zach', 'last_name' : 'McMannes', 'group' : 'forklift_operator'},
            {'username' : 'mdavis', 'email' : '', 'password' : 'mark1234', 'first_name' : 'Mark', 'last_name' : 'Davis', 'group' : 'forklift_operator'},
            {'username' : 'rthomas', 'email' : '', 'password' : 'rasari123', 'first_name' : 'Rasari', 'last_name' : 'Thomas', 'group' : 'forklift_operator'},
            {'username' : 'mlockwood', 'email' : '', 'password' : 'mike1234', 'first_name' : 'Mike', 'last_name' : 'Lockwood', 'group' : 'forklift_operator'},
            {'username' : 'cjones', 'email' : '', 'password' : 'charlie123', 'first_name' : 'Charlie', 'last_name' : 'Jones', 'group' : 'forklift_operator'},
            {'username' : 'rburton', 'email' : '', 'password' : 'reginald1234', 'first_name' : 'Reginald', 'last_name' : 'Burton', 'group' : 'forklift_operator'},
            {'username' : 'rcordell', 'email' : '', 'password' : 'randall1234', 'first_name' : 'Randall', 'last_name' : 'Cordell', 'group' : 'forklift_operator'},
            {'username' : 'mdeloach', 'email' : '', 'password' : 'mario1234', 'first_name' : 'Mario', 'last_name' : 'Deloach', 'group' : 'forklift_operator'},
            {'username' : 'jchandler', 'email' : '', 'password' : 'joe1234', 'first_name' : 'Joe', 'last_name' : 'Chandler', 'group' : 'forklift_operator'},
            {'username' : 'jboutwell-sr', 'email' : '', 'password' : 'jamie1234', 'first_name' : 'Jamie', 'last_name' : 'Boutwell-Sr', 'group' : 'forklift_operator'},
            {'username' : 'jboutwell-jr', 'email' : '', 'password' : 'jamie1234', 'first_name' : 'Jamie', 'last_name' : 'Boutwell-Jr', 'group' : 'forklift_operator'},
            {'username' : 'mabbruscato', 'email' : '', 'password' : 'michael1234', 'first_name' : 'Michael', 'last_name' : 'Abbruscato', 'group' : 'forklift_operator'},
            {'username' : 'devjen', 'email' : '', 'password' : 'david1234', 'first_name' : 'David', 'last_name' : 'Evjen', 'group' : 'forklift_operator'},
            {'username' : 'chall', 'email' : '', 'password' : 'corey1234', 'first_name' : 'Corey', 'last_name' : 'Hall', 'group' : 'forklift_operator'},
            {'username' : 'single', 'email' : '', 'password' : 'sasha1234', 'first_name' : 'Sasha', 'last_name' : 'Ingle', 'group' : 'forklift_operator'},
            {'username' : 'tjones', 'email' : '', 'password' : 'torrie1234', 'first_name' : 'Torrie', 'last_name' : 'Jones', 'group' : 'forklift_operator'},
            {'username' : 'lkratt', 'email' : '', 'password' : 'lynn1234', 'first_name' : 'Lynn', 'last_name' : 'Kratt', 'group' : 'forklift_operator'},
            {'username' : 'ulewis', 'email' : '', 'password' : 'unkrea1234', 'first_name' : 'Unkrea', 'last_name' : 'Lewis', 'group' : 'forklift_operator'},
            {'username' : 'plockett', 'email' : '', 'password' : 'paul1234', 'first_name' : 'Paul', 'last_name' : 'Lockett', 'group' : 'forklift_operator'},
            {'username' : 'rmarion', 'email' : '', 'password' : 'ralph1234', 'first_name' : 'Ralph', 'last_name' : 'Marion', 'group' : 'forklift_operator'},
            {'username' : 'lmeyers', 'email' : '', 'password' : 'lawanda1234', 'first_name' : 'LaWanda', 'last_name' : 'Meyers', 'group' : 'forklift_operator'},
            {'username' : 'kmunroe', 'email' : '', 'password' : 'kalvin1234', 'first_name' : 'Kalvin', 'last_name' : 'Munroe', 'group' : 'forklift_operator'},
            {'username' : 'jrobinson', 'email' : '', 'password' : 'johnny1234', 'first_name' : 'Johnny', 'last_name' : 'Robinson', 'group' : 'forklift_operator'},
            {'username' : 'cstewart', 'email' : '', 'password' : 'charlie1234', 'first_name' : 'Charlie', 'last_name' : 'Stewart', 'group' : 'forklift_operator'},
            {'username' : 'qcook', 'email' : '', 'password' : 'quinny1234', 'first_name' : 'Quinny', 'last_name' : 'Cook', 'group' : 'forklift_operator'},
            {'username' : 'jrobertson', 'email' : '', 'password' : 'john1234', 'first_name' : 'John', 'last_name' : 'Robertson', 'group' : 'forklift_operator'},
            {'username' : 'mgandy', 'email' : '', 'password' : 'michael1234', 'first_name' : 'Michael', 'last_name' : 'Gandy', 'group' : 'forklift_operator'},
            {'username' : 'kkaspar', 'email' : '', 'password' : 'ken1234', 'first_name' : 'Ken', 'last_name' : 'Kaspar', 'group' : 'forklift_operator'},
            {'username' : 'rpruett', 'email' : '', 'password' : 'robert1234', 'first_name' : 'Robert', 'last_name' : 'Pruett', 'group' : 'forklift_operator'},
            {'username' : 'dtowles', 'email' : '', 'password' : 'deldrick1234', 'first_name' : 'Deldrick', 'last_name' : 'Towles', 'group' : 'forklift_operator'},
            {'username' : 'vjones', 'email' : '', 'password' : 'victor1234', 'first_name' : 'Victor', 'last_name' : 'Jones', 'group' : 'forklift_operator'},
            {'username' : 'vbrown', 'email' : '', 'password' : 'vicki1234', 'first_name' : 'Vicki', 'last_name' : 'Brown', 'group' : 'forklift_operator'},
            {'username' : 'mdavis', 'email' : '', 'password' : 'mark1234', 'first_name' : 'Mark', 'last_name' : 'Davis', 'group' : 'forklift_operator'},
            {'username' : 'oglover', 'email' : '', 'password' : 'otis1234', 'first_name' : 'Otis', 'last_name' : 'Glover', 'group' : 'forklift_operator'},
            {'username' : 'jgeib', 'email' : '', 'password' : 'joshua1234', 'first_name' : 'Joshua', 'last_name' : 'Geib', 'group' : 'forklift_operator'},
            {'username' : 'fhubbard', 'email' : '', 'password' : 'frederick1234', 'first_name' : 'Frederick', 'last_name' : 'Hubbard', 'group' : 'forklift_operator'},
            {'username' : 'tmcintyre', 'email' : '', 'password' : 'tamara1234', 'first_name' : 'Tamara', 'last_name' : 'McIntyre', 'group' : 'forklift_operator'},
            {'username' : 'tvinson', 'email' : '', 'password' : 'timothy1234', 'first_name' : 'Timothy', 'last_name' : 'Vinson', 'group' : 'forklift_operator'},
            {'username' : 'tdavis', 'email' : '', 'password' : 'tony1234', 'first_name' : 'Tony', 'last_name' : 'Davis', 'group' : 'forklift_operator'},
            {'username' : 'tfloyd', 'email' : '', 'password' : 'terry1234', 'first_name' : 'Terry', 'last_name' : 'Floyd', 'group' : 'forklift_operator'},
            {'username' : 'cgoldsmith', 'email' : '', 'password' : 'charles1234', 'first_name' : 'Charles', 'last_name' : 'Goldsmith', 'group' : 'forklift_operator'},
            {'username' : 'djohnson', 'email' : '', 'password' : 'dannell1234', 'first_name' : 'Dannell', 'last_name' : 'Johnson', 'group' : 'forklift_operator'},
            {'username' : 'dcheatham', 'email' : '', 'password' : 'denzell1234', 'first_name' : 'Denzell', 'last_name' : 'Cheatham', 'group' : 'forklift_operator'},
            {'username' : 'mmarcos', 'email' : '', 'password' : 'miguel1234', 'first_name' : 'Miguel', 'last_name' : 'Marcos', 'group' : 'forklift_operator'},
            {'username' : 'jmatos', 'email' : '', 'password' : 'jihad1234', 'first_name' : 'Jihad', 'last_name' : 'Matos', 'group' : 'forklift_operator'},
            {'username' : 'rpascual', 'email' : '', 'password' : 'rigo1234', 'first_name' : 'Rigo', 'last_name' : 'Pascual', 'group' : 'forklift_operator'},
            {'username' : 'bsaldana', 'email' : '', 'password' : 'benito1234', 'first_name' : 'Benito', 'last_name' : 'Saldana', 'group' : 'forklift_operator'},
            {'username' : 'tstojak', 'email' : '', 'password' : 'tony1234', 'first_name' : 'Tony', 'last_name' : 'Stojak', 'group' : 'forklift_operator'},
            {'username' : 'lthomas', 'email' : '', 'password' : 'lloyd1234', 'first_name' : 'Lloyd', 'last_name' : 'Thomas', 'group' : 'forklift_operator'},
            {'username' : 'lwilliams', 'email' : '', 'password' : 'leroy1234', 'first_name' : 'Leroy', 'last_name' : 'Williams', 'group' : 'forklift_operator'},
            {'username' : 'dmiller', 'email' : '', 'password' : 'delancey1234', 'first_name' : 'Delancey', 'last_name' : 'Miller', 'group' : 'forklift_operator'},
            {'username' : 'jmcqueen', 'email' : '', 'password' : 'jessica1234', 'first_name' : 'Jessica', 'last_name' : 'McQueen', 'group' : 'forklift_operator'},
            {'username' : 'zmcmannes', 'email' : '', 'password' : 'zach1234', 'first_name' : 'Zach', 'last_name' : 'McMannes', 'group' : 'forklift_operator'},
            {'username' : 'rrichard', 'email' : '', 'password' : 'regina1234', 'first_name' : 'Regina', 'last_name' : 'Richard', 'group' : 'forklift_operator'},
            {'username' : 'arogers', 'email' : '', 'password' : 'antonio1234', 'first_name' : 'Antonio', 'last_name' : 'Rogers', 'group' : 'forklift_operator'},
            {'username' : 'rthomas', 'email' : '', 'password' : 'rashari1234', 'first_name' : 'Rashari', 'last_name' : 'Thomas', 'group' : 'forklift_operator'},
            {'username' : 'lwashington', 'email' : '', 'password' : 'litasha1234', 'first_name' : 'Litasha', 'last_name' : 'Washington', 'group' : 'forklift_operator'},
            {'username' : 'jwright', 'email' : '', 'password' : 'jaylon1234', 'first_name' : 'Jaylon', 'last_name' : 'Wright', 'group' : 'forklift_operator'},
            {'username' : 'kharper', 'email' : '', 'password' : 'kelly12345', 'first_name' : 'Kelly', 'last_name' : 'Harper', 'group' : 'lab'},
            {'username' : 'dtidwell', 'email' : '', 'password' : 'devin12345', 'first_name' : 'Devin', 'last_name' : 'Tidwell', 'group' : 'lab'},
            {'username' : 'lreyes', 'email' : '', 'password' : 'luckie12345', 'first_name' : 'Luckie', 'last_name' : 'Reyes', 'group' : 'lab'},
            {'username' : 'rreyes', 'email' : '', 'password' : 'ronald12345', 'first_name' : 'Ronald', 'last_name' : 'Reyes', 'group' : 'lab'},
            {'username' : 'vjones', 'email' : '', 'password' : 'victor123', 'first_name' : 'Victor', 'last_name' : 'Jones', 'group' : 'lab'},
            {'username' : 'hwhite', 'email' : '', 'password' : 'henry123', 'first_name' : 'Henry', 'last_name' : 'White', 'group' : 'forklift_operator'},
            {'username' : 'rjohnson', 'email' : '', 'password' : 'raymond123', 'first_name' : 'Raymond', 'last_name' : 'Johnson', 'group' : 'forklift_operator'}
        ]

        for user in users:
            try:
                if not User.objects.filter(username = user['username']).exists():
                    User.objects.create_user(
                        user['username'],
                        email = user['email'],
                        password = user['password'],
                        first_name = user['first_name'],
                        last_name = user['last_name']
                    )
                this_user_object = User.objects.get(username=user['username'])
                if user['group']:
                    if not Group.objects.filter(name=user['group']).exists():
                        group = Group(name=user['group'])
                        group.save()
                        print("Group created successfully!")
                    else:
                        this_user_object.groups.add(Group.objects.get(name=user['group']))
            except Exception as e:
                print(str(e))
                continue

        User.objects.get(username='pmedlin').is_superuser = True
        User.objects.get(username='jdavis').is_superuser = True
        User.objects.get(username='admin').is_superuser = True