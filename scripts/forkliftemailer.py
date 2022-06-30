from O365 import Account

credentials = ('6318854d-eeff-454e-bf84-5f529f147fba', 'Drn8Q~Q6Ynx25seZQMKjJwG-GQAQebNBR_e9yacl')

account = Account(credentials)
m = account.new_message()
m.to.add('jdavis@kinpakinc.com')
m.subject = 'Sent from forkliftemailer.py'
m.body = "Uhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh"
m.send()