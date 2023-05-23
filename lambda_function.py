import base64
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os import environ
from typing import Union
from jinja2 import Template


def lambda_handler(event: Union[dict, list, None] = None, context=None):
    if not event:
        return {
            'statusCode': 500,
            'body': 'Specify recipients in event'
        }

    if isinstance(event, dict):
        event = [event]

    for e in event:
        debug_sleep = environ.get('debug_sleep', e.get('debug_sleep'))
        if debug_sleep:
            print('sleeping for', debug_sleep)
            try:
                from time import sleep
                sleep(int(debug_sleep))
            except ValueError:
                ...

        host = environ.get('host')
        port = int(environ.get('port'))
        user = environ.get('user')
        passwd = environ.get('passwd')
        try:
            passwd = json.loads(passwd)['value']
        except json.decoder.JSONDecodeError:
            ...
        sender = environ.get('sender', user)
        template = base64.b64decode(environ.get('template', '')).decode('utf-8')
        project_id = environ.get('project_id')
        if debug_sleep:
            print('event env', {
                'host': {type(host), host},
                'port': {type(port), port},
                'user': {type(user), user},
                'passwd': {type(passwd), passwd},
                'sender': {type(sender), sender},
                'project_id': {type(project_id), project_id},
            })

        try:
            recipients: list[dict[str, list]] = e.pop('recipients')
        except KeyError:
            try:
                one_recipient = e.pop('one_recipient')
                one_role = e.pop('one_role')
                recipients = [{
                    'email': one_recipient,
                    'roles': [one_role]
                }]
            except KeyError:
                return {
                    'statusCode': 500,
                    'body': 'Specify recipients in event'
                }
        subject = e.get('subject', 'Invitation to a Centry project')

        template_vars = {
            'project_id': project_id
        }
        template_vars.update(e)

        try:
            with smtplib.SMTP_SSL(host=host, port=port) as client:
                client.ehlo()
                client.login(user, passwd)

                for recipient in recipients:
                    user_template_vars = {**template_vars, 'recipient': recipient}
                    email_content = Template(template)

                    msg_root = MIMEMultipart('alternative')
                    msg_root['Subject'] = Template(subject).render(user_template_vars)
                    if sender:
                        msg_root['From'] = sender
                    msg_root['To'] = recipient['email']
                    msg_root.attach(
                        MIMEText(email_content.render(user_template_vars), 'html')
                    )
                    client.sendmail(sender, recipient['email'], msg_root.as_string())

                    print(f'Email sent from {sender} to {recipient["email"]}')
        except Exception as e:
            from traceback import format_exc
            print(format_exc())
            return {
                'statusCode': 500,
                'body': json.dumps(str(e))
            }
        return {
            'statusCode': 200,
            'body': json.dumps('Email sent')
        }
