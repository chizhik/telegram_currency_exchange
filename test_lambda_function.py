import os
from typing import Any, Dict
from unittest import TestCase, mock

import lambda_function


def _generate_event(chat_id: str, user_id: str,
                    message: str) -> Dict[str, Any]:
    return {
        'message': {
            'chat': {
                'id': chat_id
            },
            'from': {
                'id': user_id
            },
            'text': message
        }
    }


class Test(TestCase):
    @mock.patch.dict(
        os.environ, {
            "CURRENCY_A_RUS": "тенге",
            "CURRENCY_A": "tenge",
            "CURRENCY_B_RUS": "вон",
            "CURRENCY_B": "won"
        })
    def test_helper_functions(self):
        m = lambda_function.instruction_msg()
        print(m)
        print('=================================================')
        m = lambda_function.amount_msg(True)
        print(m)
        print('=================================================')
        m = lambda_function.amount_msg(False)
        print(m)
        print('=================================================')
        m = lambda_function.unknown_msg()
        print(m)
        print('=================================================')

        currency_from, currency_to = lambda_function.currency_from_to(True)
        assert currency_from == "тенге"
        assert currency_to == "вон"

        currency_from, currency_to = lambda_function.currency_from_to(False)
        assert currency_from == "вон"
        assert currency_to == "тенге"

        m = lambda_function.notification_msg(
            {'message': {
                'from': {
                    'first_name': 'Jeff',
                    'id': 1111
                }
            }}, {"amount": 300}, 500, True)
        assert lambda_function.cancel_command(False) in m
        print(m)
        print('=================================================')

        m = lambda_function.notification_msg(
            {'message': {
                'from': {
                    'first_name': 'Jeff',
                    'id': 1111
                }
            }}, {"amount": 300}, 500, False)
        assert lambda_function.cancel_command(True) in m
        print(m)
        print('=================================================')

        print(lambda_function.relTimeToText(1625284004))

    @mock.patch.dict(
        os.environ, {
            "CURRENCY_A_RUS": "тенге",
            "CURRENCY_A": "tenge",
            "CURRENCY_B_RUS": "вон",
            "CURRENCY_B": "won"
        })
    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_unknown_messages(self, mock_send_message,
                                                     mock_add_history):
        chat_id = 'random_chat_id'

        for unknown_message in [
                'unknown_message', '-123', '0', '1.5', '2,500'
        ]:
            with self.subTest(unknown_message=unknown_message):
                event = _generate_event(chat_id=chat_id,
                                        user_id='admin',
                                        message=unknown_message)

                lambda_function.telegram_bot_main(event)

                mock_send_message.assert_called_with(
                    lambda_function.unknown_msg(), chat_id)
                mock_add_history.assert_called_with(event)

    @mock.patch.dict(
        os.environ, {
            "CURRENCY_A_RUS": "тенге",
            "CURRENCY_A": "tenge",
            "CURRENCY_B_RUS": "вон",
            "CURRENCY_B": "won"
        })
    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_start_message(self, mock_send_message,
                                                  mock_add_history):
        chat_id = 'random_chat_id'
        event = _generate_event(chat_id=chat_id,
                                user_id='admin',
                                message='/start')

        lambda_function.telegram_bot_main(event)

        mock_send_message.assert_called_with(lambda_function.instruction_msg(),
                                             chat_id)
        mock_add_history.assert_called_with(event)

    @mock.patch.dict(
        os.environ, {
            "CURRENCY_A_RUS": "тенге",
            "CURRENCY_A": "tenge",
            "CURRENCY_B_RUS": "вон",
            "CURRENCY_B": "won"
        })
    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_tenge_message(self, mock_send_message,
                                                  mock_add_history):
        chat_id = 'random_chat_id'
        event = _generate_event(chat_id=chat_id,
                                user_id='admin',
                                message='/tenge')

        lambda_function.telegram_bot_main(event)

        mock_send_message.assert_called_with(lambda_function.amount_msg(True),
                                             chat_id)
        mock_add_history.assert_called_with(event)

    @mock.patch.dict(
        os.environ, {
            "CURRENCY_A_RUS": "тенге",
            "CURRENCY_A": "tenge",
            "CURRENCY_B_RUS": "вон",
            "CURRENCY_B": "won"
        })
    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_won_message(self, mock_send_message,
                                                mock_add_history):
        chat_id = 'random_chat_id'
        event = _generate_event(chat_id=chat_id,
                                user_id='admin',
                                message='/won')

        lambda_function.telegram_bot_main(event)

        mock_send_message.assert_called_with(lambda_function.amount_msg(False),
                                             chat_id)
        mock_add_history.assert_called_with(event)

    @mock.patch.dict(
        os.environ, {
            "CURRENCY_A_RUS": "тенге",
            "CURRENCY_A": "tenge",
            "CURRENCY_B_RUS": "вон",
            "CURRENCY_B": "won"
        })
    @mock.patch('lambda_function.previous_message')
    @mock.patch('lambda_function.add_history')
    @mock.patch('lambda_function.send_message')
    def test_telegram_bot_main_with_positive_numeric_message_and_unknown_previous_messages(
            self, mock_send_message, mock_add_history, mock_previous_message):
        chat_id = 'random_chat_id'
        user_id = 'admin'

        for previous_message in ['unknown_message', '-123', '0']:
            with self.subTest():
                event = _generate_event(chat_id=chat_id,
                                        user_id=user_id,
                                        message='123')

                mock_previous_message.return_value = previous_message
                lambda_function.telegram_bot_main(event)

                mock_previous_message.assert_called_with(user_id)
                mock_send_message.assert_called_with(
                    lambda_function.unknown_msg(), chat_id)
                mock_add_history.assert_called_with(event)
