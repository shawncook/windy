import os, requests, json, smtplib

from dotenv import load_dotenv

load_dotenv()

from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

api_key   = os.environ.get('API_KEY')
base_url  = 'http://api.openweathermap.org/data/2.5/forecast?'
zip_code  = os.environ.get('ZIP_CODE')
req_url   = base_url + 'appid=' + api_key + '&zip=' + zip_code + '&units=imperial'
resp_json = requests.get(req_url).json()

# email account creds
email_recipients   = [ os.environ.get('RECIPIENT') ]
email_sender_pw    = os.environ.get('SENDER_PASSWORD')
email_sender_uname = os.environ.get('SENDER_USERNAME')
email_smtp_port    = os.environ.get('SMTP_PORT')
email_smtp_server  = os.environ.get('SMTP_SERVER')
email_subject      = '🪁 Upcoming kite conditions'

# cloud cover under 85% (overcast).
def check_cloud_cover(clouds):
	return clouds['all'] < 85

# Must be Friday, Saturday or Sunday.
def check_day_valid(date):
	weekday = date.weekday()
	valid_days = range(4, 7)
	return weekday in valid_days

# Hour must be between 10am and 6pm.
def check_hours_valid(date):
	return 10 <= date.hour <= 18

# check probability of precipitation
def check_precipitation(pop):
	return pop < 25

# Temp is between 50 and 90.
def check_temp_valid(temp):
	return 50 <= temp <= 90

# bonus points for winds from NE to S
def check_wind_direction(wind):
	return 45 <= wind['deg'] <= 180

# wind speed between 8 and 20mph
def check_wind_speed(wind):
	return 8 <= wind['speed'] <= 20

# get human readable wind direction
def degrees_to_cardinal(d):
	dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
	ix = int((d + 11.25)/22.5)
	return dirs[ix % 16]

# use smtplib to send and email
def send_email(email_body):
	server = smtplib.SMTP_SSL(email_smtp_server, email_smtp_port)
	server.login(email_sender_uname, email_sender_pw)

	for recipient in email_recipients:		
		message            = MIMEMultipart('alternative')
		message['From']    = email_sender_uname
		message['To']      = recipient
		message['Subject'] = email_subject
		
		message.attach(MIMEText(email_body, 'plain'))

		print(f'Sending email to {recipient}.')

		server.sendmail(email_sender_uname, recipient, message.as_string())

	server.quit()

# validate a weather condition
def validate_condition(cond):
	clouds = cond['clouds']
	dt     = cond['dt']
	main   = cond['main']
	pop    = cond['pop']
	wind   = cond['wind']
	temp   = main['temp']
	date   = datetime.utcfromtimestamp(dt)

	return (
		check_cloud_cover(clouds)
		and check_day_valid(date)
		and check_hours_valid(date)
		and check_precipitation(pop)
		and check_temp_valid(temp)
		and check_wind_speed(wind)
	)

# build list of contitions and data.
def build_datapoint(condition):
	desc = condition['weather'][0]['description']
	dt   = datetime.utcfromtimestamp(condition['dt'])
	main = condition['main']
	wind = condition['wind']
	temp = main['temp']

	# begin with date and time.
	body = str(format_date_time(dt))

	# append wind speed and direction
	body += (
		'\r\n'
		'Wind speed: '
		+ str(round(wind['speed'])) + ' mph '
		+ str(degrees_to_cardinal(wind['deg']))
	)

	# if favoratble direction, append star
	if check_wind_direction(wind):
		body += ' ⭐️'

	# append conditions
	body += (
		'\r\n'
		'Conditions: '
		+ str(round(main['temp'])) + '\u00b0F, ' + str(desc.title())
	)

	return body

# format date/time to specified format
def format_date_time(dt):
	date_string = '{0:%I:%M%p %A}'.format(dt).lstrip('0')
	date_string += ' {0:%b %d}'.format(dt).lstrip('0')

	return date_string

# do the rest
if resp_json['cod'] != '404':
	conditions_list = resp_json['list']
	optimal_dates = []

	for condition in conditions_list:
		if validate_condition(condition):
			optimal_dates.append(build_datapoint(condition))

	# if there are optimal dates, do things.
	if len(optimal_dates):
		message = 'Optimal conditions upcoming on the following dates:\r\n\r\n'
		message += '\r\n\r\n'.join(optimal_dates)
		message += '\r\n\r\nHave fun!'

		print(message)
		send_email(message)

else:
	print('Location not found.')
