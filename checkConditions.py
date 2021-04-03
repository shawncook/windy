import os, requests, json, smtplib

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

api_key = os.environ.get('API_KEY')
base_url = 'http://api.openweathermap.org/data/2.5/forecast?'
zip_code = os.environ.get('ZIP_CODE')
complete_url = base_url + 'appid=' + api_key + '&zip=' + zip_code + '&units=imperial'
response = requests.get(complete_url)
respJson = response.json()

#Email Account
email_sender_username = os.environ.get('SENDER_USERNAME')
email_sender_password = os.environ.get('SENDER_PASSWORD')
email_smtp_server = os.environ.get('SMTP_SERVER')
email_smtp_port = os.environ.get('SMTP_PORT')

#Email Content
email_recipients = [ os.environ.get('RECIPIENT') ]
email_subject = '🪁 Upcoming kite conditions'

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
	server.login(email_sender_username, email_sender_password)

	for recipient in email_recipients:
		print(f'Sending email to {recipient}.')
		message            = MIMEMultipart('alternative')
		message['From']    = email_sender_username
		message['To']      = recipient
		message['Subject'] = email_subject
		message.attach(MIMEText(email_body, 'plain'))
		text = message.as_string()
		server.sendmail(email_sender_username, recipient, text)

	server.quit()

# validate a weather condition
def validate_condition(cond):
	clouds = cond['clouds']
	dt     = cond['dt']
	main   = cond['main']
	wind   = cond['wind']
	temp   = main['temp']
	date   = datetime.utcfromtimestamp(dt)

	return (
		check_cloud_cover(clouds)
		and check_day_valid(date)
		and check_hours_valid(date)
		and check_temp_valid(temp)
		and check_wind_speed(wind)
	)

# build list of contitions and data.
def build_email_body(condition):
	main = condition['main']
	wind = condition['wind']
	desc = condition['weather'][0]['description'].title()
	temp = main['temp']

	dt = datetime.utcfromtimestamp(condition['dt'])
	date_string = str(format_date_time(dt))
	date_string += (
		'\r\n'
		'Wind speed: '
		+ str(round(wind['speed'])) + ' mph '
		+ str(degrees_to_cardinal(wind['deg']))
	)
	if check_wind_direction(wind):
		date_string += ' ⭐️'
	date_string += (
		'\r\n'
		'Conditions: '
		+ str(round(main['temp'])) + '\u00b0F, ' + str(desc)
	)
	return date_string

# format date/time to specified format
def format_date_time(dt):
	date_string = '{0:%I:%M%p %A}'.format(dt).lstrip('0')
	date_string += ' {0:%b %d}'.format(dt).lstrip('0')
	return date_string

# do the rest
if respJson['cod'] != '404':
	conditions_list = respJson['list']
	optimal_dates = []

	for condition in conditions_list:
		if validate_condition(condition):
			date_string = build_email_body(condition)
			optimal_dates.append(date_string)

	# if there are optimal dates, do things.
	if len(optimal_dates):
		message = 'Optimal conditions upcoming on the following dates:\r\n\r\n'
		message += '\r\n\r\n'.join(optimal_dates)
		message += '\r\n\r\nHave fun!'

		print(message)
		send_email(message)

else:
	print('Location not found.')
