from django.contrib.auth.models import User
from django.core.management import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        users = [
            {'username' : 'pmedlin', 'email' : 'pmedlin@kinpakinc.com', 'password' : 'parker123', 'first_name' : 'Parker', 'last_name' : 'Medlin'},
            {'username' : 'jdavis', 'email' : 'jdavis@kinpakinc.com', 'password' : 'jordan123', 'first_name' : 'Jordan', 'last_name' : 'Davis'},
            {'username' : 'ddavis', 'email' : 'ddavis@kinpakinc.com', 'password' : 'danny1234', 'first_name' : 'Danny', 'last_name' : 'Davis'},
            {'username' : 'gbarganier', 'email' : 'gbarganier@kinpakinc.com', 'password' : 'ginny1234', 'first_name' : 'Ginny', 'last_name' : 'Barganier'},
            {'username' : 'vwaclawek', 'email' : 'vwaclawek@kinpakinc.com', 'password' : 'vincent123', 'first_name' : 'Vincent', 'last_name' : 'Waclawek'},
            {'username' : 'sabdus', 'email' : 'matos.saeed@gmail.com', 'password' : 'saeed123', 'first_name' : 'Saeed', 'last_name' : 'Abdus-Salaam'},
            {'username' : 'rbanks', 'email' : 'rodneytbanks76@gmail.com', 'password' : 'rodney123', 'first_name' : 'Rodney', 'last_name' : 'Banks'},
            {'username' : 'ephillips', 'email' : 'ephillips334@gmail.com', 'password' : 'eric1234', 'first_name' : 'Eric', 'last_name' : 'Phillips'},
            {'username' : 'mphillips', 'email' : 'ttpphillips63@gmail.com', 'password' : 'marquett123', 'first_name' : 'Marquett', 'last_name' : 'Phillips'},
            {'username' : 'jcalhounsr', 'email' : 'jcalhoun2976@gmail.com', 'password' : 'joesr1234', 'first_name' : 'Joe', 'last_name' : 'Calhoun-Sr'},
            {'username' : 'jcalhounjr', 'email' : 'calhounjo@yahoo.com', 'password' : 'joejr1234', 'first_name' : 'Joe', 'last_name' : 'Calhoun-Jr'},
            {'username' : 'khardy', 'email' : 'hardykeith554@gmail.com', 'password' : 'keith123', 'first_name' : 'Keith', 'last_name' : 'Hardy'},
            {'username' : 'kkeyes', 'email' : 'keyeskevin91@yahoo.com', 'password' : 'kevin123', 'first_name' : 'Kevin', 'last_name' : 'Keyes'},
            {'username' : 'amccloud', 'email' : 'polokid399@gmail.com', 'password' : 'aaron123', 'first_name' : 'Aaron', 'last_name' : 'McCloud'},
            {'username' : 'jtyler', 'email' : 'tylerboi32@gmail.com', 'password' : 'jermaine123', 'first_name' : 'Jermaine', 'last_name' : 'Tyler'},
            {'username' : 'swheeler', 'email' : 'swheeler@kinpakinc.com', 'password' : 'shawn123', 'first_name' : 'Shawn', 'last_name' : 'Wheeler'},
            {'username' : 'jblankenship', 'email' : 'warehouse@kinpakinc.com', 'password' : 'joey1234', 'first_name' : 'Joey', 'last_name' : 'Blankenship'},
            {'username' : 'mchandler', 'email' : '', 'password' : 'morris123', 'first_name' : 'Morris', 'last_name' : 'Chandler'},
            {'username' : 'tstone', 'email' : '', 'password' : 'tom12345', 'first_name' : 'Tom', 'last_name' : 'Stone'},
            {'username' : 'atodd', 'email' : '', 'password' : 'anthony123', 'first_name' : 'Anthony', 'last_name' : 'Todd'},
            {'username' : 'mabrams', 'email' : '', 'password' : 'mike1234', 'first_name' : 'Mike', 'last_name' : 'Abrams'},
            {'username' : 'rwilliams', 'email' : '', 'password' : 'renardo123', 'first_name' : 'Renardo', 'last_name' : 'Williams'},
            {'username' : 'oglover', 'email' : '', 'password' : 'otis1234', 'first_name' : 'Otis', 'last_name' : 'Glover'},
            {'username' : 'vbrown', 'email' : '', 'password' : 'vicki123', 'first_name' : 'Vicki', 'last_name' : 'Brown'},
            {'username' : 'cholloway', 'email' : '', 'password' : 'crystal123', 'first_name' : 'Crystal', 'last_name' : 'Holloway'},
            {'username' : 'ljackson', 'email' : '', 'password' : 'leo12345', 'first_name' : 'Leo', 'last_name' : 'Jackson'},
            {'username' : 'chenderson', 'email' : '', 'password' : 'conita123', 'first_name' : 'Conita', 'last_name' : 'Henderson'},
            {'username' : 'etaylor', 'email' : '', 'password' : 'ernest123', 'first_name' : 'Earnest', 'last_name' : 'Taylor'},
            {'username' : 'rriddle', 'email' : '', 'password' : 'rodney123', 'first_name' : 'Rodney', 'last_name' : 'Riddle'},
            {'username' : 'mcaldwell', 'email' : '', 'password' : 'mack1234', 'first_name' : 'Mack', 'last_name' : 'Caldwell'},
            {'username' : 'ewoods', 'email' : '', 'password' : 'ernest123', 'first_name' : 'Ernest', 'last_name' : 'Woods'},
            {'username' : 'bbarganier', 'email' : '', 'password' : 'bobby123', 'first_name' : 'Bobby', 'last_name' : 'Barganier'},
            {'username' : 'mclark', 'email' : '', 'password' : 'maxie123', 'first_name' : 'Maxie', 'last_name' : 'Clark'},
            {'username' : 'karmont', 'email' : '', 'password' : 'kirby123', 'first_name' : 'Kirby', 'last_name' : 'Armont'},
            {'username' : 'zmcmannes', 'email' : '', 'password' : 'zach1234', 'first_name' : 'Zach', 'last_name' : 'McMannes'},
            {'username' : 'mdavis', 'email' : '', 'password' : 'mark1234', 'first_name' : 'Mark', 'last_name' : 'Davis'},
            {'username' : 'rthomas', 'email' : '', 'password' : 'rasari123', 'first_name' : 'Rasari', 'last_name' : 'Thomas'},
            {'username' : 'mlockwood', 'email' : '', 'password' : 'mike1234', 'first_name' : 'Mike', 'last_name' : 'Lockwood'},
            {'username' : 'cjones', 'email' : '', 'password' : 'charlie123', 'first_name' : 'Charlie', 'last_name' : 'Jones'},
            {'username' : 'rburton', 'email' : '', 'password' : 'reginald1234', 'first_name' : 'Reginald', 'last_name' : 'Burton'},
            {'username' : 'rcordell', 'email' : '', 'password' : 'randall1234', 'first_name' : 'Randall', 'last_name' : 'Cordell'},
            {'username' : 'mdeloach', 'email' : '', 'password' : 'mario1234', 'first_name' : 'Mario', 'last_name' : 'Deloach'},
            {'username' : 'jchandler', 'email' : '', 'password' : 'joe1234', 'first_name' : 'Joe', 'last_name' : 'Chandler'},
            {'username' : 'jboutwell-sr', 'email' : '', 'password' : 'jamie1234', 'first_name' : 'Jamie', 'last_name' : 'Boutwell-Sr'},
            {'username' : 'jboutwell-jr', 'email' : '', 'password' : 'jamie1234', 'first_name' : 'Jamie', 'last_name' : 'Boutwell-Jr'},
            {'username' : 'mabbruscato', 'email' : '', 'password' : 'michael1234', 'first_name' : 'Michael', 'last_name' : 'Abbruscato'},
            {'username' : 'devjen', 'email' : '', 'password' : 'david1234', 'first_name' : 'David', 'last_name' : 'Evjen'},
            {'username' : 'chall', 'email' : '', 'password' : 'corey1234', 'first_name' : 'Corey', 'last_name' : 'Hall'},
            {'username' : 'single', 'email' : '', 'password' : 'sasha1234', 'first_name' : 'Sasha', 'last_name' : 'Ingle'},
            {'username' : 'tjones', 'email' : '', 'password' : 'torrie1234', 'first_name' : 'Torrie', 'last_name' : 'Jones'},
            {'username' : 'lkratt', 'email' : '', 'password' : 'lynn1234', 'first_name' : 'Lynn', 'last_name' : 'Kratt'},
            {'username' : 'ulewis', 'email' : '', 'password' : 'unkrea1234', 'first_name' : 'Unkrea', 'last_name' : 'Lewis'},
            {'username' : 'plockett', 'email' : '', 'password' : 'paul1234', 'first_name' : 'Paul', 'last_name' : 'Lockett'},
            {'username' : 'rmarion', 'email' : '', 'password' : 'ralph1234', 'first_name' : 'Ralph', 'last_name' : 'Marion'},
            {'username' : 'lmeyers', 'email' : '', 'password' : 'lawanda1234', 'first_name' : 'LaWanda', 'last_name' : 'Meyers'},
            {'username' : 'kmunroe', 'email' : '', 'password' : 'kalvin1234', 'first_name' : 'Kalvin', 'last_name' : 'Munroe'},
            {'username' : 'jrobinson', 'email' : '', 'password' : 'johnny1234', 'first_name' : 'Johnny', 'last_name' : 'Robinson'},
            {'username' : 'cstewart', 'email' : '', 'password' : 'charlie1234', 'first_name' : 'Charlie', 'last_name' : 'Stewart'},
            {'username' : 'qcook', 'email' : '', 'password' : 'quinny1234', 'first_name' : 'Quinny', 'last_name' : 'Cook'},
            {'username' : 'jrobertson', 'email' : '', 'password' : 'john1234', 'first_name' : 'John', 'last_name' : 'Robertson'},
            {'username' : 'mgandy', 'email' : '', 'password' : 'michael1234', 'first_name' : 'Michael', 'last_name' : 'Gandy'},
            {'username' : 'kkaspar', 'email' : '', 'password' : 'ken1234', 'first_name' : 'Ken', 'last_name' : 'Kaspar'},
            {'username' : 'rpruett', 'email' : '', 'password' : 'robert1234', 'first_name' : 'Robert', 'last_name' : 'Pruett'},
            {'username' : 'dtowles', 'email' : '', 'password' : 'deldrick1234', 'first_name' : 'Deldrick', 'last_name' : 'Towles'},
            {'username' : 'vjones', 'email' : '', 'password' : 'victor1234', 'first_name' : 'Victor', 'last_name' : 'Jones'},
            {'username' : 'mabrams', 'email' : '', 'password' : 'michael12345', 'first_name' : 'Michael', 'last_name' : 'Abrams'},
            {'username' : 'vbrown', 'email' : '', 'password' : 'vicki1234', 'first_name' : 'Vicki', 'last_name' : 'Brown'},
            {'username' : 'mdavis', 'email' : '', 'password' : 'mark1234', 'first_name' : 'Mark', 'last_name' : 'Davis'},
            {'username' : 'oglover', 'email' : '', 'password' : 'otis1234', 'first_name' : 'Otis', 'last_name' : 'Glover'},
            {'username' : 'jgeib', 'email' : '', 'password' : 'joshua1234', 'first_name' : 'Joshua', 'last_name' : 'Geib'},
            {'username' : 'fhubbard', 'email' : '', 'password' : 'frederick1234', 'first_name' : 'Frederick', 'last_name' : 'Hubbard'},
            {'username' : 'tmcintyre', 'email' : '', 'password' : 'tamara1234', 'first_name' : 'Tamara', 'last_name' : 'McIntyre'},
            {'username' : 'tvinson', 'email' : '', 'password' : 'timothy1234', 'first_name' : 'Timothy', 'last_name' : 'Vinson'},
            {'username' : 'tdavis', 'email' : '', 'password' : 'tony1234', 'first_name' : 'Tony', 'last_name' : 'Davis'},
            {'username' : 'tfloyd', 'email' : '', 'password' : 'terry1234', 'first_name' : 'Terry', 'last_name' : 'Floyd'},
            {'username' : 'cgoldsmith', 'email' : '', 'password' : 'charles1234', 'first_name' : 'Charles', 'last_name' : 'Goldsmith'},
            {'username' : 'djohnson', 'email' : '', 'password' : 'dannell1234', 'first_name' : 'Dannell', 'last_name' : 'Johnson'},
            {'username' : 'dcheatham', 'email' : '', 'password' : 'denzell1234', 'first_name' : 'Denzell', 'last_name' : 'Cheatham'},
            {'username' : 'mmarcos', 'email' : '', 'password' : 'miguel1234', 'first_name' : 'Miguel', 'last_name' : 'Marcos'},
            {'username' : 'jmatos', 'email' : '', 'password' : 'jihad1234', 'first_name' : 'Jihad', 'last_name' : 'Matos'},
            {'username' : 'rpascual', 'email' : '', 'password' : 'rigo1234', 'first_name' : 'Rigo', 'last_name' : 'Pascual'},
            {'username' : 'bsaldana', 'email' : '', 'password' : 'benito1234', 'first_name' : 'Benito', 'last_name' : 'Saldana'},
            {'username' : 'tstojak', 'email' : '', 'password' : 'tony1234', 'first_name' : 'Tony', 'last_name' : 'Stojak'},
            {'username' : 'lthomas', 'email' : '', 'password' : 'lloyd1234', 'first_name' : 'Lloyd', 'last_name' : 'Thomas'},
            {'username' : 'lwilliams', 'email' : '', 'password' : 'leroy1234', 'first_name' : 'Leroy', 'last_name' : 'Williams'},
            {'username' : 'dmiller', 'email' : '', 'password' : 'delancey1234', 'first_name' : 'Delancey', 'last_name' : 'Miller'},
            {'username' : 'jmcqueen', 'email' : '', 'password' : 'jessica1234', 'first_name' : 'Jessica', 'last_name' : 'McQueen'},
            {'username' : 'zmcmannes', 'email' : '', 'password' : 'zach1234', 'first_name' : 'Zach', 'last_name' : 'McMannes'},
            {'username' : 'rrichard', 'email' : '', 'password' : 'regina1234', 'first_name' : 'Regina', 'last_name' : 'Richard'},
            {'username' : 'arogers', 'email' : '', 'password' : 'antonio1234', 'first_name' : 'Antonio', 'last_name' : 'Rogers'},
            {'username' : 'rthomas', 'email' : '', 'password' : 'rashari1234', 'first_name' : 'Rashari', 'last_name' : 'Thomas'},
            {'username' : 'lwashington', 'email' : '', 'password' : 'litasha1234', 'first_name' : 'Litasha', 'last_name' : 'Washington'},
            {'username' : 'jwright', 'email' : '', 'password' : 'jaylon1234', 'first_name' : 'Jaylon', 'last_name' : 'Wright'}
        ]

            #blend_crew_group = Group.objects.get(name='blend_crew')
            #forklift_operator_group = Group.objects.get(name='forklift_operator_group')
            #front_office_group = Group.objects.get(name='front_office_group')

        for user in users:
            try:
                User.objects.create_user(
                    user['username'],
                    email = user['email'],
                    password = user['password'],
                    first_name = user['first_name'],
                    last_name = user['last_name']
                )
            except:
                continue